"""Generate a fully artificial station example for software testing. Not real data."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    dates = pd.date_range("2020-01-01", "2026-10-31", freq="D")
    rng = np.random.default_rng(20261118)
    wet = rng.uniform(size=len(dates)) < 0.43
    rainfall = np.where(wet, rng.gamma(shape=0.9, scale=18, size=len(dates)), 0.0)
    rainfall[rng.choice(len(dates), size=131, replace=False)] = np.nan
    output = ROOT / "data" / "private" / "demo_synthetic_gauge.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": dates, "gauge_mm": rainfall}).to_csv(output, index=False)
    print(f"DEMO SYNTHETIC STATION DATA ONLY: {output}")
