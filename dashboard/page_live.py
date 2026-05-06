"""
VidyutRakshak AI — Live Stream Page
Shows real-time meter data with anomaly scoring.
Falls back to simulated data if no ESP32 stream is active.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from simulator.live_anomaly_engine import (
    load_live_stream, load_stats,
    score_live_meters, get_locality_timeseries
)

REFRESH_INTERVAL = 3  # seconds

# Fixed meter configs for simulation — some are always anomalous
METER_CONFIGS = [
    # (meter_id, locality, multiplier, anomaly_type)
    ("MTR-001", "Rajajinagar",  1.2,  "normal"),
    ("MTR-002", "Rajajinagar",  1.2,  "theft"),    # theft: near-zero consumption
    ("MTR-003", "Malleshwaram", 1.0,  "normal"),
    ("MTR-004", "Malleshwaram", 1.0,  "tamper"),   # tamper: spike + zero pattern
    ("MTR-005", "Indiranagar",  1.4,  "normal"),
    ("MTR-006", "Indiranagar",  1.4,  "normal"),
    ("MTR-007", "Whitefield",   1.8,  "spike"),    # spike: sudden high usage
    ("MTR-008", "Whitefield",   1.8,  "normal"),
    ("MTR-009", "Jayanagar",    0.9,  "normal"),
    ("MTR-010", "Jayanagar",    0.9,  "theft"),    # theft: consistently very low
]


# ---------- SIMULATED FALLBACK ----------
def generate_simulated_data():
    """
    Generate simulated live meter data with realistic anomalies injected.
    Certain meters are permanently set to anomalous patterns so
    the detection engine always has something to flag.
    """
    now  = datetime.now()
    hour = now.hour + now.minute / 60

    data = []
    for meter_id, locality, multiplier, anomaly_type in METER_CONFIGS:
        # Base realistic daily consumption curve
        base = (
            2.5 * np.exp(-0.5 * ((hour - 7.5) / 1.5) ** 2) +
            4.0 * np.exp(-0.5 * ((hour - 20.0) / 2.0) ** 2) +
            0.3
        ) * multiplier / 20

        # Inject anomaly pattern
        if anomaly_type == "theft":
            # Bypass: consumption is only 8–15% of expected baseline
            consumption   = base * np.random.uniform(0.08, 0.15)
            anomaly_flag  = 1
            anomaly_label = "theft"

        elif anomaly_type == "tamper":
            # Tamper: alternates between near-zero and big spikes
            if np.random.random() < 0.4:
                consumption = np.random.uniform(0.001, 0.005)  # near-zero
            else:
                consumption = base * np.random.uniform(3.5, 5.5)  # spike
            anomaly_flag  = 1
            anomaly_label = "tamper"

        elif anomaly_type == "spike":
            # Sudden illegal load spike
            consumption   = base * np.random.uniform(4.0, 6.0)
            anomaly_flag  = 1
            anomaly_label = "spike"

        else:
            # Normal: base + small noise
            consumption   = max(0, base + np.random.normal(0, 0.05))
            anomaly_flag  = 0
            anomaly_label = "normal"

        voltage = round(np.random.normal(230, 3 if anomaly_type == "normal" else 8), 2)

        data.append({
            "timestamp":       now.strftime("%Y-%m-%d %H:%M:%S"),
            "meter_id":        meter_id,
            "locality":        locality,
            "consumption_kwh": round(max(0, consumption), 4),
            "voltage":         voltage,
            "current":         round(consumption / 0.23, 4),
            "anomaly_flag":    anomaly_flag,
            "anomaly_label":   anomaly_label,
        })

    return pd.DataFrame(data)


def render():
    st.markdown("# ⚡ Live Smart Meter Stream")
    st.markdown(
        "<div class='section-header'>REAL-TIME METER DATA — SIMULATED / ESP32 HARDWARE</div>",
        unsafe_allow_html=True
    )

    # ── Try loading real ESP32 stream first ──────────────
    stats = load_stats()
    df    = load_live_stream()

    # ── Session state for simulated mode ─────────────────
    if "sim_live_data" not in st.session_state:
        st.session_state.sim_live_data = pd.DataFrame()
        st.session_state.sim_batch_count = 0

    use_sim = df is None or stats is None

    if use_sim:
        st.warning(
            "📡 No ESP32 stream detected — running in **simulation mode**. "
            "To use real hardware, run `python simulator/esp32_simulator.py` in a separate terminal."
        )
        new_data = generate_simulated_data()
        st.session_state.sim_live_data = pd.concat(
            [st.session_state.sim_live_data, new_data]
        ).tail(200)
        st.session_state.sim_batch_count += 1
        df = st.session_state.sim_live_data.copy()
        # Parse timestamp for consistency
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        # Build synthetic stats
        stats = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "batch_count": st.session_state.sim_batch_count,
            "active_meters": df["meter_id"].nunique(),
            "current_kwh_total": float(df["consumption_kwh"].sum()),
            "anomaly_count": int(df["anomaly_flag"].sum()) if "anomaly_flag" in df.columns else 0,
        }

    # ── KPI Row ───────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Last Updated",  stats["last_updated"].split(" ")[1] if " " in str(stats["last_updated"]) else str(stats["last_updated"]))
    k2.metric("Batches Sent",  stats["batch_count"])
    k3.metric("Active Meters", stats["active_meters"])
    k4.metric("Live kWh Total", f"{stats['current_kwh_total']:.2f}")
    k5.metric("🚨 Anomalies",   stats["anomaly_count"],
              delta="ALERT" if stats["anomaly_count"] > 0 else "Clear",
              delta_color="inverse" if stats["anomaly_count"] > 0 else "normal")

    # ── Live Consumption Chart ────────────────────────────
    st.markdown(
        "<div class='section-header'>LIVE CONSUMPTION STREAM — ALL LOCALITIES</div>",
        unsafe_allow_html=True
    )

    if "locality" in df.columns and "consumption_kwh" in df.columns:
        df_ts = df.copy()
        if "timestamp" in df_ts.columns:
            df_ts["minute_bucket"] = pd.to_datetime(df_ts["timestamp"], errors="coerce").dt.floor("min")
        else:
            df_ts["minute_bucket"] = datetime.now()

        ts = (
            df_ts.groupby(["minute_bucket", "locality"])["consumption_kwh"]
            .sum().reset_index()
        )

        fig = go.Figure()
        colors = ["#38bdf8", "#818cf8", "#34d399", "#fb923c", "#f472b6"]

        for i, locality in enumerate(ts["locality"].unique()):
            loc_ts = ts[ts["locality"] == locality]
            fig.add_trace(go.Scatter(
                x=loc_ts["minute_bucket"],
                y=loc_ts["consumption_kwh"],
                name=locality, mode="lines",
                line=dict(color=colors[i % len(colors)], width=2)
            ))

        fig.update_layout(
            paper_bgcolor="#0a0e1a", plot_bgcolor="#111827",
            font=dict(family="Syne", color="#94a3b8"),
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False, color="#334155", title=""),
            yaxis=dict(showgrid=True, gridcolor="#1e293b",
                       color="#334155", title="kWh"),
            legend=dict(bgcolor="#111827", bordercolor="#1e293b", font=dict(size=11))
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Two column layout ─────────────────────────────────
    left, right = st.columns([1.2, 1])

    with left:
        st.markdown(
            "<div class='section-header'>LIVE ANOMALY SCOREBOARD</div>",
            unsafe_allow_html=True
        )

        try:
            scored  = score_live_meters(df)
            flagged = scored[scored["is_live_anomaly"] == True]
        except Exception:
            flagged = pd.DataFrame()

        if len(flagged) == 0:
            st.markdown(
                "<div style='color:#22c55e;font-family:JetBrains Mono,"
                "monospace;font-size:13px;padding:20px'>"
                "✅ No anomalies detected in current stream</div>",
                unsafe_allow_html=True
            )
        else:
            for _, row in flagged.iterrows():
                conf = row["live_confidence"]
                if conf >= 0.75:   border, badge = "#ef4444", "badge-red"
                elif conf >= 0.55: border, badge = "#f97316", "badge-orange"
                else:              border, badge = "#eab308", "badge-yellow"

                st.markdown(f"""
                <div class="alert-card" style="border-left-color:{border}">
                    <strong style="color:#e2e8f0">{row['meter_id']}</strong>
                    <span class="badge {badge}">{conf*100:.0f}% confidence</span>
                    <br>
                    <span style="color:#64748b">{row.get('locality', 'Unknown')}</span>
                    &nbsp;·&nbsp;
                    <span style="color:#94a3b8">{row.get('live_status', 'Monitoring')}</span>
                    <br>
                    <span style="color:#475569;font-size:11px;font-family:JetBrains Mono,monospace">
                        avg {row.get('mean_kwh', 0):.4f} kWh
                        · last {row.get('last_kwh', 0):.4f} kWh
                        · {int(row.get('anomaly_count', 0))} anomalous readings
                    </span>
                </div>
                """, unsafe_allow_html=True)

    with right:
        st.markdown(
            "<div class='section-header'>LOCALITY LOAD RIGHT NOW</div>",
            unsafe_allow_html=True
        )

        locality_now = (
            df.groupby("locality")["consumption_kwh"]
            .mean().reset_index()
            .sort_values("consumption_kwh", ascending=True)
        ) if "locality" in df.columns else pd.DataFrame()

        if not locality_now.empty:
            fig_bar = go.Figure(go.Bar(
                x=locality_now["consumption_kwh"],
                y=locality_now["locality"],
                orientation="h",
                marker_color=["#38bdf8", "#818cf8", "#34d399", "#fb923c", "#f472b6"],
                text=locality_now["consumption_kwh"].round(3),
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=11, color="#94a3b8")
            ))
            fig_bar.update_layout(
                paper_bgcolor="#0a0e1a", plot_bgcolor="#111827",
                font=dict(family="Syne", color="#94a3b8"),
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=True, gridcolor="#1e293b",
                           color="#334155", title="Avg kWh"),
                yaxis=dict(showgrid=False, color="#334155"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ── Raw stream tail ───────────────────────────────────
    st.markdown(
        "<div class='section-header'>RAW STREAM — LATEST 50 READINGS</div>",
        unsafe_allow_html=True
    )

    display_cols = [c for c in ["timestamp", "meter_id", "locality", "consumption_kwh", "voltage", "anomaly_label"]
                    if c in df.columns]
    tail = df[display_cols].tail(50).copy()
    if "timestamp" in tail.columns:
        tail["timestamp"] = pd.to_datetime(tail["timestamp"], errors="coerce").dt.strftime("%H:%M:%S")
    tail = tail.sort_values("timestamp", ascending=False) if "timestamp" in tail.columns else tail
    st.dataframe(tail, use_container_width=True, hide_index=True, height=220)

    # ── Auto-refresh ──────────────────────────────────────
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
