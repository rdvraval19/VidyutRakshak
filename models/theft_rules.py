"""
VidyutRakshak AI — Theft Rules Engine
5 deterministic rule-based patterns for electricity theft / meter tampering.
Rule-based layer adds explainability on top of ML detection.
Each rule returns (triggered: bool, evidence: str).
"""

import pandas as pd
import numpy as np
import os


# ── Rule Definitions ─────────────────────────────────────

def rule_sudden_consumption_drop(meter_ts):
    """
    Theft rule: meter consumption drops >70% suddenly and stays low.
    Classic meter bypass / jumper cable signature.
    """
    daily = meter_ts.resample("D", on="timestamp")["consumption_kwh"].sum()
    if len(daily) < 10:
        return False, ""

    rolling_avg    = daily.rolling(7, min_periods=3).mean()
    drop_ratio     = daily / (rolling_avg + 1e-6)
    sustained_drop = (drop_ratio < 0.30).sum()

    if sustained_drop >= 5:
        worst = drop_ratio.min()
        return True, f"Consumption dropped to {worst*100:.0f}% of 7-day baseline for {sustained_drop}+ days"
    return False, ""


def rule_abnormal_night_usage(meter_ts):
    """
    Theft/tamper rule: unusually high consumption at night (1–4 AM)
    when legitimate usage should be minimal.
    Industrial theft often runs equipment at night to avoid detection.
    """
    night = meter_ts[meter_ts["timestamp"].dt.hour.between(1, 4)]
    day   = meter_ts[meter_ts["timestamp"].dt.hour.between(9, 18)]

    if len(night) == 0 or len(day) == 0:
        return False, ""

    night_avg = night["consumption_kwh"].mean()
    day_avg   = day["consumption_kwh"].mean()

    if night_avg > day_avg * 1.6:
        ratio = night_avg / (day_avg + 1e-6)
        return True, (
            f"Night usage ({night_avg:.3f} kWh avg) exceeds day usage "
            f"({day_avg:.3f} kWh avg) by {ratio:.1f}x"
        )
    return False, ""


def rule_high_zero_readings(meter_ts):
    """
    Tamper rule: many zero readings suggest meter interference
    or physical tampering with sensor / CT clamp.
    Legitimate meters rarely produce zero readings for extended periods.
    """
    zero_ratio = (meter_ts["consumption_kwh"] == 0).mean()
    if zero_ratio > 0.12:
        count = int((meter_ts["consumption_kwh"] == 0).sum())
        return True, f"{zero_ratio*100:.1f}% of readings are zero ({count} readings; threshold: 12%)"
    return False, ""


def rule_irregular_spike_pattern(meter_ts):
    """
    Tamper rule: random high spikes followed by zero/near-zero readings.
    Suggests meter bypass with occasional reconnection to avoid complete suspicion.
    """
    mean   = meter_ts["consumption_kwh"].mean()
    std    = meter_ts["consumption_kwh"].std()

    if std == 0:
        return False, ""

    spikes = (meter_ts["consumption_kwh"] > mean + 3.5 * std).sum()
    zeros  = (meter_ts["consumption_kwh"] < 0.01).sum()

    if spikes > 8 and zeros > 20:
        return True, f"{int(spikes)} abnormal spikes + {int(zeros)} near-zero readings (bypass pattern)"
    return False, ""


def rule_peer_deviation(meter_profile, locality_profiles):
    """
    Peer rule: meter consumption is far below locality average.
    Legitimate users in same area should have similar baseline patterns.
    Low consumption vs peers = strong theft indicator.
    """
    locality     = meter_profile["locality"]
    peers        = locality_profiles[locality_profiles["locality"] == locality]
    locality_avg = peers["mean_consumption"].mean()
    meter_avg    = meter_profile["mean_consumption"]

    if locality_avg > 0 and meter_avg < locality_avg * 0.25:
        pct = (meter_avg / locality_avg) * 100
        return True, (
            f"Consumption is {pct:.0f}% of locality average "
            f"(meter: {meter_avg:.3f} kWh vs locality avg: {locality_avg:.3f} kWh)"
        )
    return False, ""


# ── Rule Applier ─────────────────────────────────────────

def apply_theft_rules(raw_df, anomaly_profiles):
    """
    Apply all theft rules to anomalous meters only.
    Only evaluate flagged meters to keep computation lean.
    """
    print("🔍 Applying theft detection rules...")

    suspicious_meters = anomaly_profiles[
        anomaly_profiles["is_anomalous"] == True
    ]["meter_id"].tolist()

    print(f"   Evaluating {len(suspicious_meters)} flagged meters against 5 theft rules...")

    results = []

    for meter_id in suspicious_meters:
        meter_ts      = raw_df[raw_df["meter_id"] == meter_id].copy()
        meter_profile = anomaly_profiles[anomaly_profiles["meter_id"] == meter_id].iloc[0]

        triggered_rules = []
        evidence_list   = []

        rules = [
            ("sudden_drop",    rule_sudden_consumption_drop(meter_ts)),
            ("night_usage",    rule_abnormal_night_usage(meter_ts)),
            ("zero_readings",  rule_high_zero_readings(meter_ts)),
            ("spike_pattern",  rule_irregular_spike_pattern(meter_ts)),
            ("peer_deviation", rule_peer_deviation(meter_profile, anomaly_profiles)),
        ]

        for rule_name, (triggered, evidence) in rules:
            if triggered:
                triggered_rules.append(rule_name)
                evidence_list.append(evidence)

        results.append({
            "meter_id":           meter_id,
            "locality":           meter_profile["locality"],
            "rules_triggered":    len(triggered_rules),
            "triggered_rules":    ", ".join(triggered_rules) if triggered_rules else "none",
            "evidence":           " | ".join(evidence_list) if evidence_list else "No specific rule triggered",
            "mean_consumption":   meter_profile["mean_consumption"],
            "anomaly_confidence": meter_profile["anomaly_confidence"],
            "peer_direction":     meter_profile["peer_direction"],
        })

    rules_df = pd.DataFrame(results)
    matched  = len(rules_df[rules_df["rules_triggered"] > 0])
    print(f"✅ Rules applied. {matched} meters matched at least one theft rule.")
    return rules_df


def run_theft_rules_pipeline():
    print("=" * 55)
    print("  VidyutRakshak AI — Theft Rules Engine")
    print("=" * 55)

    raw_df           = pd.read_csv("data/raw/smart_meter_data.csv", parse_dates=["timestamp"])
    anomaly_profiles = pd.read_csv("data/processed/anomaly_profiles.csv")

    rules_df = apply_theft_rules(raw_df, anomaly_profiles)

    os.makedirs("data/processed", exist_ok=True)
    rules_df.to_csv("data/processed/theft_rules_output.csv", index=False)
    print("💾 Saved → data/processed/theft_rules_output.csv")
    print("✅ Theft rules pipeline complete!")
    return rules_df


if __name__ == "__main__":
    run_theft_rules_pipeline()
