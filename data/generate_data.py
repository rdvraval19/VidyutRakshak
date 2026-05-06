"""
VidyutRakshak AI — Synthetic Smart Meter Data Generator
Generates 576,000 records (5 localities × 20 meters × 60 days × 96 intervals/day)
with realistic daily/weekly patterns and injected anomalies for testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)

# ── Config ────────────────────────────────────────────────
LOCALITIES          = ["Rajajinagar", "Malleshwaram", "Indiranagar", "Whitefield", "Jayanagar"]
METERS_PER_LOCALITY = 20
DAYS                = 60   # 2 months of data
INTERVAL_MINUTES    = 15   # 15-min intervals (like real BESCOM data)

# Locality load multipliers (commercial vs residential mix)
LOCALITY_MULTIPLIERS = {
    "Rajajinagar":  1.2,
    "Malleshwaram": 1.0,
    "Indiranagar":  1.4,
    "Whitefield":   1.8,   # IT hub — high base load
    "Jayanagar":    0.9,
}

# Locality prefix for meter IDs
LOCALITY_PREFIX = {loc: loc[:3].upper() for loc in LOCALITIES}


def base_consumption(hour_float, locality):
    """
    Simulate realistic daily consumption curve with:
    - Morning peak: 6–9 AM (commute, cooking, AC startup)
    - Evening peak: 6–10 PM (return home, cooking, lighting, entertainment)
    - Night low:    12–5 AM (minimal activity)
    """
    morning  = 2.5 * np.exp(-0.5 * ((hour_float - 7.5) / 1.5) ** 2)
    evening  = 4.0 * np.exp(-0.5 * ((hour_float - 20.0) / 2.0) ** 2)
    night    = 0.3

    multiplier = LOCALITY_MULTIPLIERS.get(locality, 1.0)
    return (morning + evening + night) * multiplier


def inject_anomaly(df, meter_id, anomaly_type):
    """
    Inject realistic anomalies into specific meters.
    Each anomaly type simulates a distinct theft/tamper signature.
    """
    mask = df["meter_id"] == meter_id

    if anomaly_type == "theft":
        # Sudden and sustained drop (meter bypassed after day ~25)
        theft_start = np.random.randint(20, 35)
        theft_mask  = mask & (df["day_index"] >= theft_start)
        df.loc[theft_mask, "consumption_kwh"] *= np.random.uniform(0.10, 0.18)
        df.loc[theft_mask, "anomaly_label"]    = "theft"
        df.loc[theft_mask, "anomaly_flag"]     = 1

    elif anomaly_type == "tamper":
        # Irregular spikes + near-zero readings (meter physically tampered)
        n = mask.sum()
        multipliers = np.random.choice([0.05, 3.5], size=n, p=[0.35, 0.65])
        df.loc[mask, "consumption_kwh"] *= multipliers
        df.loc[mask, "anomaly_label"]    = "tamper"
        df.loc[mask, "anomaly_flag"]     = 1

    elif anomaly_type == "spike":
        # Sudden spikes on select days (faulty appliance / illegal high-load)
        spike_days = np.random.choice(range(DAYS), size=7, replace=False)
        spike_mask = mask & (df["day_index"].isin(spike_days))
        df.loc[spike_mask, "consumption_kwh"] *= np.random.uniform(3.5, 5.0)
        df.loc[spike_mask, "anomaly_label"]    = "spike"
        df.loc[spike_mask, "anomaly_flag"]     = 1

    return df


def generate_meter_data():
    """Generate the full synthetic dataset."""
    records           = []
    start_time        = datetime(2024, 1, 1, 0, 0)
    intervals_per_day = (24 * 60) // INTERVAL_MINUTES  # = 96

    for locality in LOCALITIES:
        prefix = LOCALITY_PREFIX[locality]
        mult   = LOCALITY_MULTIPLIERS[locality]

        for meter_num in range(METERS_PER_LOCALITY):
            meter_id = f"{prefix}-{meter_num+1:03d}"

            # Slight per-meter variation so meters aren't identical
            meter_bias = np.random.uniform(0.85, 1.15)

            for day in range(DAYS):
                for interval in range(intervals_per_day):
                    timestamp = start_time + timedelta(
                        days=day, minutes=interval * INTERVAL_MINUTES
                    )
                    hour_float = timestamp.hour + timestamp.minute / 60

                    base       = base_consumption(hour_float, locality) * meter_bias
                    is_weekend = timestamp.weekday() >= 5

                    # Weekend: residential up slightly, commercial down
                    if locality in ["Whitefield", "Indiranagar"]:
                        weekend_factor = 0.65 if is_weekend else 1.0
                    else:
                        weekend_factor = 1.10 if is_weekend else 1.0

                    noise       = np.random.normal(0, 0.07)
                    consumption = max(0.0, (base + noise) * weekend_factor)

                    # Voltage slightly varies around 230V
                    voltage = round(np.random.normal(230, 4), 2)

                    records.append({
                        "timestamp":       timestamp,
                        "meter_id":        meter_id,
                        "locality":        locality,
                        "consumption_kwh": round(consumption, 4),
                        "voltage":         voltage,
                        "current":         round(consumption / 0.23, 4),
                        "day_index":       day,
                        "hour":            timestamp.hour,
                        "is_weekend":      is_weekend,
                        "anomaly_flag":    0,
                        "anomaly_label":   "normal",
                    })

    return pd.DataFrame(records)


def main():
    print("🔄 VidyutRakshak — Generating synthetic smart meter data...")
    df = generate_meter_data()

    # ── Inject anomalies into ~6% of meters ──────────────
    # Each locality gets at least one anomalous meter (theft + tamper/spike)
    anomaly_meters = {
        "RAJ-002": "theft",
        "RAJ-018": "spike",
        "MAL-007": "tamper",
        "MAL-014": "theft",
        "IND-015": "spike",
        "IND-003": "tamper",
        "WHI-003": "theft",
        "WHI-011": "spike",
        "JAY-011": "tamper",
        "JAY-006": "theft",
    }

    for meter_id, anomaly_type in anomaly_meters.items():
        df = inject_anomaly(df, meter_id, anomaly_type)

    # ── Save ──────────────────────────────────────────────
    os.makedirs("data/raw", exist_ok=True)
    output_path = "data/raw/smart_meter_data.csv"
    df.to_csv(output_path, index=False)

    print(f"\n✅ Data generated: {len(df):,} records")
    print(f"📁 Saved to: {output_path}")
    print(f"\n📊 Summary:")
    print(f"   Localities  : {df['locality'].nunique()}")
    print(f"   Meters      : {df['meter_id'].nunique()}")
    print(f"   Date range  : {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"   Anomalous m : {df[df['anomaly_flag']==1]['meter_id'].nunique()} meters injected")
    print(f"   Total records: {len(df):,}")
    print(f"\n   Injected anomalies:")
    for meter_id, atype in anomaly_meters.items():
        print(f"   → {meter_id:<10} ({atype})")


if __name__ == "__main__":
    main()
