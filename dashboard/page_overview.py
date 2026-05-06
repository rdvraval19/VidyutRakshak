"""
VidyutRakshak AI — Grid Overview Page
Shows KPIs, zone risk chart, hourly consumption, and risk table.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ── Data Loader ─────────────────────────────────────────
@st.cache_data
def load_data():
    raw        = pd.read_csv("data/raw/smart_meter_data.csv", parse_dates=["timestamp"])
    zone_risk  = pd.read_csv("data/processed/zone_risk_scores.csv")
    anomaly_rp = pd.read_csv("data/processed/anomaly_report.csv")
    return raw, zone_risk, anomaly_rp


# ── Main Render Function ─────────────────────────────────
def render():
    raw, zone_risk, anomaly_rp = load_data()

    st.markdown("# ⚡ Grid Overview")
    st.markdown(
        "<div class='section-header'>REAL-TIME SYSTEM STATUS — VIDYUTRAKSHAK AI</div>",
        unsafe_allow_html=True
    )

    # ── KPI Row ──────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)

    total_kwh      = raw["consumption_kwh"].sum()
    active_m       = raw["meter_id"].nunique()
    anomalies      = len(anomaly_rp)
    p1_alerts      = len(anomaly_rp[anomaly_rp["inspection_priority"].str.contains("P1", na=False)])
    critical_zones = len(zone_risk[zone_risk["risk_tier"].str.contains("Critical", na=False)])

    k1.metric("Total Consumption",  f"{total_kwh/1000:.1f} MWh")
    k2.metric("Active Meters",      f"{active_m}")
    k3.metric("Anomalies Detected", f"{anomalies}")
    k4.metric("P1 Alerts",          f"{p1_alerts}", delta="Immediate Action")
    k5.metric("Critical Zones",     f"{critical_zones}")

    # ── Zone Risk Chart ──────────────────────────────────
    st.markdown("<div class='section-header'>ZONE RISK SCOREBOARD</div>", unsafe_allow_html=True)

    color_map = {
        "Critical": "#ef4444",
        "High":     "#f97316",
        "Moderate": "#eab308",
        "Low":      "#22c55e",
    }
    colors = []
    for tier in zone_risk["risk_tier"]:
        matched = "#38bdf8"
        for key, val in color_map.items():
            if key in str(tier):
                matched = val
                break
        colors.append(matched)

    fig_risk = go.Figure(go.Bar(
        x=zone_risk["locality"],
        y=zone_risk["composite_risk_score"],
        marker_color=colors,
        text=zone_risk["composite_risk_score"].round(1),
        textposition="outside",
        textfont=dict(size=12, color="#94a3b8")
    ))

    fig_risk.update_layout(
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#111827",
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, color="#334155"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", title="Risk Score", color="#334155"),
        font=dict(family="Syne", color="#94a3b8"),
        showlegend=False
    )
    st.plotly_chart(fig_risk, use_container_width=True)

    # ── Bottom Section ───────────────────────────────────
    col_left, col_right = st.columns([1.4, 1])

    # ── Left: Time Series ────────────────────────────────
    with col_left:
        st.markdown(
            "<div class='section-header'>HOURLY CONSUMPTION — ALL LOCALITIES (LAST 7 DAYS)</div>",
            unsafe_allow_html=True
        )

        raw["hour_bucket"] = raw["timestamp"].dt.floor("h")

        hourly = (
            raw.groupby(["hour_bucket", "locality"])["consumption_kwh"]
            .sum()
            .reset_index()
        )

        cutoff = hourly["hour_bucket"].max() - pd.Timedelta(days=7)
        hourly = hourly[hourly["hour_bucket"] >= cutoff]

        fig_line = px.line(
            hourly,
            x="hour_bucket",
            y="consumption_kwh",
            color="locality",
            color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#fb923c", "#f472b6"]
        )

        fig_line.update_layout(
            paper_bgcolor="#0a0e1a",
            plot_bgcolor="#111827",
            height=280,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False, color="#334155", title=""),
            yaxis=dict(showgrid=True, gridcolor="#1e293b", title="kWh", color="#334155"),
            font=dict(family="Syne", color="#94a3b8"),
            legend=dict(bgcolor="#111827", bordercolor="#1e293b", font=dict(size=10))
        )

        st.plotly_chart(fig_line, use_container_width=True)

    # ── Right: Zone Risk Table ────────────────────────────
    with col_right:
        st.markdown(
            "<div class='section-header'>ZONE RISK TABLE</div>",
            unsafe_allow_html=True
        )

        display_cols = [
            "locality",
            "risk_tier",
            "composite_risk_score",
            "critical_hours_next_48h",
            "high_risk_hours_next_48h",
        ]
        available = [c for c in display_cols if c in zone_risk.columns]

        st.dataframe(
            zone_risk[available].rename(columns={
                "locality":                  "Locality",
                "risk_tier":                 "Risk Tier",
                "composite_risk_score":      "Score",
                "critical_hours_next_48h":   "Crit. Hrs",
                "high_risk_hours_next_48h":  "High Hrs",
            }),
            use_container_width=True,
            height=280,
            hide_index=True
        )

    # ── Anomaly Type Breakdown ────────────────────────────
    st.markdown(
        "<div class='section-header'>ANOMALY TYPE BREAKDOWN</div>",
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:
        if "anomaly_type" in anomaly_rp.columns:
            type_counts = anomaly_rp["anomaly_type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            fig_donut = go.Figure(go.Pie(
                labels=type_counts["Type"],
                values=type_counts["Count"],
                hole=0.55,
                marker_colors=["#ef4444", "#f97316", "#eab308", "#38bdf8", "#818cf8", "#34d399"],
                textfont=dict(family="JetBrains Mono", size=10)
            ))
            fig_donut.update_layout(
                paper_bgcolor="#0a0e1a",
                font=dict(family="Syne", color="#94a3b8"),
                height=220,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True,
                legend=dict(bgcolor="#111827", bordercolor="#1e293b", font=dict(size=9))
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    with c2:
        if "inspection_priority" in anomaly_rp.columns:
            priority_counts = anomaly_rp["inspection_priority"].apply(
                lambda x: x.split("—")[0].strip() if "—" in str(x) else str(x)
            ).value_counts().reset_index()
            priority_counts.columns = ["Priority", "Count"]

            fig_priority = go.Figure(go.Bar(
                x=priority_counts["Priority"],
                y=priority_counts["Count"],
                marker_color=["#ef4444", "#f97316", "#eab308", "#22c55e"],
                text=priority_counts["Count"],
                textposition="outside",
                textfont=dict(family="JetBrains Mono", size=11, color="#94a3b8")
            ))
            fig_priority.update_layout(
                paper_bgcolor="#0a0e1a",
                plot_bgcolor="#111827",
                height=220,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, color="#334155"),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", title="Meters", color="#334155"),
                font=dict(family="Syne", color="#94a3b8"),
                showlegend=False
            )
            st.plotly_chart(fig_priority, use_container_width=True)
