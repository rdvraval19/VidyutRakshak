"""
VidyutRakshak AI — Live Anomaly Scorer
Reads the live stream CSV and scores each meter in real time.
Called by the dashboard — not a separate process.
Uses lightweight statistical scoring (no heavy ML) for sub-second response.
"""

import pandas as pd
import numpy as np
import json
import os

LIVE_CSV   = "data/live/live_stream.csv"
STATS_JSON = "data/live/stream_stats.json"


def load_live_stream():
    """Load live stream data. Returns None if not started yet."""
    if not os.path.exists(LIVE_CSV):
        return None
    try:
        df = pd.read_csv(LIVE_CSV, parse_dates=["timestamp"])
        return df if len(df) > 0 else None
    except Exception:
        return None


def load_stats():
    """Load pre-computed stats JSON for fast KPI reading."""
    if not os.path.exists(STATS_JSON):
        return None
    try:
        with open(STATS_JSON) as f:
            return json.load(f)
    except Exception:
        return None


def score_live_meters(df):
    """
    Score each meter from the live stream.
    Fast lightweight scoring — no heavy ML, just stats.
    Suitable for real-time dashboard updates every 3 seconds.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()

    # Ensure numeric types
    df["consumption_kwh"] = pd.to_numeric(df["consumption_kwh"], errors="coerce").fillna(0)
    df["anomaly_flag"]    = pd.to_numeric(df.get("anomaly_flag", 0), errors="coerce").fillna(0)
    df["anomaly_label"]   = df.get("anomaly_label", pd.Series(["normal"] * len(df))).fillna("normal")

    group_cols = [c for c in ["meter_id", "locality"] if c in df.columns]
    if not group_cols:
        return pd.DataFrame()

    profiles = df.groupby(group_cols).agg(
        mean_kwh       = ("consumption_kwh", "mean"),
        std_kwh        = ("consumption_kwh", "std"),
        max_kwh        = ("consumption_kwh", "max"),
        anomaly_count  = ("anomaly_flag",    "sum"),
        total_readings = ("consumption_kwh", "count"),
        last_kwh       = ("consumption_kwh", "last"),
        last_label     = ("anomaly_label",   "last"),
    ).reset_index()

    profiles["std_kwh"]      = profiles["std_kwh"].fillna(0)
    profiles["anomaly_rate"] = profiles["anomaly_count"] / profiles["total_readings"]

    # Peer Z-score within locality (if locality column exists)
    if "locality" in profiles.columns:
        locality_means          = profiles.groupby("locality")["mean_kwh"].transform("mean")
        locality_stds           = profiles.groupby("locality")["mean_kwh"].transform("std").fillna(1e-6) + 1e-6
        profiles["peer_zscore"] = (profiles["mean_kwh"] - locality_means) / locality_stds
    else:
        profiles["peer_zscore"] = 0

    # Live confidence score [0, 1]
    profiles["live_confidence"] = (
        0.5 * profiles["anomaly_rate"].clip(0, 1) +
        0.3 * (profiles["peer_zscore"].abs().clip(0, 5) / 5) +
        0.2 * ((profiles["std_kwh"] / (profiles["mean_kwh"] + 1e-6)).clip(0, 2) / 2)
    ).clip(0, 1).round(3)

    profiles["is_live_anomaly"] = (
        (profiles["anomaly_count"] > 0) |
        (profiles["live_confidence"] > 0.45)
    )

    label_map = {
        "normal": "🟢 Normal",
        "theft":  "🔴 Theft Detected",
        "tamper": "🟠 Tamper Detected",
        "spike":  "🟡 Spike Detected",
    }
    profiles["live_status"] = profiles["last_label"].map(label_map).fillna("🟢 Normal")

    return profiles.sort_values("live_confidence", ascending=False).reset_index(drop=True)


def get_locality_timeseries(df):
    """Aggregate live data to locality level for chart rendering."""
    if df is None or "locality" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["consumption_kwh"] = pd.to_numeric(df["consumption_kwh"], errors="coerce").fillna(0)

    if "timestamp" in df.columns:
        df["minute_bucket"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.floor("min")
    else:
        from datetime import datetime
        df["minute_bucket"] = datetime.now()

    ts = (
        df.groupby(["minute_bucket", "locality"])["consumption_kwh"]
        .sum().reset_index()
    )
    return ts
