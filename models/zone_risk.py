"""
VidyutRakshak AI — Zone Risk Classifier
Scores each locality on grid stress risk using a weighted composite score.
Combines: peak frequency, demand volatility, average load pressure.
"""

import pandas as pd
import numpy as np
import os


def compute_zone_risk_scores(forecast_df, hourly_df):
    """
    Score each locality on overall grid stress risk for the next 48 hours.
    """
    results    = []
    localities = forecast_df["locality"].unique()

    for locality in localities:
        loc_forecast   = forecast_df[
            (forecast_df["locality"] == locality) &
            (forecast_df["is_forecast"] == True)
        ]
        loc_historical = hourly_df[hourly_df["locality"] == locality]

        if len(loc_forecast) == 0:
            continue

        # ── Metric 1: Peak frequency score ───────────────
        total_hours    = len(loc_forecast)
        high_risk_hrs  = len(loc_forecast[loc_forecast["risk_level"] == "High Risk"])
        critical_hrs   = len(loc_forecast[loc_forecast["risk_level"] == "Critical"])
        # Critical hours weighted 2x
        peak_score     = (high_risk_hrs + critical_hrs * 2) / total_hours * 100

        # ── Metric 2: Demand volatility ───────────────────
        if len(loc_historical) > 1:
            hist_mean   = loc_historical["total_kwh"].mean()
            hist_std    = loc_historical["total_kwh"].std()
            volatility  = hist_std / (hist_mean + 1e-6)
        else:
            volatility  = 0
        volatility_score = min(volatility * 100, 100)

        # ── Metric 3: Average load pressure ──────────────
        avg_load   = loc_forecast["yhat"].mean()
        max_load   = loc_forecast["yhat"].max()
        load_score = (avg_load / (max_load + 1e-6)) * 100

        # ── Composite risk score (weighted) ──────────────
        composite = (
            0.45 * peak_score +
            0.30 * volatility_score +
            0.25 * load_score
        )

        # ── Risk tier ─────────────────────────────────────
        if composite >= 65:
            tier = "🔴 Critical"
        elif composite >= 40:
            tier = "🟠 High"
        elif composite >= 20:
            tier = "🟡 Moderate"
        else:
            tier = "🟢 Low"

        results.append({
            "locality":                  locality,
            "peak_score":                round(peak_score, 2),
            "volatility_score":          round(volatility_score, 2),
            "load_score":                round(load_score, 2),
            "composite_risk_score":      round(composite, 2),
            "risk_tier":                 tier,
            "critical_hours_next_48h":   int(critical_hrs),
            "high_risk_hours_next_48h":  int(high_risk_hrs),
            "avg_predicted_kwh":         round(avg_load, 3),
            "max_predicted_kwh":         round(max_load, 3),
        })

    return pd.DataFrame(results).sort_values("composite_risk_score", ascending=False)


def run_zone_risk_analysis():
    print("=" * 55)
    print("  VidyutRakshak AI — Zone Risk Classifier")
    print("=" * 55)

    forecast_df = pd.read_csv("data/processed/forecasts.csv", parse_dates=["ds"])
    forecast_df["is_forecast"] = forecast_df["is_forecast"].astype(bool)

    raw_df = pd.read_csv("data/raw/smart_meter_data.csv", parse_dates=["timestamp"])
    raw_df["hour_bucket"] = raw_df["timestamp"].dt.floor("h")
    hourly_df = (
        raw_df.groupby(["hour_bucket", "locality"])
        .agg(total_kwh=("consumption_kwh", "sum"))
        .reset_index()
        .rename(columns={"hour_bucket": "timestamp"})
    )

    zone_risk_df = compute_zone_risk_scores(forecast_df, hourly_df)

    os.makedirs("data/processed", exist_ok=True)
    zone_risk_df.to_csv("data/processed/zone_risk_scores.csv", index=False)

    print("\n📍 ZONE RISK REPORT (Next 48 Hours)\n")
    print(f"{'Locality':<16} {'Risk Tier':<16} {'Score':>7} {'Critical Hrs':>13} {'Max kWh':>10}")
    print("-" * 65)
    for _, row in zone_risk_df.iterrows():
        print(
            f"{row['locality']:<16} {row['risk_tier']:<16} "
            f"{row['composite_risk_score']:>7.1f} "
            f"{row['critical_hours_next_48h']:>13} "
            f"{row['max_predicted_kwh']:>10.2f}"
        )

    print("\n💾 Zone scores saved → data/processed/zone_risk_scores.csv")
    print("✅ Zone risk analysis complete!")
    return zone_risk_df


if __name__ == "__main__":
    run_zone_risk_analysis()
