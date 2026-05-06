"""
VidyutRakshak AI — Master Pipeline Runner
Run this single file to execute all phases in order.
Usage: python run_pipeline.py
"""

import time
import sys
import os

# ── Pretty printer ────────────────────────────────────────
def section(title):
    print("\n" + "═" * 58)
    print(f"  {title}")
    print("═" * 58)

def step(msg):
    print(f"\n  ▶  {msg}")

def done(msg):
    print(f"  ✅ {msg}")

def warn(msg):
    print(f"  ⚠️  {msg}")

# ── Phase 1: Data Generation ──────────────────────────────
def run_phase1():
    section("PHASE 1 — Synthetic Data Generation")
    step("Generating 576,000 smart meter records...")

    from data.generate_data import main
    main()
    done("Smart meter data ready at data/raw/smart_meter_data.csv")

# ── Phase 2A: Demand Forecasting ─────────────────────────
def run_phase2a():
    section("PHASE 2A — Localized Demand Forecasting (Prophet)")
    step("Training Prophet models for 5 localities...")
    warn("This takes 2-3 minutes. Please wait.")

    from models.forecaster import run_forecasting_pipeline
    run_forecasting_pipeline()
    done("Forecasts saved at data/processed/forecasts.csv")

# ── Phase 2B: Zone Risk ───────────────────────────────────
def run_phase2b():
    section("PHASE 2B — Zone Risk Classification")
    step("Scoring grid stress risk per locality...")

    from models.zone_risk import run_zone_risk_analysis
    run_zone_risk_analysis()
    done("Zone scores saved at data/processed/zone_risk_scores.csv")

# ── Phase 3A: Anomaly Detection ───────────────────────────
def run_phase3a():
    section("PHASE 3A — Anomaly Detection (Isolation Forest + Z-Score)")
    step("Building meter profiles and running ML detection...")

    from models.anomaly_detector import run_anomaly_detection
    run_anomaly_detection()
    done("Anomaly profiles saved at data/processed/anomaly_profiles.csv")

# ── Phase 3B: Theft Rules ─────────────────────────────────
def run_phase3b():
    section("PHASE 3B — Theft Rules Engine")
    step("Applying rule-based theft detection patterns...")

    from models.theft_rules import run_theft_rules_pipeline
    run_theft_rules_pipeline()
    done("Theft rules output saved at data/processed/theft_rules_output.csv")

# ── Phase 3C: Explainer ───────────────────────────────────
def run_phase3c():
    section("PHASE 3C — Explainability Engine")
    step("Generating confidence scores and inspection priorities...")

    from models.explainer import run_explainer_pipeline
    run_explainer_pipeline()
    done("Anomaly report saved at data/processed/anomaly_report.csv")

# ── Final Summary ─────────────────────────────────────────
def print_summary():
    section("PIPELINE COMPLETE — SUMMARY")

    import pandas as pd

    zone   = pd.read_csv("data/processed/zone_risk_scores.csv")
    report = pd.read_csv("data/processed/anomaly_report.csv")

    print()
    print(f"  {'METRIC':<35} VALUE")
    print(f"  {'─'*50}")
    print(f"  {'Smart Meter Records Generated':<35} 576,000")
    print(f"  {'Localities Monitored':<35} 5")
    print(f"  {'Meters Analyzed':<35} 100")
    print(f"  {'Forecast Horizon':<35} 48 hours")
    print(f"  {'Critical Risk Zones':<35} {len(zone[zone['risk_tier'].str.contains('Critical')])}")
    print(f"  {'High Risk Zones':<35} {len(zone[zone['risk_tier'].str.contains('High')])}")
    print(f"  {'Anomalous Meters Detected':<35} {len(report)}")
    print(f"  {'P1 Alerts (Immediate Action)':<35} {len(report[report['inspection_priority'].str.contains('P1')])}")
    print(f"  {'Theft Suspected Cases':<35} {len(report[report['anomaly_type'].str.contains('Theft')])}")
    print(f"  {'Avg Detection Confidence':<35} {report['final_confidence'].mean()*100:.0f}%")

    print()
    print("  ─" * 29)
    print()
    print("  🚀 Launch dashboard with:")
    print("     streamlit run dashboard/app.py")
    print()

# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  ██╗   ██╗██╗██████╗ ██╗   ██╗██╗   ██╗████████╗")
    print("  ██║   ██║██║██╔══██╗╚██╗ ██╔╝██║   ██║╚══██╔══╝")
    print("  ██║   ██║██║██║  ██║ ╚████╔╝ ██║   ██║   ██║   ")
    print("  ╚██╗ ██╔╝██║██║  ██║  ╚██╔╝  ██║   ██║   ██║   ")
    print("   ╚████╔╝ ██║██████╔╝   ██║   ╚██████╔╝   ██║   ")
    print("    ╚═══╝  ╚═╝╚═════╝    ╚═╝    ╚═════╝    ╚═╝   ")
    print()
    print("  ██████╗  █████╗ ██╗  ██╗███████╗██╗  ██╗ █████╗ ██╗  ██╗")
    print("  ██╔══██╗██╔══██╗██║ ██╔╝██╔════╝██║  ██║██╔══██╗██║ ██╔╝")
    print("  ██████╔╝███████║█████╔╝ ███████╗███████║███████║█████╔╝ ")
    print("  ██╔══██╗██╔══██║██╔═██╗ ╚════██║██╔══██║██╔══██║██╔═██╗ ")
    print("  ██║  ██║██║  ██║██║  ██╗███████║██║  ██║██║  ██║██║  ██╗")
    print("  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝")
    print()
    print("  VidyutRakshak AI — Smart Grid Intelligence")
    print("  BESCOM · Demand Forecasting · Loss Detection")
    print()

    start = time.time()

    try:
        run_phase1()
        run_phase2a()
        run_phase2b()
        run_phase3a()
        run_phase3b()
        run_phase3c()
        print_summary()

    except Exception as e:
        print(f"\n  ❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - start
    print(f"  ⏱  Total time: {elapsed/60:.1f} minutes")
