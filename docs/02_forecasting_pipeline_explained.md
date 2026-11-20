> **Note:** this document was first written for an earlier combined notebook. File paths have been updated to this repository's layout. In this folder, data now lives in `data/raw/` and `data/processed/`, Ashita's scripts in `src/`, the notebooks in `notebooks/` and figures in `figures/`. See the top-level `README.md`.

# `notebooks/archive/02_forecasting_pipeline.ipynb` explained

This notebook brings Ashita's data preprocessing and forecasting scripts together in one place. They come from the group repo (`Christmas-Casuals`, `ashita_branch`, commits `105c452` and `7ff8b8a`, 10 Nov 2026), and the notebook runs them in order from this repository. This file explains what each section does, what was changed from her code and why, and what the results show.

**The question:** in the Humboldt Current, can we forecast:
1. next month's SST anomaly;
2. how long a coastal El Niño or La Niña episode will last;
3. how warm or cold the water will get before the episode ends?

**El Niño / La Niña rule used throughout:** a coastal **El Niño** is ICEN **≥ +0.4 °C** for at least **3 consecutive months**, and a coastal **La Niña** is ICEN **≤ −0.4 °C** for at least 3 consecutive months.

---

## Quick reference

| Section | From Ashita's file | What it does | Output |
|---|---|---|---|
| Setup | — | Relabels the ICEN episodes with the ±0.4 °C rule | `icen_monthly_pm04.csv`, `ICEN_CSV` |
| 1 | `data_cleaning.py` | Loads drifter SST for the study region and period | `df`, `data/cache/forecast_obs.npz` |
| 2 | `data_preprocessing_2010.py` | Builds monthly SST anomaly series, each against a baseline fitted only on earlier years | 3 × `sst_forecast_data*.csv` |
| 3a–d | `forecast_monthly_sst.py` | Forecasts next month's SST anomaly | error tables |
| 4 | `forecast_episode_duration.py` | Forecasts how many months an episode has left, with 5 methods including ETS and BSTS | error tables |
| 5 | `forecast_peak_sst_arima_gam.py` | Forecasts the peak (or lowest) SST over the rest of an episode | error tables |

**Run order:** top to bottom. A full run takes about 40 seconds once `data/cache/forecast_obs.npz` exists, and most of that is the BSTS sampling in Sections 4 and 5. The first run builds the cache file from the full drifter arrays, which takes a few minutes. Every cell's output is saved in the notebook.

---

## Input data

- **Drifter data:** hourly Clouddrift `gdp1h` readings, stored as `.npy` arrays in `data/cache/`. There are about 197 million readings worldwide.
- **ICEN** (`data/raw/icen_monthly_original.csv`):
  - Peru's coastal El Niño index: a centred 3-month average of the SST anomaly in the Niño 1+2 region, January 2001 to September 2026.
  - The file comes with episode labels (`ENSO`, `Episode`, `Episode_ID`) built with a stricter rule: > +0.5 °C and < −0.7 °C.
  - **The setup cell replaces those labels** using the ±0.4 °C rule, and saves the result as `icen_monthly_pm04.csv`. Every section reads that file.

---

## Changes from Ashita's code

The code is hers, apart from these changes:

1. **Imports between files removed.** `from data_cleaning import df` and `from forecast_episode_duration import ...` are gone, because those objects are already defined in earlier cells.
2. **`main()` is called directly,** instead of through `if __name__ == "__main__":`.
3. **In Section 5, `FEATURES` is renamed `PEAK_FEATURES`.** Both of her forecasting scripts define a global `FEATURES`. In one notebook, Section 5's version would overwrite Section 4's, and Section 4's `make_forecasts` would then crash when Section 5 calls it.
4. **Section 1 reads the drifter data in chunks.** Her `data_cleaning.py` loads the full global arrays at once, about 7 GB for the raw arrays and over 10 GB at peak. That's more memory than an 8 GB laptop has. The chunked version keeps exactly the same readings. It saves them once to `data/cache/forecast_obs.npz`, and the whole notebook then peaks at about 1.5 GB.
5. **Section 2 runs three times.** Her script made only `sst_forecast_data_2011_2013.csv`, but Sections 3 and 5 also need `sst_forecast_data.csv` and `sst_forecast_data_2014_2017.csv`. No script in the repo makes those two files, on any branch. Section 2 is now a function of `TRAIN_END_YEAR` and the output filename, and it runs for 2010, 2013 and 2017.
   - **This is a reconstruction.** The years follow the forecast periods set in her `forecast_peak_sst_arima_gam.py`, but her actual files may differ.
