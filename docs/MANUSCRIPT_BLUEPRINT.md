# Manuscript template — placeholder text, not a scientific result

## Provisional title

**Satellite-Guided Reconstruction of Missing Daily Rainfall at Kemayoran, Indonesia: Performance Across Missingness Patterns and Heavy-Rainfall Days**

> Working draft only. Do not submit this template without genuine satellite retrieval, independent checks, an updated literature review, source-data permission, and robustness analysis.

## Abstract (fill after actual experiment)

*Context*: Reliable rainfall series are needed for hydrometeorological analysis, but operational gauges contain missing observations. Satellite-gridded precipitation products offer alternative estimates; however, their performance on heavy-rainfall days may differ from their overall accuracy.

*Methods*: We used gauge observations at Kemayoran, Jakarta, during [years]. CHIRPS v3 RNL and IMERG V07 precipitation products were matched by [verified accumulation-period convention]. We fitted simple gauge-to-product bias adjustments using 2020–2022, chose or weighted methods using 2023 validation, and evaluated withheld gauge observations in 2024 under six masking scenarios.

*Results*: **[FILL ONLY FROM REAL DATA]**. Report n matched days, P95 threshold, MAE, heavy-rainfall MAE, event counts, recall, and uncertainty.

*Conclusion*: **[FILL ONLY IF SUPPORTED]**.

## Introduction (research problem)

1. Gauge observations are sparse and occasionally incomplete, especially problematic for rare extremes.
2. Satellite precipitation datasets offer spatial coverage but may smooth local convective extremes and contain systematic biases.
3. Gridded products may match monthly totals while missing individual heavy-rainfall dates.
4. Proposed question: Does the method that minimizes ordinary daily error also preserve rare heavy-rainfall classifications under different missingness mechanisms?
5. Avoid a novelty claim until checking comparable studies in Indonesia and the tropics.

## Methods

### 2.1 Gauge data and QC
- `Stamet Kemayoran`, latitude -6.15559°, longitude 106.84°; daily gauge RR 2020–2026 supplied by user; main experiment 2020–2024.
- Conversion 8888 / 9999 to NaN; no other arbitrary removal. Verify unit, QA flags, observation-window dating and access permissions.

### 2.2 Satellite products
- CHIRPS v3 `DAILY_RNL` (daily precipitation mm/day; ERA5 temporal disaggregation).
- NASA GPM IMERG V07 permanent `precipitation` (mm/hr half-hourly × 0.5; require 48 valid slots/day).
- Point extraction from nearest spatial grid center; document grid center coordinates and resolutions.

### 2.3 Calibration and splits
- Train 2020–2022, validation 2023, test 2024 (chronological).
- Monthly gauge median baseline; raw satellite inputs; ratio-adjusted satellite inputs (fit on training); inverse-validation-MAE weighted ensemble.
- Never select the winning method using 2024.

### 2.4 Missingness experiments
- Random 5%, 10%, 20% masked valid dates.
- 3-day/7-day block ~10% masking.
- Rain-targeted masking as a deliberately strong MNAR stress test (depends on hidden truth; not a model of actual equipment failures).
- Retrospective linear interpolation as baseline; future observations may be used.

### 2.5 Evaluation
- Daily MAE/RMSE/bias, extreme-day MAE, precision/recall/F1 based on fixed P95 of train days with >=1 mm rainfall.
- 100 Monte Carlo masks quantify sensitivity to mask placement but do not establish independent sampling confidence intervals.
- Report sample sizes, number of extreme dates, and absent predictions per model.

## Results — fill from real outputs only

**Table 1:** Data completeness per year and product.

**Table 2:** `independent_test_2024_metrics.csv` (all methods).

**Table 3:** `simulation_summary.csv` (all scenarios, missing counts, true extreme cases, recall).

**Figures:** station completeness; 2024 seasonal time series; scatter; MAE all/extreme; recall by missingness.

## Discussion — critically interpret

- Why all-day MAE may reward methods predicting dry days well.
- Why heavy rain appears harder for 0.05°/0.1° products than for the gauge point.
- Why a zero/near-zero monthly baseline can look good on all days but fail heavy rain.
- Date shift ±1 day as a validation-period sensitivity, **not** an optimized test parameter.
- Potential input-gauge reuse in satellite products and ERA5 CHIRPS temporal partitioning.
- A handful of extremes in 2024 is inadequate for strong claims; additional years/stations are needed.

## Conclusion

**[WRITE AFTER RUNNING REAL SATELLITES AND QUALITY CHECKS.]**

## References to verify and cite

- CHIRPS v3 primary dataset: https://doi.org/10.15780/G2JQ0P
- CHIRPS GEE catalog: https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHC_CHIRPS_V3_DAILY_RNL
- IMERG NASA catalog: https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_V07
- IMERG mission documentation: https://gpm.nasa.gov/data/imerg

Add a focused literature review on satellite-based gap filling in tropical convection before submission. For a full paper, revise the study to include multiple stations and rigorous uncertainty treatment.