# GitHub + Colab workflow

1. Open [the repository](https://github.com/priambudihudaf/kemayoran-rainfall-gapfill).
2. Open the [Colab-ready notebook](https://colab.research.google.com/github/priambudihudaf/kemayoran-rainfall-gapfill/blob/main/notebooks/Run_Kemayoran_from_GitHub.ipynb).
3. Run setup and install cells. Colab clones the `main` branch into its temporary runtime.
4. Upload the **private normalized** `Kemayoran_Gauge_Private_Input.csv` only to the Colab runtime.
5. Run the DEMO mode once: demo charts are not scientific findings.
6. For REAL mode: register Earth Engine, enable a Google Cloud project, set `GEE_PROJECT` in notebook, sign in with your Google account, and run satellite extraction and evaluation cells.
7. Download real outputs to your computer; do not push station observations, extracted values or private figures to the public repository.
8. Revise methods or scripts locally; commit source changes only. The CI test workflow runs on each push.

Keep station redistribution permission, gauge accumulation timing, sample-size limitations and independence of satellite/gauge reference explicit in reports.