6. **The El Niño / La Niña rule is now ±0.4 °C for 3 consecutive months.**
   - The setup cell rebuilds `ENSO`, `Episode` and `Episode_ID` from the monthly ICEN. Her file used > +0.5 °C and < −0.7 °C.
   - The new episodes go to every section: Section 3's phase labels, Section 4's episode table, and Section 5's episodes.
   - Section 4's ARIMA now treats an episode as over once its forecast ICEN path leaves ±0.4 °C. It used 0.5 and −0.7 before.
7. **Section 4 has two new duration methods, ETS and BSTS.** See Section 4 below.

Her velocity masks (`valid_velocity.npy` and `valid_sst_velocity.npy`) aren't recreated, because nothing in this notebook uses them.

---

## Setup: relabelling the episodes

1. **Read** Ashita's ICEN file.
2. **Mark qualifying months.** A month is El Niño if ICEN ≥ +0.4 °C and it's part of a run of at least 3 such months in a row. La Niña is the same at ≤ −0.4 °C.
3. **Label each month.** `ENSO` is El Niño, La Niña or Neutral. `Episode` is El Niño, La Niña or No. `Episode_ID` numbers each run in time order.
4. **Save** the result as `icen_monthly_pm04.csv` and set `ICEN_CSV` to it.

**Result:** **28 episodes** from 2001 to 2026, 13 El Niño and 15 La Niña. The old rule gave 22.
- **23 of them fall within the 2001–2022 study period:** 10 El Niño and 13 La Niña, against 19 under the old rule.
- **The lower threshold adds weaker events,** for example La Niña in 2006, 2011 and 2019, and El Niño in late 2002.
- **Episodes also run longer.** For example:

| Episode | Old rule | ±0.4 °C rule |
|---|---|---|
| 2005 La Niña | 4 months | 11 months |
| 2012–13 La Niña | 7 months | 13 months |
| 2021–22 La Niña | 14 months | 17 months |

---

## Section 1: Data cleaning

**What it keeps:** readings that fall in the study box and period and have a usable SST:
- **Box:** 94°W–65°W, 54°S–4°S.
- **Period:** 2001–2022.
- **SST:** finite and between −2 and 35 °C, after converting from Kelvin to °C.

**How it reads the data:**
- The global arrays are opened from disk without loading them (`mmap_mode="r"`) and read 2 million readings at a time.
- Each reading's drifter ID comes from `rowsize`: a reading's position in the array, together with the running total of readings per drifter, identifies its drifter.

**The table `df`:** one row per reading, with drifter ID, time, longitude, latitude, `sst_degC`, year, month and day of year.

**Result:** 4,081,401 readings. This is more than the 2.5 million in `notebooks/archive/01_exploratory_analysis.ipynb`, because Ashita's box is larger (it reaches 94°W and 54°S, against 89°W and 49°S) and she doesn't require velocity.

---

## Section 2: SST anomalies against a baseline fitted only on earlier years

**Why not use raw SST?** Drifters move around, and the south of the region is much colder than the north. A monthly average would mostly track where the drifters were. Instead, each reading is compared with the normal SST for its place and time of year.

**What `build_forecast_data(TRAIN_END_YEAR, OUTPUT_FILE)` does:**

1. **Filters.** It keeps SST between 5 and 35 °C and drops the Atlantic corner south of 40°S and east of 71°W.
2. **Fits the normal SST on training years only (2001 to `TRAIN_END_YEAR`).**
   - The model is a smooth surface of SST by place and season. It uses B-spline curves across latitude (16) and longitude (10), each with an annual and a six-month cycle.
   - It's fitted to monthly averages for each 1° cell, with each year given equal weight.
   - A smoothness penalty stops it from wiggling in poorly sampled cells.
   - The fit is built one year at a time to save memory.
3. **Works out anomalies.** It subtracts the fitted normal from **every** reading, including the forecast years, which the normal never saw.
4. **Builds the monthly series.**
   - It averages anomalies within 2° cells; a cell needs at least 24 readings.
   - It combines the cells with area weighting, using cos(latitude).
5. **Flags coverage.** A month is `low_coverage` if it has fewer than 10 cells or fewer than 5 drifters.

**Why fit only on earlier years?** If the baseline included the forecast years, the definition of "normal" would already contain the future, and the forecast scores would look better than they are.

