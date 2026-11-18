# Methods and interpretation

**Aim:** evaluate gap-filling of missing daily gauge rainfall at Kemayoran using CHIRPS v3 RNL, GPM IMERG V07, monthly climatology, simple bias adjustments, a satellite ensemble, and time interpolation.

## Experimental design

- Reference: daily station totals; missing codes 8888/9999 treated as NA, never zero. Numeric and temporal QC is necessary before publication.
- Coordinates: approximately 6.1556°S, 106.84°E (confirm station metadata).
- 2020–2022: fitting bias ratios and monthly climatology.
- 2023: validation to choose weights and best method.
- 2024: independent holdout test. 2025–2026 are retained privately for later checks.
- Real data: CHIRPS v3 daily RNL and permanent GPM IMERG V07 half-hourly. The latter is integrated as 48 rates (mm/hour) × 0.5 hours. Missing time slots make a day NA.
- Masks: random 5%, 10%, 20%; 3-/7-day contiguous blocks; and an oracle rain-targeted stress case (not a deployable missingness predictor).
- Metrics: MAE, RMSE, signed bias, extreme-day MAE and event recall/precision. Extreme threshold estimated using training observations only.

## Scientific limitations

**Timestamp convention:** If gauge date D labels the 24-hour total ending 07:00 WIB on D, this is exactly the UTC calendar day D−1. Use date shift +1 only after verifying that convention. If daily CHIRPS label semantics differ from UTC accumulation, analysis requires a sensitivity test.

**Reference:** A point rain gauge and ~5–11 km grid-cell means have different spatial support. Their mismatch is not simply algorithm error. CHIRPS and IMERG incorporate station information / gauge corrections, so reference independence cannot be assumed without data-source analysis.

**Uncertainty:** Heavy-rain samples in 2024 are few. Repeated masking of the same dates does not produce independent extreme events. Do not overstate significance of pooled recall; report denominators and uncertainty. The stress masking uses the reference truth and is illustrative only.

**Publication:** No real GEE extraction was performed in the file-packaging environment. All `--mode demo` images are test artifacts, not findings.

## Official catalog

- CHIRPS v3: https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHC_CHIRPS_V3_DAILY_RNL
- IMERG V07: https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_V07
