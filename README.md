# ⚡ VidyutRakshak AI
### Smart Grid Intelligence Platform for BESCOM
> AI-powered Demand Forecasting · Anomaly Detection · Electricity Theft Identification

---

## Problem
BESCOM smart meters generate massive high-frequency data that goes underutilized.
This leads to unpredicted demand spikes, undetected electricity theft, and inefficient
field inspections.

## Solution
VidyutRakshak AI transforms raw smart meter data into predictive, explainable,
and actionable grid intelligence using:
- **Prophet + LSTM** for localized demand forecasting
- **Isolation Forest + Z-score** for anomaly detection
- **Rule-based engine** for theft pattern identification
- **Streamlit dashboard** for real-time operational decision support

---

## Architecture

```
Smart Meter Data (15-min intervals)
│
▼
┌─────────────────────┐     ┌──────────────────────────┐
│  Part A: Forecasting │     │  Part B: Anomaly Detection│
│  ─────────────────  │     │  ──────────────────────── │
│  Prophet model       │     │  Isolation Forest (ML)    │
│  Hourly predictions  │     │  Peer Z-score comparison  │
│  Zone risk scoring   │     │  Theft rule engine        │
│  48h ahead forecast  │     │  Explainability layer     │
└──────────┬──────────┘     └────────────┬─────────────┘
           │                             │
           └──────────┬──────────────────┘
                      ▼
          ┌───────────────────────┐
          │  Streamlit Dashboard  │
          │  Grid Overview        │
          │  Demand Forecast      │
          │  Anomaly Alerts       │
          │  Live Stream          │
          └───────────────────────┘
```

---

## Quick Start

### 1. Setup
```bash
git clone <repo>
cd VidyutRakshak
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### 2. Run full pipeline (one command)
```bash
python run_pipeline.py
```

### 3. Launch dashboard
```bash
streamlit run dashboard/app.py
```

---

## Project Structure

```
VidyutRakshak/
├── data/
│   ├── generate_data.py          # Synthetic smart meter data generator
│   ├── raw/                      # Raw meter readings (576,000 records)
│   └── processed/                # Pipeline outputs
│       ├── forecasts.csv         # 48h demand forecasts per locality
│       ├── zone_risk_scores.csv  # Grid stress risk scores
│       ├── anomaly_profiles.csv  # ML anomaly scores per meter
│       ├── theft_rules_output.csv# Rule-based theft evidence
│       └── anomaly_report.csv    # Final ranked inspection report
├── models/
│   ├── forecaster.py             # Prophet demand forecasting engine
│   ├── zone_risk.py              # Zone stress classifier
│   ├── anomaly_detector.py       # Isolation Forest + Z-score engine
│   ├── theft_rules.py            # Rule-based theft detection
│   └── explainer.py              # Confidence scoring + explanations
├── dashboard/
│   ├── app.py                    # Streamlit app entry point
│   ├── page_overview.py          # Grid overview page
│   ├── page_forecast.py          # Demand forecast page
│   ├── page_anomaly.py           # Anomaly & theft alerts page
│   └── page_live.py              # Live stream page
├── simulator/
│   └── live_anomaly_engine.py    # Real-time anomaly scoring engine
├── run_pipeline.py               # Master pipeline runner
└── requirements.txt
```

---

## Key Features

| Feature | Approach | Output |
|---|---|---|
| Demand Forecasting | Facebook Prophet | Hourly predictions + confidence bands |
| Zone Risk Scoring | Weighted composite score | Risk tier per locality |
| Anomaly Detection | Isolation Forest + Z-score | Anomaly confidence per meter |
| Theft Detection | 5 rule-based patterns | Evidence + rule triggers |
| Explainability | Reasoning traces | Human-readable audit trail |
| Inspection Priority | Confidence-weighted | P1/P2/P3/P4 queue |

---

## Non-Negotiables Addressed

- ✅ No modification to existing BESCOM systems
- ✅ Works as a decision-support layer only
- ✅ Uses synthetic/masked data
- ✅ All outputs are explainable and auditable
- ✅ False positives minimized via dual-method detection
- ✅ No hosted LLM used on sensitive data

---

## Evaluation Metrics

| Metric | Target |
|---|---|
| Forecast MAE | < 10% of mean load |
| Anomaly Precision | > 80% (minimize false positives) |
| Anomaly Recall | > 75% (catch real theft) |
| P1 Alert False Positive Rate | < 5% |
| Dashboard Latency | < 3s page load |

---

## Team
Built for **Smart India Hackathon / BESCOM Theme 8**  
*AI for Smart Meter Intelligence & Loss Detection*