| Baseline years | Output file | Used by |
|---|---|---|
| 2001–2010 | `sst_forecast_data_2011_2013.csv` | Section 5, forecasts in 2011–2013 |
| 2001–2013 | `sst_forecast_data_2014_2017.csv` | Section 5, forecasts in 2014–2017 |
| 2001–2017 | `sst_forecast_data.csv` | Section 3, and Section 5 for 2018–2022 |

**Result:** each file has 264 months (2001–2022), and 260 of them have an SST anomaly. Section 2 doesn't use the ENSO rule, so this result is the same as before.

---

## Section 3: Forecasting next month's SST anomaly (`forecast_monthly_sst.py`)

**Setup:**
- **Data:** `sst_forecast_data.csv`, the anomaly against the 2001–2017 baseline.
- **Low-coverage months:** set to missing, so nothing is trained or scored on them.
- **Training and testing:** training ends in December 2017, and the tests cover January 2018 to December 2022.
- **Phase:** each test month is labelled El Niño, La Niña or Neutral using the ±0.4 °C episodes. The phase is only used to group the errors; the models themselves don't use it.

**3a. Persistence.** Next month's anomaly equals this month's. This is the reference to beat.

**3b. Linear regression** on:
- the last two months' anomalies (`sst_lag1`, `sst_lag2`);
- the target month, encoded as sine and cosine so that December and January sit next to each other.

**3c. Regression with lagged ICEN.**
- It adds `icen_lag3`, the ICEN value from three months before the target month.
- ICEN is a centred 3-month index, so its latest month is only known a month later. One more month is allowed for publication, so a March forecast uses December's ICEN.

**3d. XGBoost.** A small boosted-tree model on the same inputs: 100 trees, depth 2, learning rate 0.05.

### Results (58 test months)

The overall scores don't depend on the ENSO rule:

| Model | Average error (°C) | RMSE (°C) |
|---|---|---|
| Persistence | 0.216 | 0.274 |
| Regression without ICEN | 0.196 | — |
| Regression with ICEN | 0.195 | 0.254 |
| XGBoost with ICEN | 0.195 | 0.251 |

**By phase (±0.4 °C rule):**

| Phase | Months | Persistence | Regression | XGBoost |
|---|---|---|---|---|
| El Niño | 4 | 0.494 | 0.454 | 0.411 |
| La Niña | 39 | 0.200 | 0.183 | 0.191 |
| Neutral | 15 | 0.184 | 0.158 | 0.146 |

Phase values are average errors in °C. Under the old rule, the split was 3 El Niño, 29 La Niña and 24 neutral months.

**What the results show:**
- **Both models beat persistence by about 10%** (0.216 to 0.195 °C).
- **ICEN adds almost nothing** (0.196 to 0.195). Lagged SST already holds most of what can be predicted.
- **XGBoost matches the regression,** so a more complex model doesn't help.
- **Errors are much larger in El Niño months,** about 2.5 times the other phases, but that rests on only 4 test months. The 2018–2022 test period was mostly La Niña.

---

## Section 4: How many months an episode has left (`forecast_episode_duration.py`)

This section uses ICEN only, with no drifter data.

### Building the episode table (`build_episode_table`)

- **Episodes:** the ±0.4 °C episodes that fall within 2001–2022. There are **23**: 10 El Niño and 13 La Niña.
- **Confirmation:** an episode is **confirmed** at its third month. The forecast is issued 2 months later (`ICEN_DELAY = 2`), when that ICEN value is actually available.
- **Target:** the number of episode months left after the forecast month (`Actual months left`).

### Five methods (`make_forecasts`)

Every method uses only information available on the forecast date. An episode's end only counts as known once its last month plus the 2-month delay has passed. ARIMA, ETS and BSTS each need at least 24 months of ICEN history.

| Method | How it forecasts |
|---|---|
| Median | The median months left in past episodes of the same phase |
| Regression | A linear regression of months left on the ICEN value at confirmation, trained on past same-phase episodes (needs at least 3) |
| ARIMA | ARIMA(1,0,1) fitted to the monthly ICEN history up to the latest available month. Its **average forecast path**, up to 36 months ahead, gives the end of the episode: the first month the path leaves ±0.4 °C. If it never does, the episode is left unscored |
| **ETS** (new) | Exponential smoothing with additive errors. AIC chooses no trend, additive trend or damped trend. It simulates **1,000 possible ICEN paths** for the next 36 months |
| **BSTS** (new) | A Bayesian structural time series: a local level (random walk) plus noise, fitted by Gibbs sampling (3,000 draws, the first 1,000 discarded). The priors follow the R `bsts` defaults. It gives **1,000 possible ICEN paths** for the next 36 months |

