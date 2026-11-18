"""Pull CHIRPS v3 RNL daily and GPM IMERG V07 permanent half-hourly point values.

This module does NOT fabricate satellite observations. It requires an authorized Google
Earth Engine project. It writes daily rainfall estimates aligned to station labels.

Run: python src/extract_satellite_gee.py --project YOUR_GEE_CLOUD_PROJECT
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
import time
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GEE_CHIRPS = "UCSB-CHC/CHIRPS/V3/DAILY_RNL"
GEE_IMERG = "NASA/GPM_L3/IMERG_V07"


def _chunks(start: str, end_exclusive: str, months: int = 3):
    current = pd.Timestamp(start)
    end = pd.Timestamp(end_exclusive)
    while current < end:
        next_date = min(current + pd.DateOffset(months=months), end)
        yield current.strftime("%Y-%m-%d"), next_date.strftime("%Y-%m-%d")
        current = next_date


def _get_region_to_frame(collection, location, resolution_m: int):
    """Retrieve native-resolution point values without making 100k API calls."""
    response = collection.getRegion(location, resolution_m).getInfo()
    if not response or len(response) <= 1:
        return pd.DataFrame(columns=["timestamp_utc", "value", "pixel_lon", "pixel_lat"])
    df = pd.DataFrame(response[1:], columns=response[0])
    for required in ("time", "precipitation"):
        if required not in df:
            raise RuntimeError(f"Earth Engine getRegion response lacks '{required}'. Fields: {df.columns.tolist()}")
    df["timestamp_utc"] = pd.to_datetime(df["time"], unit="ms", utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["precipitation"], errors="coerce")
    df["pixel_lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["pixel_lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    df = df.dropna(subset=["timestamp_utc"]).sort_values("timestamp_utc")
    if df.duplicated("timestamp_utc").any():
        raise ValueError("More than one pixel value per timestamp; check the selected point/resolution.")
    if (df["value"].dropna() < 0).any():
        raise ValueError("Unexpected negative satellite rain rate; inspect no-data encoding.")
    return df[["timestamp_utc", "value", "pixel_lon", "pixel_lat"]]


def extract(project: str, start: str = "2019-12-31", end_exclusive: str = "2025-01-01",
            date_shift_days: int = 1, lat: float = -6.15559, lon: float = 106.84,
            output_root: Path = ROOT, authenticate: bool = True):
    """For daily gauge date D observed at 07 WIB, UTC-day D-1 is the likely window.

    Date convention is a RESEARCH ASSUMPTION: verify station data_timestamp metadata.
    Use --date-shift-days 0 if gauge values are labeled by start instead of end.
    """
    try:
        import ee
    except ImportError as exc:
        raise RuntimeError("Install google Earth Engine API: pip install earthengine-api") from exc
    if not project or project == "ISI_GOOGLE_CLOUD_PROJECT_ID":
        raise ValueError("Set Google Earth Engine Cloud project ID first (see README).");
    if authenticate:
        ee.Authenticate()
    ee.Initialize(project=project)
    point = ee.Geometry.Point([lon, lat])
    cache = Path(output_root) / "data" / "cache_gee"
    cache.mkdir(parents=True, exist_ok=True)
    frames = {}
    for label, dataset, scale_m in [
        ("chirps", GEE_CHIRPS, 5566),
        ("imerg", GEE_IMERG, 11132),
    ]:
        pieces = []
        for s, e in _chunks(start, end_exclusive, months=3):
            path = cache / f"{label}_{s}_{e}.csv"
            if path.exists():
                df = pd.read_csv(path, parse_dates=["timestamp_utc"])
                print(f"CACHE {label}: {s} through {e}")
            else:
                print(f"GEE {label.upper()}: {s} through {e} ...", flush=True)
                collection = ee.ImageCollection(dataset).filterDate(s, e).select("precipitation")
                if label == "imerg":
                    # Never silently combine provisional and final IMERG products.
                    collection = collection.filter(ee.Filter.eq("status", "permanent"))
                try:
                    df = _get_region_to_frame(collection, point, scale_m)
                except Exception as exc:
                    raise RuntimeError(
                        f"GEE failed for {label} [{s},{e}]. No data were fabricated. "
                        "Try running this cell again; cached successful chunks are reused. "
                        f"Original error: {exc}"
                    ) from exc
                df.to_csv(path, index=False)
                print(f"  Received {len(df):,} time steps")
            pieces.append(df)
            time.sleep(0.15)
        if not pieces:
            raise RuntimeError(f"No data retrieved for {label}")
        full = pd.concat(pieces, ignore_index=True)
        if full.empty:
            raise RuntimeError(f"Empty {label} collection: check availability and final/permanent status")
        full["timestamp_utc"] = pd.to_datetime(full["timestamp_utc"], utc=True)
        full = full.drop_duplicates(subset="timestamp_utc", keep="first")
        full["date_utc"] = full["timestamp_utc"].dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("D")
        full["value"] = pd.to_numeric(full["value"], errors="coerce")
        if label == "chirps":
            daily = full.groupby("date_utc", as_index=False).agg(chirps3_rnl_mm=("value", "mean"), chirps_n=("value", "count"))
            daily.loc[daily["chirps_n"] != 1, "chirps3_rnl_mm"] = float("nan")
        else:
            # GEE IMERG precipitation band is mm/hr, each image = 30 minutes.
            daily = full.groupby("date_utc", as_index=False).agg(
                imerg_n=("value", "count"), n_images=("timestamp_utc", "nunique"),
                rate_sum=("value", "sum"))
            daily["imerg_v07_mm"] = daily["rate_sum"] * 0.5
            daily.loc[(daily["imerg_n"] != 48) | (daily["n_images"] != 48), "imerg_v07_mm"] = float("nan")
            daily = daily.drop(columns="rate_sum")
        daily["date"] = daily["date_utc"] + pd.to_timedelta(date_shift_days, unit="D")
        frames[label] = daily
        daily.to_csv(Path(output_root) / "data" / f"{label}_daily_utc_and_station_date.csv", index=False)
    combined = frames["chirps"][["date", "chirps3_rnl_mm", "chirps_n"]].merge(
        frames["imerg"][["date", "imerg_v07_mm", "imerg_n", "n_images"]], on="date", how="outer", validate="one_to_one")
    combined = combined.sort_values("date")
    combined = combined[(combined["date"] >= pd.Timestamp("2020-01-01")) & (combined["date"] < pd.Timestamp("2025-01-01"))]
    target = Path(output_root) / "data" / "satellite_daily_station_dates.csv"
    combined.to_csv(target, index=False)
    meta = {
        "created_at": datetime.now().isoformat(), "source": "GOOGLE_EARTH_ENGINE_REAL_DATA",
        "chirps_gee_collection": GEE_CHIRPS, "imerg_gee_collection": GEE_IMERG,
        "imerg_status": "permanent only", "location": {"lat": lat, "lon": lon},
        "station_date_shift_from_utc_day": date_shift_days,
        "units": "both daily products mm/day; IMERG sum of 48 half-hour mm/hr times 0.5",
        "alignment_warning": "Assumes gauge timestamp = END date of 07:00 WIB accumulation, which is 00 UTC. Must verify with BMKG metadata.",
        "n_days": len(combined),
        "valid_chirps_days": int(combined["chirps3_rnl_mm"].notna().sum()),
        "valid_imerg_days": int(combined["imerg_v07_mm"].notna().sum())
    }
    with open(Path(output_root) / "data" / "satellite_extraction_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print("Saved", target)
    print(json.dumps(meta, indent=2))
    if meta["valid_chirps_days"] < 1400 or meta["valid_imerg_days"] < 1400:
        print("WARNING: many missing satellite days. Check dataset status, Earth Engine error, or date window.")
    return combined


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Extract authentic satellite point time series via Earth Engine")
    p.add_argument("--project", required=True, help="Earth Engine-enabled Google Cloud project ID")
    p.add_argument("--date-shift-days", type=int, default=1, choices=[-1, 0, 1])
    p.add_argument("--no-authenticate", action="store_true")
    args = p.parse_args()
    extract(project=args.project, date_shift_days=args.date_shift_days, authenticate=not args.no_authenticate)