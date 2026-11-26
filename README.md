# Kemayoran Rainfall Gap-Filling — GitHub Research Project

**Status:** Reproducible workflow implemented and tested in offline/demo mode. **Real CHIRPS/IMERG observations have NOT yet been extracted or evaluated** in this release.

A small research project evaluating reconstruction of missing daily rainfall at Kemayoran (Jakarta, Indonesia) from **CHIRPS v3 RNL** and **NASA GPM IMERG V07**. Python scripts run locally or in Google Colab; the repository stores **code and documentation, not the station observations or API credentials**.

> **Please verify data permissions before publishing the station measurements or generated values.** The example data are synthetic. In particular, do not publish the older self-contained notebook: it embedded the real station dataset.

## Quick start A — Colab from GitHub (recommended)

1. Open the existing repository [`priambudihudaf/kemayoran-rainfall-gapfill`](https://github.com/priambudihudaf/kemayoran-rainfall-gapfill). Code and documentation are published there; the gauge CSV stays private.
2. Open [Google Colab](https://colab.research.google.com/) → **File → Open notebook → GitHub** → enter `priambudihudaf/kemayoran-rainfall-gapfill` → open `notebooks/Run_Kemayoran_from_GitHub.ipynb`.
3. In the first config cell set `REPO_URL` to your repository HTTPS URL. Run setup cells to clone the latest repo and install packages.
4. Upload the separate private file `Kemayoran_Gauge_Private_Input.csv` when prompted. The notebook renames it to `data/private/kemayoran_gauge_daily_2020_2026.csv` inside the **temporary** Colab runtime.
5. Run `DEMO` first to check the analysis pipeline (**not scientific results**).
6. Register an [Earth Engine-enabled Google Cloud project](https://developers.google.com/earth-engine/guides/quickstart_python), enter `GEE_PROJECT` into the notebook, and run the *real-data extraction* and *real analysis* cells. Sign in interactively in the notebook: `ee.Authenticate(auth_mode="colab")` runs before the extractor subprocess.
7. Download `outputs/REAL_SATELLITE_RESULTS` as ZIP. Review scientific assumptions before reporting findings.

**Note:** Colab's runtime storage is temporary. Keep your private gauge source separately, and download outputs after each run.

## Quick start B — local Windows / VS Code

Use Python 3.11 and Git. Run from a terminal in this repository folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Place the **separate private observation CSV** in `data/private/kemayoran_gauge_daily_2020_2026.csv` and run a demo:

```powershell
python src/run_analysis.py --mode demo --repeats 10
```

For authentic satellite estimates:

```powershell
python src/extract_satellite_gee.py --project YOUR_GOOGLE_CLOUD_PROJECT --date-shift-days 1
python src/run_analysis.py --mode real --repeats 100
```

Without your own observation CSV, you can smoke-test with **entirely synthetic gauge data**:

```powershell
python scripts/make_demo_gauge.py
python src/run_analysis.py --mode demo --gauge-csv data/private/demo_synthetic_gauge.csv --repeats 5
```

**No Earth Engine credential or Cloud Project ID is stored in the repository.** See [GitHub workflow](docs/GITHUB_WORKFLOW.md) for updating code safely. All input/output CSVs under `data/private/` and all generated charts under `outputs/` are Git-ignored.

## Structure

```text
kemayoran-rainfall-gapfill/
├── README.md
├── .gitignore
├── requirements.txt
├── .github/workflows/tests.yml          # GitHub Actions: offline tests
├── notebooks/Run_Kemayoran_from_GitHub.ipynb
├── src/
│   ├── extract_satellite_gee.py          # real GEE downloads
│   └── run_analysis.py                  # calibration/evaluation/simulation
├── scripts/make_demo_gauge.py           # generates SYNTHETIC data for smoke test
├── docs/
│   ├── GITHUB_WORKFLOW.md
│   ├── METHODOLOGY.md
│   ├── DATA_DICTIONARY.md
│   └── MANUSCRIPT_BLUEPRINT.md
├── tests/test_core.py
└── data/README.md
    # data/private/ and outputs/ are created locally, NOT tracked
```

## Research protocol

| Stage | Years | Role |
|---|---|---|
| Train | 2020–2022 | Fit rain-gauge to satellite bias correction, monthly climatology |
| Validation | 2023 | Choose/weight methods without using test labels |
| Independent test | 2024 | MAE, RMSE, bias, heavy-rainfall performance, extreme recall |
| Optional follow-up | 2025–2026 | Additional data after separate quality and IMERG status checks |

Missing gauge measurements are **not** assigned zero. Original sentinel codes `8888/9999` are `NaN`. Simulated masks cover 5%, 10%, 20% randomly, 3- or 7-day blocks, and a *rain-targeted oracle stress test*. Outputs distinguish actual missing-day estimates from measurements.

**Vital unresolved issue:** If the gauge's `date` means the end of a 07:00 WIB-to-07:00 WIB 24-hour accumulation, that window is exactly the preceding UTC calendar day (07 WIB = 00 UTC). `--date-shift-days 1` then aligns the time windows, not merely labels. **Verify the gauge timestamp convention** before claiming scientific alignment. CHIRPS daily-product temporal definition must also be checked against its provider metadata. Do not interpret satellite-vs-gauge discrepancies as scientific results until aggregation-window alignment is verified or a sensitivity analysis is performed. See `docs/METHODOLOGY.md`.

## How to publish code to a new GitHub repository

Create a **blank** GitHub repository (do not add GitHub's starter README, license, or .gitignore because this ZIP contains those). In Git Bash or terminal, inside this folder:

```bash
git init
git branch -M main
git add .
git status --short
git commit -m "Initialize reproducible rainfall gap-filling study"
git remote add origin https://github.com/priambudihudaf/kemayoran-rainfall-gapfill.git
git push -u origin main
```

**Read `git status --short` before committing**: confirm nothing under `data/private/` and `outputs/` appears. The separate observation CSV must not be part of the GitHub repository ZIP or the commit history.

## Verified public sources

- [CHIRPS v3 RNL — GEE catalog](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHC_CHIRPS_V3_DAILY_RNL). CHIRPS v3 RNL uses ERA5 for daily partitioning; it is not satellite-only.
- [GPM IMERG V07 — GEE catalog](https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_V07). Half-hour precipitation band is in **mm/hr**; sum 48 slots ×0.5 hr for an UTC calendar day. This workflow filters `status=permanent` and tests only through 2024.
- [Google Earth Engine Python authentication](https://developers.google.com/earth-engine/guides/auth).
- [GitHub: add existing local code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

No independent station QA or actual authenticated GEE request has been completed in this release. This repository is **not** a submitted manuscript and demo charts must not be cited as real results.

## Project status (18 November 2026)

- ✅ Source code, Colab notebook, offline tests and CI workflow are tracked here.
- ✅ Local unit tests and synthetic smoke-test passed before publishing.
- ⏳ Genuine CHIRPS / IMERG extraction and the actual gauge-based evaluation still require an Earth Engine-enabled Google Cloud project and authorized notebook session.
- 🔒 The observation data and any station-level predictions are intentionally not public in this repository.

The code is **not** a peer-reviewed result or an accepted preprint. Avoid publishing numerical conclusions based on DEMO mode.


## Separate research: Heatwave QC Policy Benchmark (moved)

The independent [Heatwave QC Policy Benchmark](https://github.com/priambudihudaf/projects-heatwave-qc-policy-benchmark) now lives in its own repository. Its code, notebook, workflows, tests, manuscript outline, and reproducibility documentation were moved on 26 November 2026. No BMKG station observations are included. Historic GitHub Actions results remain available in [the original successful 12-station run](https://github.com/priambudihudaf/kemayoran-rainfall-gapfill/actions/runs/45747326581).