**How ETS and BSTS turn simulated paths into a forecast:**
- **Why simulate?** Unlike ARIMA(1,0,1), neither model pulls ICEN back towards normal. On average, they predict ICEN stays where it is. So their average path would often never leave the episode range, and the end of the episode has to come from simulated futures.
- **The forecast:** for each simulated path, find the first month ICEN leaves the episode range. The forecast is the **median** of those months.
- **If the median path never leaves within 36 months,** the forecast is **capped at the window end** and still scored. Otherwise these models would drop out of every long-episode comparison.
- **Random variation:** with fixed seeds, the forecasts change by about ±2–3 months between seeds. That's small next to their errors.

### Results

**Forecast status:**

| Status | ARIMA | ETS | BSTS |
|---|---|---|---|
| Insufficient ICEN history | 2 | 2 | 2 |
| Path never left the range (unscored) | 4 | — | — |
| Scored | 17 | 19 | 20 |
| Scored, capped at window end | — | 2 | 1 |

**Scores on the 15 episodes every method could forecast:**

| Phase | Episodes | Median | Regression | ARIMA | ETS | BSTS |
|---|---|---|---|---|---|---|
| El Niño | 7 | 2.00 | **1.87** | 3.43 | 16.00 | 12.57 |
| La Niña | 8 | 4.88 | **4.09** | 4.25 | 7.00 | 6.25 |
| **All** | **15** | 3.53 | **3.05** | 3.87 | 11.20 | 9.20 |

Values are average errors in months.

| RMSE (months) | Median | Regression | ARIMA | ETS | BSTS |
|---|---|---|---|---|---|
| All 15 episodes | 4.65 | **3.86** | 5.06 | 14.66 | 12.39 |

**What the results show:**
- **Regression on the ICEN value at confirmation is the best method** in both phases. The median is close behind for El Niño.
- **ETS and BSTS are much worse,** at 9–11 months of average error against 3–4 for the others.
  - Because neither model pulls ICEN back towards normal, they expect an episode to last until random changes happen to push ICEN back over the threshold. That takes far longer than real episodes last.
  - They often predict 13–34 months left for episodes that actually had 0–12 months left. For the 2003 La Niña, which was already over, ETS predicted 23 months and BSTS 22.
  - Example: the 2015–16 El Niño had 10 months left. ETS and BSTS both predicted 34 (capped), ARIMA predicted 13, and the median predicted 0.
- **ARIMA(1,0,1) pulls back towards normal,** but it often overshoots the length (by 12 months for the 2017 El Niño). For 4 La Niña episodes, its path never ends the episode within 36 months.
- **The ±0.4 °C rule makes this harder than before.** Episodes are longer and include more weak events. Under the old rule, the best average error was about 1.8 months for El Niño and 2.6 for La Niña. Now it's 1.9 and 4.1.

**Conclusion:** for episode length, how strong the episode is at confirmation, through simple regression, beats time-series models that don't pull back towards normal. A better BSTS for ICEN would add that pull, for example an AR(1) term instead of a random-walk level.

---

## Section 5: Peak SST over the rest of an episode (`forecast_peak_sst_arima_gam.py`)

**What it forecasts:** the most extreme SST anomaly over the remaining months of an episode. That's the peak for El Niño and the lowest value for La Niña.

**How it works:**
1. **Episodes and length.** It takes the episode table and **ARIMA's** months-left forecast from Section 4, for episodes with forecasts issued from 2011 onward. ETS and BSTS aren't used here.
2. **Choosing an SST file.** It picks the file whose baseline ends before the forecast year (2011–13, 2014–17 or 2018–22), so the baseline never sees the forecast period.
3. **The GAM path.** For each month ahead, up to ARIMA's predicted months left, it fits a separate model. A GAM here is a regression where some inputs can have curved effects. Its inputs are:
   - the latest and previous available SST anomaly;
   - sine and cosine of the target month;
   - a smooth spline curve in the latest available ICEN.

   Each model is trained only on SST outcomes known by the forecast month, and needs at least 36 training months. The forecast is the maximum (El Niño) or minimum (La Niña) along the predicted path.
4. **Comparisons:**
   - **Persistence:** the SST anomaly in the forecast month.
   - **Historical median:** the median extreme of past same-phase episodes whose end was already known.
