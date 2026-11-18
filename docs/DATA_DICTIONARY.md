# Data dictionary

| Field | Unit | Description |
|---|---|---|
| date | YYYY-MM-DD | Gauge day label; verify 07:00 WIB end-date convention |
| gauge_mm | mm/day | Daily precipitation at Kemayoran, with 8888/9999/NA interpreted as missing |
| chirps3_rnl_mm | mm/day | CHIRPS v3 daily precipitation at nearest selected grid cell |
| imerg_v07_mm | mm/day | Sum of 48 half-hour IMERG precipitation rates × 0.5 h |
| chirps_n | count/day | Number of available CHIRPS samples (expect 1) |
| imerg_n | count/day | Number of available IMERG samples (expect 48) |
| date_shift_days | days | Mapping from UTC date to station gauge day label; see Methods |
| Satellite ensemble | mm/day | Validation-weighted combination of bias-adjusted satellite estimates |

### Private file paths

- `data/private/kemayoran_gauge_daily_2020_2026.csv` (station observations)
- `data/private/satellite_daily_station_dates.csv` (satellite extracts)
- `outputs/REAL_SATELLITE_RESULTS/` (numeric outputs and graphs)

These paths are ignored by Git. Do not commit files with per-date gauge data or predictions unless permissions have been checked.
