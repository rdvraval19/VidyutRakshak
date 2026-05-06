"""
VidyutRakshak AI — Demand Forecast Page
Shows 48-hour Prophet forecast with confidence intervals and peak risk shading.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np


@st.cache_data
def load_forecasts():
    return pd.read_csv("data/processed/forecasts.csv", parse_dates=["ds"])


def render():
    forecasts = load_forecasts()

    st.markdown("# 📈 Demand Forecast")
    st.markdown(
        "<div class='section-header'>48-HOUR AHEAD PREDICTION — PROPHET MODEL — VIDYUTRAKSHAK AI</div>",
        unsafe_allow_html=True
    )

    localities = forecasts["locality"].unique().tolist()
    col_sel, col_info = st.columns([1, 3])

    with col_sel:
        selected = st.selectbox("Select Locality", localities)

    loc_df  = forecasts[forecasts["locality"] == selected].copy()
    future  = loc_df[loc_df["is_forecast"] == True]
    history = loc_df[loc_df["is_forecast"] == False]

    with col_info:
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Peak Predicted",  f"{future['yhat'].max():.2f} kWh")
        s2.metric("Avg Predicted",   f"{future['yhat'].mean():.2f} kWh")
        s3.metric("Critical Hours",  len(future[future["risk_level"] == "Critical"]))
        s4.metric("High Risk Hours", len(future[future["risk_level"] == "High Risk"]))

    st.markdown(
        "<div class='section-header'>FORECAST CHART WITH CONFIDENCE INTERVAL</div>",
        unsafe_allow_html=True
    )

    fig = go.Figure()

    # Historical (last 7 days)
    hist_cut = history[history["ds"] >= history["ds"].max() - pd.Timedelta(days=7)]

    fig.add_trace(go.Scatter(
        x=hist_cut["ds"], y=hist_cut["yhat"],
        name="Historical", mode="lines",
        line=dict(color="#334155", width=1.5, dash="dot")
    ))

    # Confidence band
    fig.add_trace(go.Scatter(
        x=pd.concat([future["ds"], future["ds"][::-1]]),
        y=pd.concat([future["yhat_upper"], future["yhat_lower"][::-1]]),
        fill="toself",
        fillcolor="rgba(56,189,248,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        name="90% Confidence Band",
        hoverinfo="skip"
    ))

    # Forecast line
    fig.add_trace(go.Scatter(
        x=future["ds"], y=future["yhat"],
        name="Forecast", mode="lines",
        line=dict(color="#38bdf8", width=2.5)
    ))

    # Risk shading — Critical
    for _, row in future[future["risk_level"] == "Critical"].iterrows():
        fig.add_shape(
            type="rect",
            x0=str(row["ds"]),
            x1=str(row["ds"] + pd.Timedelta(hours=1)),
            y0=0, y1=1,
            xref="x", yref="paper",
            fillcolor="rgba(239,68,68,0.15)",
            line_width=0
        )

    # Risk shading — High Risk
    for _, row in future[future["risk_level"] == "High Risk"].iterrows():
        fig.add_shape(
            type="rect",
            x0=str(row["ds"]),
            x1=str(row["ds"] + pd.Timedelta(hours=1)),
            y0=0, y1=1,
            xref="x", yref="paper",
            fillcolor="rgba(249,115,22,0.10)",
            line_width=0
        )

    # Forecast start marker
    split_time = future["ds"].min()
    y_max = max(future["yhat"].max(), hist_cut["yhat"].max()) if len(hist_cut) > 0 else future["yhat"].max()

    fig.add_trace(go.Scatter(
        x=[split_time, split_time],
        y=[0, y_max * 1.05],
        mode="lines+text",
        line=dict(color="#475569", width=1.5, dash="dash"),
        text=["", "Forecast Start"],
        textposition="top center",
        textfont=dict(color="#475569", size=11, family="JetBrains Mono"),
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#111827",
        font=dict(family="Syne", color="#94a3b8"),
        height=420,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(showgrid=False, color="#334155", title=""),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", color="#334155",
                   title="Consumption (kWh)"),
        legend=dict(bgcolor="#111827", bordercolor="#1e293b",
                    orientation="h", y=-0.15)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Risk Breakdown Table ──────────────────────────────
    st.markdown(
        "<div class='section-header'>HOURLY RISK BREAKDOWN — NEXT 48H</div>",
        unsafe_allow_html=True
    )

    risk_display = future[future["risk_level"] != "Normal"][[
        "ds", "yhat", "yhat_lower", "yhat_upper", "risk_level"
    ]].copy()

    if len(risk_display) == 0:
        st.success("✅ No critical or high-risk hours predicted in next 48h for this locality.")
    else:
        risk_display.columns = ["Timestamp", "Predicted kWh", "Lower Bound", "Upper Bound", "Risk Level"]
        risk_display["Timestamp"]     = risk_display["Timestamp"].dt.strftime("%d %b %H:%M")
        risk_display["Predicted kWh"] = risk_display["Predicted kWh"].round(3)
        risk_display["Lower Bound"]   = risk_display["Lower Bound"].round(3)
        risk_display["Upper Bound"]   = risk_display["Upper Bound"].round(3)
        st.dataframe(risk_display, use_container_width=True, hide_index=True, height=250)

    # ── All-Locality Comparison ───────────────────────────
    st.markdown(
        "<div class='section-header'>ALL-LOCALITY PEAK DEMAND COMPARISON</div>",
        unsafe_allow_html=True
    )

    future_all = forecasts[forecasts["is_forecast"] == True]
    peak_by_loc = future_all.groupby("locality")["yhat"].agg(["max", "mean"]).reset_index()
    peak_by_loc.columns = ["Locality", "Peak kWh", "Avg kWh"]

    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        name="Peak kWh",
        x=peak_by_loc["Locality"],
        y=peak_by_loc["Peak kWh"],
        marker_color="#ef4444",
        text=peak_by_loc["Peak kWh"].round(1),
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=10, color="#94a3b8")
    ))
    fig_compare.add_trace(go.Bar(
        name="Avg kWh",
        x=peak_by_loc["Locality"],
        y=peak_by_loc["Avg kWh"],
        marker_color="#38bdf8",
        text=peak_by_loc["Avg kWh"].round(1),
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=10, color="#94a3b8")
    ))

    fig_compare.update_layout(
        barmode="group",
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#111827",
        font=dict(family="Syne", color="#94a3b8"),
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, color="#334155"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", color="#334155", title="kWh"),
        legend=dict(bgcolor="#111827", bordercolor="#1e293b", font=dict(size=10))
    )
    st.plotly_chart(fig_compare, use_container_width=True)
