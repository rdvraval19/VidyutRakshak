import streamlit as st

st.set_page_config(
    page_title="VidyutRakshak AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global CSS ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1220;
    border-right: 1px solid #1e2d4a;
}
section[data-testid="stSidebar"] * {
    color: #94a3b8 !important;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px;
}
[data-testid="metric-container"] label {
    color: #64748b !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 800;
    font-size: 2rem !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px;
    letter-spacing: 0.05em;
    color: #475569 !important;
    background: transparent !important;
    border: none !important;
    padding: 10px 20px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    background: #111827;
    border-radius: 10px;
    border: 1px solid #1e3a5f;
}

/* Headers */
h1, h2, h3 { font-family: 'Syne', sans-serif; font-weight: 800; }

/* Alert cards */
.alert-card {
    background: #111827;
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 8px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.7;
}
.alert-card.p2 { border-left-color: #f97316; }
.alert-card.p3 { border-left-color: #eab308; }
.alert-card.p4 { border-left-color: #22c55e; }

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin-left: 8px;
}
.badge-red    { background: #450a0a; color: #fca5a5; }
.badge-orange { background: #431407; color: #fdba74; }
.badge-yellow { background: #422006; color: #fde047; }
.badge-green  { background: #052e16; color: #86efac; }
.badge-blue   { background: #0c1a3a; color: #7dd3fc; }

.section-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #334155;
    margin: 24px 0 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.success("🚀 Live Smart Grid System")
st.info("⚡ VidyutRakshak AI — Real-time Grid Intelligence (ESP32 Hardware Ready)")

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ VidyutRakshak AI")
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:11px;"
        "color:#334155;letter-spacing:0.1em;margin-bottom:24px'>"
        "BESCOM SMART GRID INTELLIGENCE</div>",
        unsafe_allow_html=True
    )

    page = st.radio(
        "Navigation",
        ["🏠  Grid Overview", "📈  Demand Forecast", "🚨  Anomaly & Theft", "📡  Live Stream"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#1e3a5f'>"
        "DATA SCOPE<br>"
        "Localities : 5<br>"
        "Meters : 100<br>"
        "Interval : 15 min<br>"
        "Period : 60 days<br>"
        "Records : 576,000"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#1e3a5f'>"
        "VidyutRakshak v1.0<br>"
        "BESCOM Theme 8<br>"
        "By Team PROTONOVA"
        "</div>",
        unsafe_allow_html=True
    )

# ── Page routing ─────────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

if "Overview" in page:
    from page_overview import render
    render()
elif "Forecast" in page:
    from page_forecast import render
    render()
elif "Anomaly" in page:
    from page_anomaly import render
    render()
elif "Live" in page:
    from page_live import render
    render()
