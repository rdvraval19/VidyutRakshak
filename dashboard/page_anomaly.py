"""
VidyutRakshak AI — Anomaly & Theft Detection Page
Shows ML + rule-based anomaly alerts with inspection queue.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


@st.cache_data
def load_data():
    report = pd.read_csv("data/processed/anomaly_report.csv")
    raw    = pd.read_csv("data/raw/smart_meter_data.csv", parse_dates=["timestamp"])
    return report, raw


def priority_class(p):
    if "P1" in str(p): return "alert-card",        "badge-red"
    if "P2" in str(p): return "alert-card p2",      "badge-orange"
    if "P3" in str(p): return "alert-card p3",      "badge-yellow"
    return             "alert-card p4",              "badge-green"


def render():
    report, raw = load_data()

    st.markdown("# 🚨 Anomaly & Theft Detection")
    st.markdown(
        "<div class='section-header'>ML + RULE-BASED DETECTION ENGINE — VIDYUTRAKSHAK AI</div>",
        unsafe_allow_html=True
    )

    # ── KPI Row ──────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Flagged",   len(report))
    k2.metric("P1 — Immediate",  len(report[report["inspection_priority"].str.contains("P1", na=False)]))
    k3.metric("Theft Suspected", len(report[report["anomaly_type"].str.contains("Theft", na=False)]))
    k4.metric("Avg Confidence",  f"{report['final_confidence'].mean()*100:.0f}%")

    # ── Filters ───────────────────────────────────────────
    st.markdown("<div class='section-header'>FILTERS</div>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)

    with f1:
        locality_filter = st.multiselect(
            "Locality",
            options=report["locality"].unique().tolist(),
            default=report["locality"].unique().tolist()
        )
    with f2:
        type_filter = st.multiselect(
            "Anomaly Type",
            options=report["anomaly_type"].unique().tolist(),
            default=report["anomaly_type"].unique().tolist()
        )
    with f3:
        min_conf = st.slider("Min Confidence %", 0, 100, 50)

    filtered = report[
        (report["locality"].isin(locality_filter)) &
        (report["anomaly_type"].isin(type_filter)) &
        (report["final_confidence"] * 100 >= min_conf)
    ].sort_values("final_confidence", ascending=False)

    st.caption(f"Showing **{len(filtered)}** flagged meters matching filters.")

    # ── Charts Row ────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("<div class='section-header'>ANOMALIES BY TYPE</div>", unsafe_allow_html=True)
        if len(filtered) > 0:
            type_counts = filtered["anomaly_type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            fig_donut = go.Figure(go.Pie(
                labels=type_counts["Type"],
                values=type_counts["Count"],
                hole=0.6,
                marker_colors=["#ef4444", "#f97316", "#eab308", "#38bdf8", "#818cf8", "#34d399"],
                textfont=dict(family="JetBrains Mono", size=11)
            ))
            fig_donut.update_layout(
                paper_bgcolor="#0a0e1a",
                font=dict(family="Syne", color="#94a3b8"),
                height=260, margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(bgcolor="#111827", bordercolor="#1e293b", font=dict(size=10))
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No anomalies match current filters.")

    with c2:
        st.markdown("<div class='section-header'>CONFIDENCE DISTRIBUTION</div>", unsafe_allow_html=True)
        if len(filtered) > 0:
            fig_hist = go.Figure(go.Histogram(
                x=filtered["final_confidence"] * 100,
                nbinsx=15,
                marker_color="#38bdf8",
                marker_line=dict(color="#0a0e1a", width=1)
            ))
            fig_hist.update_layout(
                paper_bgcolor="#0a0e1a", plot_bgcolor="#111827",
                font=dict(family="Syne", color="#94a3b8"),
                height=260, margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showgrid=False, color="#334155", title="Confidence %"),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", color="#334155", title="Meters"),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

    # ── Meter Detail + Alert Cards ────────────────────────
    detail_col, alert_col = st.columns([1, 1.6])

    with detail_col:
        st.markdown("<div class='section-header'>METER CONSUMPTION TRACE</div>", unsafe_allow_html=True)

        if len(filtered) == 0:
            st.info("No meters to inspect with current filters.")
        else:
            selected_meter = st.selectbox(
                "Select meter to inspect",
                options=filtered["meter_id"].tolist()
            )

            meter_ts = raw[raw["meter_id"] == selected_meter].copy()
            meter_ts["day"] = meter_ts["timestamp"].dt.floor("D")
            daily = meter_ts.groupby("day")["consumption_kwh"].sum().reset_index()

            # Peer average for same locality
            meter_locality = filtered[filtered["meter_id"] == selected_meter]["locality"].values[0]
            peers = raw[raw["locality"] == meter_locality]
            peer_daily = peers.groupby(
                [peers["timestamp"].dt.floor("D"), "meter_id"]
            )["consumption_kwh"].sum().reset_index()
            peer_avg = peer_daily.groupby("timestamp")["consumption_kwh"].mean().reset_index()

            fig_trace = go.Figure()
            fig_trace.add_trace(go.Scatter(
                x=peer_avg["timestamp"], y=peer_avg["consumption_kwh"],
                name="Locality Avg", mode="lines",
                line=dict(color="#334155", width=1.5, dash="dot")
            ))
            fig_trace.add_trace(go.Scatter(
                x=daily["day"], y=daily["consumption_kwh"],
                name=selected_meter, mode="lines+markers",
                line=dict(color="#ef4444", width=2),
                marker=dict(size=5, color="#ef4444")
            ))
            fig_trace.update_layout(
                paper_bgcolor="#0a0e1a", plot_bgcolor="#111827",
                font=dict(family="Syne", color="#94a3b8"),
                height=280, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, color="#334155", title=""),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", color="#334155", title="Daily kWh"),
                legend=dict(bgcolor="#111827", bordercolor="#1e293b", font=dict(size=10))
            )
            st.plotly_chart(fig_trace, use_container_width=True)

            # ── Detailed explanation ──────────────────────
            st.markdown("<div class='section-header'>AUDIT TRAIL</div>", unsafe_allow_html=True)
            row = filtered[filtered["meter_id"] == selected_meter].iloc[0]
            explanation = row.get("explanation", "No explanation available.")
            st.code(str(explanation), language=None)

    with alert_col:
        st.markdown("<div class='section-header'>INSPECTION ALERT QUEUE</div>", unsafe_allow_html=True)

        if len(filtered) == 0:
            st.success("✅ No meters flagged with current filter settings.")
        else:
            for _, row in filtered.iterrows():
                card_class, badge_class = priority_class(row["inspection_priority"])
                conf_pct  = f"{row['final_confidence']*100:.0f}%"
                rules     = str(row.get("triggered_rules", "none"))
                evidence  = str(row.get("evidence", ""))[:140]

                st.markdown(f"""
                <div class="{card_class}">
                    <strong style="color:#e2e8f0">{row['meter_id']}</strong>
                    <span class="badge {badge_class}">{row['inspection_priority'].split('—')[0].strip()}</span>
                    <span class="badge badge-blue">{conf_pct} confidence</span>
                    <br>
                    <span style="color:#64748b">{row['locality']}</span>
                    &nbsp;·&nbsp;
                    <span style="color:#94a3b8">{row['anomaly_type']}</span>
                    <br>
                    <span style="color:#475569;font-size:11px">Rules: {rules}</span>
                    <br>
                    <span style="color:#334155;font-size:11px">{evidence}{'...' if len(str(row.get('evidence',''))) > 140 else ''}</span>
                </div>
                """, unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────
    st.markdown("<div class='section-header'>EXPORT</div>", unsafe_allow_html=True)
    st.download_button(
        label="⬇️ Download Inspection Report (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="vidyutrakshak_inspection_report.csv",
        mime="text/csv"
    )
