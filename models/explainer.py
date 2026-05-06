"""
VidyutRakshak AI — Explainability Engine
Generates human-readable audit trails for every flagged meter.
Assigns inspection priority tiers for field teams.
Non-negotiable: all outputs must be explainable and auditable.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime


def classify_anomaly_type(row):
    """
    Assign human-readable anomaly type based on triggered rules + peer direction.
    Order matters: more specific types checked first.
    """
    rules     = str(row.get("triggered_rules", ""))
    direction = str(row.get("peer_direction", ""))

    if "sudden_drop" in rules and "peer_deviation" in rules:
        return "Electricity Theft (Bypass — High Confidence)"
    elif "sudden_drop" in rules or "peer_deviation" in rules:
        return "Electricity Theft (Bypass Suspected)"
    elif "spike_pattern" in rules and "zero_readings" in rules:
        return "Meter Tampering (Spike + Zero Pattern)"
    elif "spike_pattern" in rules or "zero_readings" in rules:
        return "Meter Tampering Suspected"
    elif "night_usage" in rules:
        return "Illegal Load / Unauthorized Night Usage"
    elif direction == "unusually_high":
        return "Abnormal High Consumption"
    elif direction == "unusually_low":
        return "Suspicious Low Consumption"
    else:
        return "Statistical Anomaly (ML Detected)"


def compute_final_confidence(row):
    """
    Final confidence score combining:
    - ML anomaly confidence (Isolation Forest + Z-score)
    - Number of theft rules triggered (each +10%, max +35%)
    - Strong peer deviation (+10%)
    Scale: 0.0 to 0.99
    """
    base             = float(row.get("anomaly_confidence", 0.5))
    rules_triggered  = int(row.get("rules_triggered", 0))
    rule_boost       = min(rules_triggered * 0.10, 0.35)
    direction        = str(row.get("peer_direction", "normal"))
    peer_boost       = 0.10 if direction != "normal" else 0.0

    return round(min(base + rule_boost + peer_boost, 0.99), 3)


def assign_inspection_priority(confidence, rules_triggered):
    """
    Convert confidence + rule count to actionable priority tier
    for field inspection teams.
    P1 → immediate, P2 → 48h, P3 → this week, P4 → monitor.
    """
    if confidence >= 0.80 or rules_triggered >= 3:
        return "P1 — Immediate Inspection Required"
    elif confidence >= 0.65 or rules_triggered >= 2:
        return "P2 — Inspect Within 48 Hours"
    elif confidence >= 0.50 or rules_triggered >= 1:
        return "P3 — Schedule Inspection This Week"
    else:
        return "P4 — Monitor and Review"


def build_explanation(row):
    """
    Build a structured, human-readable explanation for each flagged meter.
    Designed to be auditable by field engineers without ML background.
    """
    confidence   = row["final_confidence"]
    anomaly_type = row["anomaly_type"]
    evidence     = str(row.get("evidence", ""))
    mean_kwh     = float(row.get("mean_consumption", 0))

    lines = [
        "=" * 55,
        f"VIDYUTRAKSHAK AI — METER INSPECTION REPORT",
        "=" * 55,
        f"METER ID       : {row.get('meter_id', 'Unknown')}",
        f"LOCALITY       : {row.get('locality', 'Unknown')}",
        f"ANOMALY TYPE   : {anomaly_type}",
        f"CONFIDENCE     : {confidence*100:.0f}%",
        f"AVG CONSUMPTION: {mean_kwh:.4f} kWh per 15-min interval",
        f"PRIORITY       : {row['inspection_priority']}",
        f"GENERATED AT   : {row.get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}",
        "",
        "EVIDENCE:",
    ]

    if evidence and evidence != "No specific rule triggered":
        for piece in evidence.split(" | "):
            lines.append(f"  → {piece.strip()}")
    else:
        lines.append("  → Statistical deviation detected by ML model")
        lines.append(f"  → Anomaly confidence: {confidence*100:.0f}%")
        lines.append(f"  → Peer deviation direction: {row.get('peer_direction', 'unknown')}")

    lines.append("")
    lines.append("RECOMMENDATION:")

    if "Theft" in anomaly_type and "High Confidence" in anomaly_type:
        lines += [
            "  → PRIORITY SITE VISIT: Physical meter inspection required",
            "  → Check for bypass wiring, jumper cables, or meter cover tampering",
            "  → Compare meter index with billing records",
            "  → Consider installing anti-tamper seal and CCTV monitoring",
        ]
    elif "Theft" in anomaly_type:
        lines += [
            "  → Physical meter inspection + site visit recommended",
            "  → Check for bypass wiring or meter cover tampering",
            "  → Compare meter readings with manual spot check",
        ]
    elif "Tamper" in anomaly_type:
        lines += [
            "  → Verify meter seal integrity (look for seal breakage)",
            "  → Compare meter readings with manual spot check",
            "  → Check CT clamp connections if smart meter installed",
        ]
    elif "Illegal Load" in anomaly_type or "Night" in anomaly_type:
        lines += [
            "  → Verify sanctioned load vs actual connected load",
            "  → Inspect premises for unauthorized high-load equipment",
            "  → Review billing for billing-consumption mismatch",
        ]
    else:
        lines += [
            "  → Monitor for next 7 days before escalation",
            "  → Compare with historical baseline for this meter",
        ]

    lines.append("=" * 55)
    return "\n".join(lines)


def run_explainer_pipeline():
    print("=" * 55)
    print("  VidyutRakshak AI — Explainability Engine")
    print("=" * 55)

    anomaly_profiles = pd.read_csv("data/processed/anomaly_profiles.csv")
    theft_rules_df   = pd.read_csv("data/processed/theft_rules_output.csv")

    # Merge ML scores + rule outputs
    merged = theft_rules_df.merge(
        anomaly_profiles[[
            "meter_id", "anomaly_confidence", "peer_direction",
            "iso_normalized", "peer_score"
        ]],
        on="meter_id", how="left"
    )

    # Enrich with explainability columns
    merged["anomaly_type"]        = merged.apply(classify_anomaly_type, axis=1)
    merged["final_confidence"]    = merged.apply(compute_final_confidence, axis=1)
    merged["inspection_priority"] = merged.apply(
        lambda r: assign_inspection_priority(r["final_confidence"], r["rules_triggered"]), axis=1
    )
    merged["generated_at"]        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged["explanation"]         = merged.apply(build_explanation, axis=1)

    # Sort by confidence descending (P1 at top)
    merged = merged.sort_values("final_confidence", ascending=False).reset_index(drop=True)

    os.makedirs("data/processed", exist_ok=True)
    merged.to_csv("data/processed/anomaly_report.csv", index=False)

    # Print console summary
    print("\n" + "=" * 55)
    print("🚨 ANOMALY DETECTION REPORT — VIDYUTRAKSHAK AI")
    print("=" * 55)
    print(f"\n{'Meter ID':<14} {'Locality':<14} {'Type':<40} {'Conf':>6} {'Priority'}")
    print("-" * 100)

    for _, row in merged.iterrows():
        print(
            f"{row['meter_id']:<14} "
            f"{row['locality']:<14} "
            f"{row['anomaly_type']:<40} "
            f"{row['final_confidence']*100:>5.0f}%"
            f"  {row['inspection_priority']}"
        )

    print(f"\n\n{'='*55}")
    print("📋 DETAILED AUDIT — TOP FLAGGED METER")
    print("=" * 55)
    if len(merged) > 0:
        top = merged.iloc[0]
        print(f"\n{top['explanation']}")

    print(f"\n\n💾 Full report saved → data/processed/anomaly_report.csv")
    print("✅ Explainability engine complete!")
    return merged


if __name__ == "__main__":
    run_explainer_pipeline()