5. **Scoring.** The actual end date is used only to work out the true extreme. Episodes with any missing SST month in the remaining period aren't scored.

### Results (±0.4 °C episodes)

**Coverage.** 11 episodes fall in the forecast period, and 6 of them actually continued past the forecast month:
- All 6 got a GAM forecast. No episode was wrongly predicted as already over.
- **5 forecasts were issued for episodes that had in fact already ended.** ARIMA predicted 3–12 more months for them. That's more than under the old rule, because ARIMA now often overestimates how long episodes last.
- 1 continuing episode, the 2021–22 La Niña, has incomplete SST data and can't be scored.

**All three methods on the same episodes:**

| Phase | Episodes | ARIMA + GAM | Persistence | Historical median |
|---|---|---|---|---|
| El Niño | 2 | **0.564 °C** | 0.717 | 0.583 |
| La Niña | 3 | 0.229 | 0.225 | **0.099** |

Values are average errors in °C.

**What the results show:**
- **El Niño:** ARIMA + GAM is slightly better than the historical median and clearly better than persistence.
- **La Niña:** the historical median is clearly best, at 0.10 °C against about 0.23 for the other two. ARIMA + GAM no longer beats persistence; under the old rule it did, 0.165 against 0.319.
- **The GAM still underestimates strong events.** For the 2015–16 El Niño, it forecast a peak of +0.20 °C against an actual +1.00 °C.
- **Too few episodes to be confident:** with 2–3 episodes per phase, these results are only suggestive.

---

## Overall findings

1. **Next-month SST:** simple models beat persistence by about 10%. ICEN and XGBoost add essentially nothing beyond lagged SST. The ENSO rule doesn't affect this.
2. **Episode length (±0.4 °C rule, 15 shared episodes):**
   - Regression on ICEN at confirmation is best, at 3.1 months average error.
   - Next come the median (3.5) and ARIMA (3.9).
   - ETS (11.2) and BSTS (9.2) are far worse, because they don't pull ICEN back towards normal, so they predict episodes lasting much too long.
3. **Peak SST:** ARIMA + GAM helps for El Niño. For La Niña, the median of past episodes is best, and the GAM still underestimates strong events.
4. **The ±0.4 °C rule changes the picture.** It adds weaker events and lengthens episodes, which makes episode length harder to forecast. ARIMA also overestimates length more often, so 5 peak-SST forecasts are issued for episodes that had already ended.
5. **Fair testing throughout:** every section uses only information available on the forecast date. That covers baselines fitted on earlier years, the ICEN delay, and episode ends that only count once known.

## Limitations

- **Small samples:** 58 test months, of which only 4 are El Niño; 15 shared episodes in Section 4; 2–3 episodes per comparison in Section 5.
- **Reconstructed inputs:** the 2014–2017 and 2018–2022 SST files are my reconstruction of files that aren't in the repo.
- **Capped forecasts:** ETS and BSTS forecasts are capped at the 36-month window when the median path never ends the episode (2 episodes for ETS, 1 for BSTS). Without the cap their errors would be larger still.
- **The BSTS is hand-written:** it's my numpy implementation of a local-level BSTS, following the R `bsts` method and priors, not the `bsts` package itself.
- **Different setup from `notebooks/archive/01_exploratory_analysis.ipynb`:** Ashita's study box (94°W–65°W, 54°S–4°S) is larger. That notebook's events also use Niño 1+2 with +0.4 / −1.0 °C. So these anomalies and episodes aren't directly comparable with that notebook's.
- **ICEN and the El Niño label:** ICEN is a NOAA-based index, not drifter data. The drifter data enters only through the SST anomaly series in Sections 2, 3 and 5.

## Files

**Reads:**
- `data/cache/lon.npy`, `lat.npy`, `time.npy`, `sst.npy`, `id.npy`, `rowsize.npy` (first run only)
- `data/cache/forecast_obs.npz`
- `data/raw/icen_monthly_original.csv`

**Writes:**
- `icen_monthly_pm04.csv` (the ICEN episodes relabelled with the ±0.4 °C rule)
- `data/cache/forecast_obs.npz` (first run)
- `sst_forecast_data_2011_2013.csv`
- `sst_forecast_data_2014_2017.csv`
- `sst_forecast_data.csv`

**Environment:** kernel `.venv-1` (Python 3.13). Needs numpy, pandas, scipy, scikit-learn, statsmodels and xgboost 3.2.0. xgboost also needs `libomp`, installed with Homebrew. `nbclient` is only needed to run the notebook from the terminal.
