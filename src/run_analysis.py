"""Reproducible satellite rainfall gap filling experiment, Kemayoran 2020–2024.

Usage:
  python src/run_analysis.py --mode demo
  python src/run_analysis.py --mode real

DEMO builds SYNTHETIC satellite-like proxies for code testing, not actual research data.
REAL requires data/satellite_daily_station_dates.csv from extract_satellite_gee.py.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
GAUGE_CSV = ROOT / "data" / "kemayoran_gauge_daily_2020_2026.csv"
SATELLITE_CSV = ROOT / "data" / "satellite_daily_station_dates.csv"
PREDICTION_COLS = ["Monthly climatology", "CHIRPS v3 RNL", "IMERG V07", "CHIRPS bias adjusted", "IMERG bias adjusted", "Satellite ensemble"]
SEED = 20261118
plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 160, "axes.spines.top": False, "axes.spines.right": False})


def station_data():
    d = pd.read_csv(GAUGE_CSV, parse_dates=["date"])
    if d["date"].isna().any() or d["date"].duplicated().any():
        raise ValueError("Gauge file has missing/duplicate dates")
    d = d.sort_values("date").reset_index(drop=True)
    d["gauge_mm"] = pd.to_numeric(d["gauge_mm"], errors="coerce")
    if ((d["gauge_mm"] < 0) | (d["gauge_mm"] > 1000)).any():
        raise ValueError("Gauge contains unexpected negative or >1000 mm rainfall; inspect QC")
    expected = pd.date_range(d["date"].min(), d["date"].max(), freq="D")
    if len(expected) != len(d):
        raise ValueError("Station date range incomplete: reindex missing dates first")
    return d


def synthetic_satellite_for_smoke_test(gauge):
    """DEMO ONLY; satellite proxies fabricated from gauge, so scores are NOT science."""
    r = np.random.default_rng(5112026)
    y = gauge["gauge_mm"].to_numpy(float)
    # Fill only for constructing artificial proxies, not for real QC or analysis.
    wet = np.where(np.isfinite(y), y, r.gamma(0.8, 11, len(y)))
    chirps = np.clip(0.62 * wet + r.gamma(1.2, 2.5, len(y)) + r.normal(0, 4, len(y)), 0, None)
    imerg = np.clip(0.86 * wet + r.gamma(1.4, 3, len(y)) + r.normal(0, 7, len(y)), 0, None)
    return pd.DataFrame({"date": gauge["date"], "chirps3_rnl_mm": chirps, "imerg_v07_mm": imerg})


def metrics(observed, predicted, threshold):
    y = np.asarray(observed, float)
    p = np.asarray(predicted, float)
    keep = np.isfinite(y) & np.isfinite(p)
    y, p = y[keep], p[keep]
    if len(y) == 0:
        return dict(n=0, mae=np.nan, rmse=np.nan, bias=np.nan, extreme_mae=np.nan,
                    n_true_extreme=0, true_positive=0, false_negative=0, false_positive=0,
                    recall=np.nan, precision=np.nan, f1=np.nan)
    truth = y >= threshold
    pred = p >= threshold
    tp, fn, fp = int(np.sum(truth & pred)), int(np.sum(truth & ~pred)), int(np.sum(~truth & pred))
    n_exc = int(truth.sum())
    recall = tp / n_exc if n_exc else np.nan
    prec = tp / (tp + fp) if tp + fp else np.nan
    f1 = 2 * recall * prec / (recall + prec) if np.isfinite(recall) and np.isfinite(prec) and recall + prec > 0 else np.nan
    return dict(n=int(len(y)), mae=float(np.mean(np.abs(y - p))),
                rmse=float(np.sqrt(np.mean((y - p)**2))), bias=float(np.mean(p - y)),
                extreme_mae=float(np.mean(np.abs(y[truth] - p[truth]))) if n_exc else np.nan,
                n_true_extreme=n_exc, true_positive=tp, false_negative=fn, false_positive=fp,
                recall=recall, precision=prec, f1=f1)


def _ratio_fit(df, sat_col):
    sub = df.dropna(subset=["gauge_mm", sat_col])
    if len(sub) < 150:
        raise ValueError(f"Insufficient training pairs ({len(sub)}) for {sat_col}")
    ratio = sub["gauge_mm"].sum() / max(sub[sat_col].sum(), 1e-6)
    # Conservative cap avoids pathological correction when satellite series is wrong.
    return float(np.clip(ratio, 0.2, 5.0))


def add_methods(df):
    train = df[df["date"].dt.year.between(2020, 2022)].copy()
    val = df[df["date"].dt.year.eq(2023)].copy()
    if train["gauge_mm"].notna().sum() < 600:
        raise ValueError("Too few train observations (2020–2022)")
    ratios = {"chirps": _ratio_fit(train, "chirps3_rnl_mm"), "imerg": _ratio_fit(train, "imerg_v07_mm")}
    result = df.copy()
    monthly = train.groupby(train["date"].dt.month)["gauge_mm"].median()
    result["Monthly climatology"] = result["date"].dt.month.map(monthly).fillna(train["gauge_mm"].median())
    result["CHIRPS v3 RNL"] = result["chirps3_rnl_mm"].clip(lower=0)
    result["IMERG V07"] = result["imerg_v07_mm"].clip(lower=0)
    result["CHIRPS bias adjusted"] = result["CHIRPS v3 RNL"] * ratios["chirps"]
    result["IMERG bias adjusted"] = result["IMERG V07"] * ratios["imerg"]
    validation = result.loc[result["date"].dt.year.eq(2023)]
    errors = {c: metrics(validation["gauge_mm"], validation[c], threshold=20)["mae"]
              for c in ("CHIRPS bias adjusted", "IMERG bias adjusted")}
    if not all(np.isfinite(v) for v in errors.values()):
        raise ValueError("Missing complete satellite data in 2023 validation")
    inverse = {name: 1 / max(value, 0.1) for name, value in errors.items()}
    z = sum(inverse.values())
    weights = {name: v / z for name, v in inverse.items()}
    a, b = result["CHIRPS bias adjusted"], result["IMERG bias adjusted"]
    wa, wb = weights["CHIRPS bias adjusted"], weights["IMERG bias adjusted"]
    weight_sum = wa * a.notna().astype(float) + wb * b.notna().astype(float)
    result["Satellite ensemble"] = (wa * a.fillna(0) + wb * b.fillna(0)) / weight_sum.replace(0, np.nan)
    validation = result.loc[result["date"].dt.year.eq(2023)]
    choices = {c: metrics(validation["gauge_mm"], validation[c], threshold=20)["mae"] for c in PREDICTION_COLS}
    best = min(choices, key=lambda col: choices[col] if np.isfinite(choices[col]) else np.inf)
    info = {"calibration_ratios": ratios, "validation_inverse_mae_weights": weights,
            "validation_mae_mm": choices, "selected_method_by_val_mae": best}
    return result, info


def choose_mask(test_df, kind, p, rng):
    """Mask observed gauge dates only; same mask is used to compare all methods."""
    candidates = np.flatnonzero(test_df["gauge_mm"].notna().to_numpy() &
                                test_df["chirps3_rnl_mm"].notna().to_numpy() &
                                test_df["imerg_v07_mm"].notna().to_numpy())
    if len(candidates) < 180:
        raise ValueError("Insufficient common 2024 valid station+satellite days")
    count = max(1, int(round(p * len(candidates))))
    if kind == "random":
        return np.sort(rng.choice(candidates, size=count, replace=False))
    if kind == "rainy_stress":
        # Explicit stress scenario: use known hidden truth to preferentially remove rainy days.
        values = test_df.iloc[candidates]["gauge_mm"].to_numpy(float)
        weights = 1 + 12 * (values >= 1) + 15 * (values >= 20)
        weights = weights / weights.sum()
        return np.sort(rng.choice(candidates, size=count, replace=False, p=weights))
    if kind.startswith("block"):
        width = int(kind.replace("block", ""))
        selected = set()
        # Select 3-/7-calendar-day contiguous windows, may include genuine missing days.
        max_pos = len(test_df) - width
        attempts = 0
        allowed = set(map(int, candidates))
        while len(selected) < count and attempts < 1000:
            start = int(rng.integers(0, max_pos + 1))
            selected.update(i for i in range(start, start + width) if i in allowed)
            attempts += 1
        return np.array(sorted(selected), dtype=int)
    raise ValueError(kind)


def simulation(test, threshold, n_reps=100):
    scenarios = [("Random 5%", "random", 0.05), ("Random 10%", "random", 0.10),
                 ("Random 20%", "random", 0.20), ("3-day blocks ~10%", "block3", 0.10),
                 ("7-day blocks ~10%", "block7", 0.10),
                 ("Rain-targeted stress ~10%", "rainy_stress", 0.10)]
    rows = []
    for scen_i, (name, kind, p) in enumerate(scenarios):
        for rep in range(n_reps):
            rng = np.random.default_rng(SEED + scen_i * 10000 + rep)
            ix = choose_mask(test, kind, p, rng)
            tmp = test.copy()
            tmp["gauge_masked"] = tmp["gauge_mm"]
            tmp.loc[ix, "gauge_masked"] = np.nan
            # Retrospective linear interpolation may use future records; not suitable for real-time imputation.
            interpolated = tmp.set_index("date")["gauge_masked"].interpolate(method="time", limit_area="inside")
            tmp["Linear interpolation"] = interpolated.to_numpy()
            hidden = tmp.iloc[ix]
            for method in [*PREDICTION_COLS, "Linear interpolation"]:
                result = metrics(hidden["gauge_mm"], hidden[method], threshold)
                rows.append({"scenario": name, "repeat": rep, "method": method, "hidden_count": len(ix), **result})
    runs = pd.DataFrame(rows)
    summary = runs.groupby(["scenario", "method"], as_index=False).agg(
        repeats=("repeat", "size"), mean_hidden=("hidden_count", "mean"),
        mean_mae=("mae", "mean"), mean_rmse=("rmse", "mean"),
        mean_extreme_mae=("extreme_mae", "mean"),
        mean_recall_when_estimable=("recall", "mean"),
        reps_containing_extremes=("n_true_extreme", lambda s: int((s > 0).sum())),
        cumulative_hidden_extreme_appearances=("n_true_extreme", "sum"),
        cumulative_true_positive=("true_positive", "sum"),
        cumulative_false_negative=("false_negative", "sum"),
    )
    summary["pooled_recall_over_repeats"] = summary["cumulative_true_positive"] / summary["cumulative_hidden_extreme_appearances"].replace(0, np.nan)
    return runs, summary


def write_plot(df, out, name):
    plt.tight_layout()
    plt.savefig(out / name, bbox_inches="tight")
    plt.close()


def make_figures(df, test, year_audit, test_summary, scenario_summary, out, demo):
    mark = "DEMO / SYNTHETIC SATELLITE DATA - NOT RESEARCH RESULTS" if demo else "REAL DATA / QUALITY AND DATE ALIGNMENT REQUIRE VERIFICATION"
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(year_audit["year"].astype(str), year_audit["valid_percent"])
    ax.set_ylim(0, 100); ax.set_ylabel("Valid numeric daily RR (%)")
    ax.set_title("Kemayoran gauge: completeness by year")
    for i, v in enumerate(year_audit["valid_percent"]): ax.text(i, v+0.7, f"{v:.1f}%", ha="center", fontsize=8)
    write_plot(df, out, "01_station_completeness.png")

    small = test[test["date"].between("2024-01-01", "2024-03-31")]
    fig, ax = plt.subplots(figsize=(11, 4))
    for c, label in [("gauge_mm", "Gauge"), ("CHIRPS v3 RNL", "CHIRPS"), ("IMERG V07", "IMERG")]:
        ax.plot(small["date"], small[c], label=label, lw=1.2, alpha=.9)
    ax.set_title("2024 test sample: daily rainfall (" + mark + ")", fontsize=10)
    ax.set_ylabel("mm/day"); ax.legend(ncol=3)
    write_plot(df, out, "02_timeseries_2024.png")

    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for ax, col in zip(axs, ["CHIRPS v3 RNL", "IMERG V07"]):
        pairs = test.dropna(subset=["gauge_mm", col])
        ax.scatter(pairs["gauge_mm"], pairs[col], s=8, alpha=.5)
        hi = max(float(pairs[["gauge_mm", col]].max().max()),1)
        ax.plot([0, hi], [0, hi], ls="--", c="gray")
        ax.set(xlabel="Gauge (mm/day)", ylabel="Satellite (mm/day)", title=col)
    fig.suptitle("Independent 2024 test (" + mark + ")", fontsize=10)
    write_plot(df, out, "03_scatter_test.png")

    fig, ax = plt.subplots(figsize=(10, 4))
    names = ["Monthly climatology", "CHIRPS v3 RNL", "IMERG V07", "CHIRPS bias adjusted", "IMERG bias adjusted", "Satellite ensemble"]
    m = test_summary.set_index("method").reindex(names)
    x = np.arange(len(m)); w=.38
    ax.bar(x-w/2, m["mae"], width=w, label="All days MAE")
    ax.bar(x+w/2, m["extreme_mae"], width=w, label="Extreme days MAE")
    ax.set_xticks(x, ["Monthly\nmedian", "CHIRPS", "IMERG", "CHIRPS\nadjusted", "IMERG\nadjusted", "Ensemble"])
    ax.set_ylabel("MAE (mm/day)"); ax.legend(); ax.set_title("2024 error by rainfall intensity ("+mark+")",fontsize=10)
    write_plot(df, out, "04_mae_all_vs_extreme.png")

    target = scenario_summary[scenario_summary["method"].isin(["CHIRPS v3 RNL", "IMERG V07", "Satellite ensemble", "Linear interpolation"])].copy()
    pivot = target.pivot(index="scenario", columns="method", values="pooled_recall_over_repeats")
    pivot = pivot.reindex(["Random 5%", "Random 10%", "Random 20%", "3-day blocks ~10%", "7-day blocks ~10%", "Rain-targeted stress ~10%"])
    fig, ax = plt.subplots(figsize=(10, 4.5))
    arr = pivot.to_numpy(dtype=float)
    im = ax.imshow(arr, vmin=0, vmax=1, aspect="auto")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, "NA" if not np.isfinite(arr[i,j]) else f"{arr[i,j]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_xticks(np.arange(len(pivot.columns)),pivot.columns,rotation=25,ha="right")
    ax.set_yticks(np.arange(len(pivot.index)),pivot.index)
    ax.set_title("Extreme recall over simulated gaps - repeated days not independent\n"+mark, fontsize=9)
    fig.colorbar(im, ax=ax, label="Recall")
    write_plot(df, out, "05_extreme_recall_simulated_gaps.png")


def run(mode="demo", repeats=100, satellite_file=SATELLITE_CSV):
    if mode not in ("demo", "real"):
        raise ValueError("mode must be demo or real")
    gauge = station_data()
    demo = mode == "demo"
    if demo:
        sat = synthetic_satellite_for_smoke_test(gauge)
    else:
        satellite_file = Path(satellite_file)
        if not satellite_file.exists():
            raise FileNotFoundError(f"REAL satellites not found: {satellite_file}. First run src/extract_satellite_gee.py")
        sat = pd.read_csv(satellite_file, parse_dates=["date"])
        required = {"date", "chirps3_rnl_mm", "imerg_v07_mm"}
        if not required.issubset(sat.columns):
            raise ValueError(f"Missing satellite CSV columns: {required-set(sat.columns)}")
        if sat["date"].duplicated().any():
            raise ValueError("Duplicate satellite date labels")
        for c in ["chirps3_rnl_mm", "imerg_v07_mm"]:
            sat[c] = pd.to_numeric(sat[c], errors="coerce")
            if (sat[c].dropna()<0).any():
                raise ValueError(f"Negative {c}: check dataset no-data value")
        overlap = gauge[gauge["date"].between("2020-01-01", "2024-12-31")][["date", "gauge_mm"]].merge(sat, on="date",how="inner")
        both = int(overlap.dropna(subset=["gauge_mm","chirps3_rnl_mm","imerg_v07_mm"]).shape[0])
        if both < 1200:
            raise ValueError(f"Only {both} fully observed date pairs; expected roughly 1700+. Check GEE extraction and date labeling.")
    df = gauge.merge(sat[["date", "chirps3_rnl_mm", "imerg_v07_mm"]], on="date",how="left", validate="one_to_one")
    df = df[df["date"].between("2020-01-01", "2024-12-31")].copy()
    df, fitted = add_methods(df)
    train = df[df["date"].dt.year.between(2020, 2022)]
    threshold = float(train.loc[train["gauge_mm"] >= 1.0, "gauge_mm"].quantile(0.95))
    val = df[df["date"].dt.year.eq(2023)]
    test = df[df["date"].dt.year.eq(2024)].copy().reset_index(drop=True)
    val_metrics = pd.DataFrame([{"method": c, **metrics(val["gauge_mm"], val[c], threshold)} for c in PREDICTION_COLS])
    test_metrics = pd.DataFrame([{"method": c, **metrics(test["gauge_mm"], test[c], threshold)} for c in PREDICTION_COLS])
    sim_runs, sim_summary = simulation(test, threshold, n_reps=int(repeats))
    target = ROOT / "outputs" / ("DEMO_SYNTHETIC_NOT_SCIENTIFIC" if demo else "REAL_SATELLITE_RESULTS")
    target.mkdir(parents=True, exist_ok=True)
    yr = gauge.assign(year=gauge["date"].dt.year).groupby("year",as_index=False).agg(total=("date","count"), valid=("gauge_mm","count"))
    yr["missing"] = yr["total"]-yr["valid"]
    yr["valid_percent"] = 100*yr["valid"]/yr["total"]
    for name, frame in [
        ("data_merged_with_predictions.csv", df), ("gauge_completeness_by_year.csv",yr),
        ("validation_2023_metrics.csv",val_metrics), ("independent_test_2024_metrics.csv",test_metrics),
        ("simulation_replicate_metrics.csv",sim_runs), ("simulation_summary.csv", sim_summary),
    ]:
        frame.to_csv(target / name, index=False)
    target_missing = df.loc[df["gauge_mm"].isna(), ["date","gauge_mm", *PREDICTION_COLS]].copy()
    target_missing["selected_by_validation"] = target_missing[fitted["selected_method_by_val_mae"]]
    target_missing["WARNING"] = "ESTIMATES ONLY - NOT MEASURED; independent verification unavailable"
    target_missing.to_csv(target / "historical_missing_dates_estimates_NOT_TRUTH.csv", index=False)
    meta = {"mode": mode, "demo": demo, "created_at": datetime.now().isoformat(),
            "station": "Stamet Kemayoran", "lat": -6.15559, "lon": 106.84,
            "train_years": "2020-2022", "validation_years":"2023", "test_years":"2024",
            "extreme_definition": "training 2020–2022 95th percentile of observed wet-day (>=1mm) rainfall",
            "extreme_threshold_mm_per_day": threshold,
            "n_train_gauge_valid": int(train["gauge_mm"].notna().sum()),
            "n_validation_gauge_valid": int(val["gauge_mm"].notna().sum()),
            "n_test_gauge_valid": int(test["gauge_mm"].notna().sum()),
            "simulation_repeats": int(repeats), "seed": SEED,
            "model_fit_info": fitted,
            "warnings": [
                "Numeric gauge values have not passed independent instrument QC.",
                "Confirm whether gauge date is the END of the 07 WIB observation window.",
                "The 5th percentile of masked days may include very few extreme days; interpret recall cautiously.",
                "CHIRPS and IMERG integrate other information and may assimilate some gauges.",
                "Repeated simulations on the same 2024 days are NOT independent samples.",
                "One station does not establish wider generalizability.",
            ]}
    with open(target / "METHODS_AND_ASSUMPTIONS.json", "w",encoding="utf-8") as f:
        json.dump(meta,f,indent=2,ensure_ascii=False)
    make_figures(df, test, yr, test_metrics, sim_summary, target, demo)
    warning = "DEMO DATA: NOT SCIENTIFIC FINDINGS" if demo else "REAL SATELLITE EXTRACTS: DATE CONVENTION MUST BE VERIFIED"
    best_test_mae = test_metrics.dropna(subset=["mae"]).sort_values("mae").iloc[0]
    text = f"""# {'DEMO ONLY — NOT SCIENTIFIC RESULTS' if demo else 'Preliminary results — Kemayoran'}

