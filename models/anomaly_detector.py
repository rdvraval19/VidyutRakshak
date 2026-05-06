"""
VidyutRakshak AI — Anomaly Detection Engine
Combines Isolation Forest (ML) + Peer Z-score (statistical) for robust detection.
Dual-method approach minimizes false positives — a key non-negotiable.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings
import os

warnings.filterwarnings("ignore")


def load_and_engineer_features(csv_path="data/raw/smart_meter_data.csv"):
    """
    Load raw meter data and create time-based features.
    """
    print("📂 Loading meter data for anomaly detection...")
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    df["hour"]        = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["week"]        = df["timestamp"].dt.isocalendar().week.astype(int)

    print(f"✅ Loaded {len(df):,} records across {df['meter_id'].nunique()} meters")
    return df


def build_meter_profiles(df):
    """
    Aggregate each meter into a statistical fingerprint.
    This is what Isolation Forest will analyze.
    Rich feature set captures multiple theft/tamper signatures.
    """
    print("🔧 Building meter consumption profiles...")

    profiles = df.groupby(["meter_id", "locality"]).agg(
        mean_consumption   = ("consumption_kwh", "mean"),
        std_consumption    = ("consumption_kwh", "std"),
        max_consumption    = ("consumption_kwh", "max"),
        min_consumption    = ("consumption_kwh", "min"),
        median_consumption = ("consumption_kwh", "median"),
        total_consumption  = ("consumption_kwh", "sum"),
        zero_count         = ("consumption_kwh", lambda x: (x == 0).sum()),
        spike_count        = ("consumption_kwh", lambda x: (x > x.mean() + 3 * x.std()).sum()),
        drop_count         = ("consumption_kwh", lambda x: (x < x.mean() - 2 * x.std()).sum()),
        reading_count      = ("consumption_kwh", "count"),
    ).reset_index()

    # Derived ratios — highly informative for theft/tamper
    profiles["coeff_variation"] = profiles["std_consumption"]  / (profiles["mean_consumption"] + 1e-6)
    profiles["zero_ratio"]      = profiles["zero_count"]       / profiles["reading_count"]
    profiles["spike_ratio"]     = profiles["spike_count"]      / profiles["reading_count"]
    profiles["drop_ratio"]      = profiles["drop_count"]       / profiles["reading_count"]
    profiles["range_ratio"]     = (
        (profiles["max_consumption"] - profiles["min_consumption"])
        / (profiles["mean_consumption"] + 1e-6)
    )

    # Fill NaN std (single-reading meters)
    profiles["std_consumption"] = profiles["std_consumption"].fillna(0)

    print(f"✅ Profiles built for {len(profiles)} meters")
    return profiles


def run_isolation_forest(profiles):
    """
    Isolation Forest isolates anomalies by randomly partitioning features.
    Anomalous meters get isolated faster → lower score.
    contamination = expected fraction of anomalous meters (~8%).
    """
    print("🌲 Running Isolation Forest...")

    feature_cols = [
        "mean_consumption", "std_consumption", "max_consumption",
        "min_consumption", "median_consumption", "coeff_variation",
        "zero_ratio", "spike_ratio", "drop_ratio", "range_ratio"
    ]

    X = profiles[feature_cols].fillna(0)

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso_forest = IsolationForest(
        n_estimators=200,
        contamination=0.08,
        random_state=42,
        max_samples="auto"
    )

    profiles["iso_score"]     = iso_forest.fit_predict(X_scaled)
    profiles["iso_raw_score"] = iso_forest.decision_function(X_scaled)
    profiles["iso_anomaly"]   = profiles["iso_score"] == -1

    flagged = profiles["iso_anomaly"].sum()
    print(f"✅ Isolation Forest flagged {flagged} meters as anomalous")
    return profiles, scaler


def run_peer_zscore_analysis(profiles):
    """
    Compare each meter against its locality peers.
    Catches theft that blends into city-wide averages but stands out locally.
    """
    print("📊 Running peer-level Z-score analysis...")

    results = []

    for locality in profiles["locality"].unique():
        loc_df   = profiles[profiles["locality"] == locality].copy()
        loc_mean = loc_df["mean_consumption"].mean()
        loc_std  = loc_df["mean_consumption"].std() + 1e-6

        loc_df["peer_zscore"]  = (loc_df["mean_consumption"] - loc_mean) / loc_std
        loc_df["peer_anomaly"] = loc_df["peer_zscore"].abs() > 2.0

        loc_df["peer_direction"] = "normal"
        loc_df.loc[loc_df["peer_zscore"] < -2.0, "peer_direction"] = "unusually_low"
        loc_df.loc[loc_df["peer_zscore"] >  2.0, "peer_direction"] = "unusually_high"

        results.append(loc_df)

    profiles     = pd.concat(results, ignore_index=True)
    peer_flagged = profiles["peer_anomaly"].sum()
    print(f"✅ Peer Z-score flagged {peer_flagged} meters as outliers")
    return profiles


def combine_anomaly_signals(profiles):
    """
    Combine Isolation Forest + Peer Z-score into one unified confidence score.
    Both methods agreeing = high confidence → minimizes false positives.
    """
    print("🔗 Combining anomaly signals...")

    profiles["signal_count"] = (
        profiles["iso_anomaly"].astype(int) +
        profiles["peer_anomaly"].astype(int)
    )

    # Normalize iso_raw_score to [0, 1] — lower raw = more anomalous → invert
    min_s = profiles["iso_raw_score"].min()
    max_s = profiles["iso_raw_score"].max()
    profiles["iso_normalized"] = 1 - (profiles["iso_raw_score"] - min_s) / (max_s - min_s + 1e-6)

    # Peer score contribution: clip z-score to [0, 5] then normalize
    profiles["peer_score"] = profiles["peer_zscore"].abs().clip(upper=5) / 5

    # Weighted composite confidence [0, 1]
    profiles["anomaly_confidence"] = (
        0.55 * profiles["iso_normalized"] +
        0.45 * profiles["peer_score"]
    ).clip(0, 1)

    # Final flag: at least one method AND confidence > 0.45
    # Requiring both reduces false positives significantly
    profiles["is_anomalous"] = (
        (profiles["signal_count"] >= 1) &
        (profiles["anomaly_confidence"] > 0.45)
    )

    print(f"✅ Final anomalous meters: {profiles['is_anomalous'].sum()}")
    return profiles


def run_anomaly_detection():
    print("=" * 55)
    print("  VidyutRakshak AI — Anomaly Detection Engine")
    print("=" * 55)

    df       = load_and_engineer_features()
    profiles = build_meter_profiles(df)
    profiles, scaler = run_isolation_forest(profiles)
    profiles = run_peer_zscore_analysis(profiles)
    profiles = combine_anomaly_signals(profiles)

    os.makedirs("data/processed", exist_ok=True)
    profiles.to_csv("data/processed/anomaly_profiles.csv", index=False)
    print("\n💾 Saved → data/processed/anomaly_profiles.csv")
    print("✅ Anomaly detection complete!")
    return profiles, df


if __name__ == "__main__":
    run_anomaly_detection()
