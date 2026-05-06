"""
VidyutRakshak AI — Demand Forecasting Engine
Uses Facebook Prophet to forecast 48-hour demand per locality.
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import warnings
import os

warnings.filterwarnings("ignore")


def load_and_aggregate(csv_path="data/raw/smart_meter_data.csv"):
    """
    Load raw 15-min meter data and aggregate to hourly per locality.
    Prophet works best on hourly or daily granularity.
    """
    print("📂 Loading smart meter data...")
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    df["hour_bucket"] = df["timestamp"].dt.floor("h")

    hourly = (
        df.groupby(["hour_bucket", "locality"])
        .agg(
            total_kwh   = ("consumption_kwh", "sum"),
            avg_voltage = ("voltage", "mean"),
            meter_count = ("meter_id", "nunique")
        )
        .reset_index()
    )

    hourly.rename(columns={"hour_bucket": "timestamp"}, inplace=True)
    print(f"✅ Aggregated to {len(hourly):,} hourly locality records")
    return hourly


def train_forecast_model(hourly_df, locality):
    """
    Train a Prophet model for one locality.
    Prophet needs columns named 'ds' (date) and 'y' (value).
    """
    loc_df = hourly_df[hourly_df["locality"] == locality].copy()
    loc_df = loc_df[["timestamp", "total_kwh"]].rename(
        columns={"timestamp": "ds", "total_kwh": "y"}
    )

    # Sort and remove duplicates
    loc_df = loc_df.sort_values("ds").drop_duplicates("ds")

    # Remove non-positive values (Prophet requires positive y for multiplicative seasonality)
    loc_df = loc_df[loc_df["y"] > 0]

    model = Prophet(
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        interval_width=0.90
    )

    model.fit(loc_df)
    return model, loc_df


def generate_forecast(model, loc_df, forecast_hours=48):
    """Predict next 48 hours of demand for the locality."""
    last_date = loc_df["ds"].max()
    future = model.make_future_dataframe(
        periods=forecast_hours,
        freq="h",
        include_history=True
    )

    forecast = model.predict(future)

    # Clip negative predictions
    forecast["yhat"]       = forecast["yhat"].clip(lower=0)
    forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
    forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)

    forecast["is_forecast"] = forecast["ds"] > last_date
    return forecast


def detect_peak_periods(forecast, locality, threshold_percentile=85):
    """
    Flag hours where predicted demand exceeds the 85th percentile.
    These are HIGH RISK periods for grid stress.
    """
    future_only = forecast[forecast["is_forecast"]].copy()

    if len(future_only) == 0:
        future_only["risk_level"] = []
        return future_only, 0

    threshold    = np.percentile(forecast["yhat"], threshold_percentile)
    crit_thresh  = np.percentile(forecast["yhat"], 95)

    future_only["risk_level"] = "Normal"
    future_only.loc[future_only["yhat"] > threshold,   "risk_level"] = "High Risk"
    future_only.loc[future_only["yhat"] > crit_thresh, "risk_level"] = "Critical"

    print(f"\n⚡ [{locality}] Peak periods in next 48h:")
    print(f"   High Risk  : {len(future_only[future_only['risk_level'] == 'High Risk'])} hours")
    print(f"   Critical   : {len(future_only[future_only['risk_level'] == 'Critical'])} hours")
    print(f"   Threshold  : {threshold:.2f} kWh")

    return future_only, threshold


def save_forecast_results(all_results):
    os.makedirs("data/processed", exist_ok=True)
    combined = pd.concat(all_results, ignore_index=True)
    combined.to_csv("data/processed/forecasts.csv", index=False)
    print(f"\n💾 Forecasts saved → data/processed/forecasts.csv")
    return combined


def run_forecasting_pipeline():
    print("=" * 55)
    print("  VidyutRakshak AI — Demand Forecasting Engine")
    print("=" * 55)

    hourly_df  = load_and_aggregate()
    localities = hourly_df["locality"].unique()

    all_forecasts = []

    for locality in localities:
        print(f"\n🔮 Forecasting: {locality}")

        model, loc_df           = train_forecast_model(hourly_df, locality)
        forecast                = generate_forecast(model, loc_df, forecast_hours=48)
        forecast_with_risk, thr = detect_peak_periods(forecast, locality)

        forecast_with_risk["locality"]      = locality
        forecast_with_risk["threshold_kwh"] = thr

        output_cols = [
            "ds", "locality", "yhat", "yhat_lower", "yhat_upper",
            "risk_level", "threshold_kwh", "is_forecast"
        ]
        all_forecasts.append(forecast_with_risk[output_cols])

    combined = save_forecast_results(all_forecasts)

    print("\n" + "=" * 55)
    print("📊 FORECAST SUMMARY")
    print("=" * 55)
    risk_summary = (
        combined[combined["is_forecast"]]
        .groupby(["locality", "risk_level"])
        .size()
        .unstack(fill_value=0)
    )
    print(risk_summary.to_string())
    print("\n✅ Forecasting pipeline complete!")
    return combined


if __name__ == "__main__":
    run_forecasting_pipeline()