**{warning}**

- Dataset: Kemayoran gauge 2020–2024, {'SYNTHETIC satellite proxies' if demo else 'CHIRPS v3 RNL and IMERG V07 from GEE'}.
- Train = 2020–2022; validation = 2023; independent test = 2024.
- Daily extreme threshold from training wet days (>= 1 mm): **{threshold:.2f} mm/day** (P95).
- Reference valid days: train {meta['n_train_gauge_valid']}, val {meta['n_validation_gauge_valid']}, test {meta['n_test_gauge_valid']}.
- Selected imputation method by *validation* MAE: **{fitted['selected_method_by_val_mae']}**.
- Lowest *test* overall MAE (descriptive only, not selected by test): {best_test_mae['method']}, {best_test_mae['mae']:.2f} mm/day.

## How to read the outputs

1. `independent_test_2024_metrics.csv` compares errors and extreme-event recall for unmasked test dates.
2. `simulation_summary.csv` summarizes 100 simulated masking repetitions (or the configured repeat count).
3. `historical_missing_dates_estimates_NOT_TRUTH.csv` contains estimates for actual missing dates, which cannot be scored against unavailable truth.
4. `05_extreme_recall_simulated_gaps.png` compares extreme-event detection for different missing patterns.

## Essential caveats

- Satellite estimates are gridded area estimates, not direct point-gauge measurements.
- The date-shift assumption must be checked against the station observation log.
- Extreme-event counts in a single test year can be very small; inspect `n_true_extreme`.
- Repeated masks resample the same dates; the repeated results are not independent replications.
- Do not publish figures from DEMO mode or assert causal effects from this observational comparison.
"""
    (target / "RESULTS_README.md").write_text(text,encoding="utf-8")
    print("\n"+"="*72)
    print(warning)
    print(f"Extreme threshold: {threshold:.2f} mm/day; selected method: {fitted['selected_method_by_val_mae']}")
    print(f"Outputs: {target}")
    print(test_metrics[["method","n","mae","extreme_mae","recall","n_true_extreme"]].to_string(index=False))
    print("="*72)
    return meta, test_metrics, sim_summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description="Run independently evaluated satellite rainfall gap-filling research")
    p.add_argument("--mode",choices=["demo","real"],default="demo")
    p.add_argument("--repeats",type=int,default=100)
    p.add_argument("--satellite-csv",default=str(SATELLITE_CSV))
    args=p.parse_args()
    run(mode=args.mode,repeats=args.repeats,satellite_file=args.satellite_csv)