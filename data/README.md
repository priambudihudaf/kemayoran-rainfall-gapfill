# Data access and privacy

This public repository deliberately contains **no raw Kemayoran observations**, satellite point time series, or predictions. Place your normalized observations in `data/private/kemayoran_gauge_daily_2020_2026.csv` locally or in temporary Google Colab storage only.

Required CSV columns:

```csv
date,gauge_mm
2020-01-01,0
2020-01-02,12.5
```

Use your separately provided normalized private CSV, not a published GitHub attachment. Observations coded 8888 or 9999 become missing values; 0 means a verified dry day. Do not share point-level outputs or credentials before confirming redistribution permissions.

To test the software without station observations:

```bash
python scripts/make_demo_gauge.py
python src/run_analysis.py --mode demo --gauge-csv data/private/demo_synthetic_gauge.csv --repeats 5
```
