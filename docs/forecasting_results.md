> **Note:** this document was first written for an earlier combined notebook. File paths have been updated to this repository's layout. In this folder, data now lives in `data/raw/` and `data/processed/`, Ashita's scripts in `src/`, the notebooks in `notebooks/` and figures in `figures/`. See the top-level `README.md`.

# Ashita's forecasting code with the ±0.4 °C ENSO rule: how it works and results

This document covers Ashita's scripts in `src/` (`ashita_branch`), changed to use a **±0.4 °C** coastal El Niño / La Niña rule. It explains how each script works, what changed, and every result. The duration and peak predictions get the most detail.

**The rule:** a coastal **El Niño** is ICEN **≥ +0.4 °C** for at least **3 consecutive months**, and a coastal **La Niña** is ICEN **≤ −0.4 °C** for at least 3 consecutive months. Her original data used > +0.5 °C and < −0.7 °C.

---

## Contents
1. [What changed in Ashita's files](#1-what-changed-in-ashitas-files)
2. [How the pipeline fits together](#2-how-the-pipeline-fits-together)
3. [How the results were produced](#3-how-the-results-were-produced)
4. [The episodes under the ±0.4 °C rule](#4-the-episodes-under-the-04-c-rule)
5. [SST anomaly series](#5-sst-anomaly-series)
6. [Next-month SST forecast](#6-next-month-sst-forecast-forecast_monthly_sstpy)
7. [**Duration predictions**: how many months an episode has left](#7-duration-predictions-forecast_episode_durationpy)
8. [**Peak predictions**: how extreme SST gets before the episode ends](#8-peak-predictions-forecast_peak_sst_arima_gampy)
9. [SST by ENSO phase](#9-sst-by-enso-phase-plot_icen_sstpy)
10. [Overall conclusions](#10-overall-conclusions)
11. [Limitations](#11-limitations)

---

## 1. What changed in Ashita's files

The cutoffs only appeared in two places: the labels already stored in `icen_monthly.csv` (no script creates them), and four hard-coded lines in two scripts. All the changes are local edits to the repo folder. Nothing was committed or pushed, and `git diff` shows them.

| File | Change |
|---|---|
| `relabel_icen.py` (**new**) | Rebuilds the `ENSO`, `Episode` and `Episode_ID` columns of `icen_monthly.csv` with the ±0.4 °C, 3-month rule. The thresholds are named constants at the top (`ENSO_WARM`, `ENSO_COLD`, `MIN_MONTHS`). The first run keeps the original as `icen_monthly_original.csv`, and every run relabels from that original, so running it again gives the same result |
| `icen_monthly.csv` | Relabelled. Only `ENSO`, `Episode` and `Episode_ID` change: 55 of 309 months get a new label, and later episode numbers shift. ICEN values, dates, line endings and the integer IDs are all kept as they were |
| `icen_monthly_original.csv` (**new**) | Her original file, unchanged |
| `forecast_episode_duration.py` | Adds `ENSO_WARM = 0.4` and `ENSO_COLD = -0.4`. The ARIMA end test (old line 100) was `path.le(0.5)` / `path.ge(-0.7)` and is now `path.lt(ENSO_WARM)` / `path.gt(ENSO_COLD)` |
| `plot_icen_sst.py` | Adds the same constants. The dashed threshold lines (were 0.5 and −0.7) and the "neutral" months (were −0.7 to 0.5) now use them |

`forecast_monthly_sst.py` and `forecast_peak_sst_arima_gam.py` didn't need editing for the rule: they read the labels from the CSV, and the peak script gets the end rule by importing from `forecast_episode_duration.py`.

**New models added to the scripts** (Sections 7b and 8b explain them). Her original methods and outputs are unchanged; the new ones are added alongside.

| File | Added |
|---|---|
| `forecast_episode_duration.py` | **Hazard model:** a month-by-month model of the chance an episode ends, fitted on all phases together. **ARIMA sim:** the same ARIMA(1,0,1) fit, with the forecast taken from 1,000 simulated paths. New episode-table columns `Confirmation`, `Strength` and `Trend`. A summary table scoring all 5 methods |
| `forecast_peak_sst_arima_gam.py` | **GAM sim:** the GAM average path plus resampled whole past-error paths, taking the median simulated extreme. **Blend:** 50/50 of the GAM sim and the historical median. `forecast_sst_path` now also returns the past-error paths. A new comparison of all methods |

**To undo:** run `git checkout -- .` and delete the two new files.

---

## 2. How the pipeline fits together

```
data/cache/*.npy (Clouddrift gdp1h drifters)
        │
        ▼
data_cleaning.py ──► df  (one row per hourly SST reading in the study box)
        │
        ├──► sst_monthly_anomalies.py ──► sst_monthly_anomalies.csv ──► plot_icen_sst.py
        │         (one baseline from all years, each year left out of its own)
        │
        └──► data_preprocessing_2010.py ──► sst_forecast_data_2011_2013.csv   (baseline 2001–2010)
                 (run again with 2013, 2017)  sst_forecast_data_2014_2017.csv   (baseline 2001–2013)
                                              sst_forecast_data.csv             (baseline 2001–2017)
                                                     │
icen_monthly.csv (relabelled by relabel_icen.py)     │
        │                                            ▼
        ├──────────────► forecast_monthly_sst.py      (next-month SST)
        ├──────────────► forecast_episode_duration.py (DURATION: months left)
        │                         │ episodes, ARIMA months left
        │                         ▼
        └──────────────► forecast_peak_sst_arima_gam.py (PEAK: most extreme SST still to come)
```

**About ICEN:** ICEN is Peru's coastal El Niño index, a centred 3-month average of the Niño 1+2 SST anomaly. It is NOAA-based, not drifter data. The drifters only come in through the SST anomaly files.

---

## 3. How the results were produced

Ashita's scripts were run **as they are** in a separate working folder, with two exceptions. Everything is in the session scratchpad, not in the repo.

1. **`data_cleaning.py` was swapped for a stand-in.** Her version loads all ~197 million global readings at once, about 7 GB of arrays and over 10 GB at peak. That crashes an 8 GB laptop.
   - The stand-in builds the **same `df`** (same box, period and SST filter) from `data/cache/forecast_obs.npz`, which `notebooks/archive/02_forecasting_pipeline.ipynb` makes by reading the arrays in chunks.
   - Every script that does `from data_cleaning import df` gets the stand-in instead.
2. **The two missing SST files were made by re-running her preprocessing script** with `TRAIN_END_YEAR = 2013` and `2017` (and matching output names). The repo has no script for these files.
   - **This is a reconstruction.** The years follow the forecast periods in her `forecast_peak_sst_arima_gam.py`.

All 8 script runs finished without errors.

**Cross-check:** the three SST files are byte-for-byte identical to the ones `notebooks/archive/02_forecasting_pipeline.ipynb` makes, and every forecast result below matches that notebook exactly.

---

## 4. The episodes under the ±0.4 °C rule

`relabel_icen.py` finds **28 episodes** in 2001–2026: 13 El Niño and 15 La Niña. The old rule found 22. **23 fall within the 2001–2022 study period**: 10 El Niño and 13 La Niña, against 19 before.

| ID | Phase | Start | End | Months |
|---|---|---|---|---|
| 1 | La Niña | 2001-06 | 2002-01 | 8 |
| 2 | El Niño | 2002-03 | 2002-05 | 3 |
| 3 | El Niño | 2002-10 | 2003-01 | 4 |
| 4 | La Niña | 2003-04 | 2003-08 | 5 |
| 5 | La Niña | 2004-04 | 2004-08 | 5 |
| 6 | La Niña | 2005-02 | 2005-12 | 11 |
| 7 | La Niña | 2006-03 | 2006-05 | 3 |
| 8 | El Niño | 2006-08 | 2007-01 | 6 |
| 9 | La Niña | 2007-03 | 2008-01 | 11 |
| 10 | El Niño | 2008-04 | 2008-09 | 6 |
| 11 | El Niño | 2009-05 | 2009-09 | 5 |
| 12 | La Niña | 2010-07 | 2011-03 | 9 |
| 13 | La Niña | 2011-09 | 2011-12 | 4 |
| 14 | El Niño | 2012-03 | 2012-07 | 5 |
| 15 | La Niña | 2012-11 | 2013-11 | 13 |
| 16 | El Niño | 2014-05 | 2014-11 | 7 |
| 17 | El Niño | 2015-04 | 2016-06 | 15 |
| 18 | El Niño | 2016-12 | 2017-04 | 5 |
| 19 | La Niña | 2017-08 | 2018-07 | 12 |
| 20 | El Niño | 2018-11 | 2019-02 | 4 |
| 21 | La Niña | 2019-07 | 2019-10 | 4 |
| 22 | La Niña | 2020-06 | 2021-06 | 13 |
| 23 | La Niña | 2021-08 | 2022-12 | 17 |

**What the lower threshold does:**
- **It adds weak events**, mostly La Niña: 2006, 2011 and 2019 La Niña, and the late-2002 El Niño.
- **It lengthens existing ones**, for example:

| Episode | Old rule | ±0.4 °C rule |
|---|---|---|
| 2005 La Niña | 4 months | 11 months |
| 2012–13 La Niña | 7 months | 13 months |
| 2017–18 La Niña | 8 months | 12 months |

Episodes 24–28 (2023–2026) fall outside the study period and aren't used.

---

## 5. SST anomaly series

**Both SST scripts use the same method:**
1. **Fit a "normal SST" surface** by place and season: B-spline curves across latitude and longitude, each with annual and six-month cycles.
2. **Subtract it** from every hourly drifter reading.
3. **Average the anomalies** within 2° cells, needing at least 24 readings per cell.
4. **Combine the cells** with area weighting.
5. **Flag coverage:** a month is `low_coverage` if it has fewer than 10 cells or fewer than 5 drifters.

The method corrects for drifters drifting between the warm north and the cold south.

| Script | Baseline | Output | Result |
|---|---|---|---|
| `data_preprocessing_2010.py` (×3) | Fitted only on 2001–2010 / 2013 / 2017, so forecasts never use future data | 3 forecast files | 264 months each, 260 with an anomaly |
| `sst_monthly_anomalies.py` | All years, with each year left out of its own baseline | `sst_monthly_anomalies.csv` | 4,067,291 readings used. 260 of 264 months have data, 4 of them low coverage |

The ENSO rule doesn't affect these series.

---

## 6. Next-month SST forecast (`forecast_monthly_sst.py`)

**How it works:**
- **Target:** next month's regional SST anomaly, from `sst_forecast_data.csv` (2001–2017 baseline). Low-coverage months are left out.
- **Training and testing:** trained up to December 2017, tested on January 2018 to December 2022 (58 months).
- **Methods:**
  - **Persistence:** next month = this month.
  - **Linear regression:** on the last two months' SST and the season, coded as sine and cosine of the month.
  - **The same regression plus ICEN** from 3 months earlier. ICEN is a centred 3-month average, so its latest value is a month late, and one more month is allowed for publication.
  - **XGBoost:** 100 trees, depth 2, on the same inputs.
- **Where the ENSO rule comes in:** only to group the errors by phase. The models themselves don't use the labels.

**Results:**

| Model | Average error (°C) | RMSE (°C) |
|---|---|---|
| Persistence | 0.216 | 0.274 |
| Regression without ICEN | 0.196 | — |
| Regression with ICEN | 0.195 | 0.254 |
| XGBoost with ICEN | 0.195 | 0.251 |

| Phase (±0.4 °C) | Test months | Persistence | Regression | XGBoost |
|---|---|---|---|---|
| El Niño | 4 | 0.494 | 0.454 | 0.411 |
| La Niña | 39 | 0.200 | 0.183 | 0.191 |
| Neutral | 15 | 0.184 | 0.158 | 0.146 |

Phase values are average errors in °C.

**What it shows:**
- **About 10% better than persistence.** Lagged SST already holds most of what can be predicted.
- **ICEN and XGBoost add essentially nothing.**
- **El Niño errors are about 2.5 times larger,** but that rests on only 4 months. The 2018–22 test period was mostly La Niña: 39 of 58 months under the new rule.

---

## 7. Duration predictions (`forecast_episode_duration.py`)

### The question

**When a coastal El Niño or La Niña has just been confirmed, how many more months will it last?**

### Setting up each forecast

**Timing.** For each episode, the forecast is set up as it would be in real time:
- **Confirmation:** the third month of the episode, when it first meets the 3-month rule (`confirmation = event.iloc[2]`).
- **Forecast date:** confirmation + `ICEN_DELAY` (2 months), because ICEN is a centred 3-month average and is published late.
  - Example: the 2015–16 El Niño started in April 2015 and was confirmed in June 2015. The forecast date is August 2015.
- **Target:** `Actual months left`, the episode months *after* the forecast date. That's the last month minus the forecast date, or 0 if it has already ended.
  - The 2015–16 El Niño ended in June 2016, so 10 months were left.
- **Only past information:** everything uses data known on the forecast date. A past episode only counts as "known" once its end month plus the 2-month delay has passed.

### The three methods

| Method | What it predicts | Needs |
|---|---|---|
| **Median** | The median `Actual months left` of past episodes of the same phase whose ends were already known | At least 1 past episode |
| **Regression** | A linear regression of months left on the **ICEN value at confirmation** (how strong the episode is), fitted on past same-phase episodes. Negative predictions are set to 0 | At least 3 past same-phase episodes |
| **ARIMA** | Fits ARIMA(1,0,1) to the full monthly ICEN history up to the last available month (forecast date − 2), forecasts its **average path** up to 36 months ahead, and finds the **first month the path leaves the episode range**: below +0.4 for El Niño, above −0.4 for La Niña. Months left = that month − 1 − the forecast date | At least 24 months of ICEN history. If the path never leaves within 36 months, it is "No exit within forecast window" and unscored |

**Why ARIMA can work at all:** ARIMA(1,0,1) pulls back towards the long-run average ICEN, close to 0, so its forecast path eventually crosses back over the threshold. How fast it does so decides the predicted length.

### Scoring

- **Absolute error:** |predicted − actual| in months.
- **Shared episodes only:** to compare fairly, each method is scored only on episodes where **all three** produced a forecast. That leaves **15 of the 23**.
  - Episodes 1–2: too early for any method.
  - Episodes 3, 4, 5, 8: fewer than 3 earlier same-phase episodes, so no regression.
  - Episodes 4, 5, 7, 9: the ARIMA path never ended the episode.

### Results

**Every episode** (months left, with absolute error in brackets; — means no forecast):

| ID | Phase | Forecast date | ICEN at confirmation | **Actual** | Median | Regression | ARIMA |
|---|---|---|---|---|---|---|---|
| 1 | La Niña | 2001-10 | −0.88 | 3 | — | — | — (too little history) |
| 2 | El Niño | 2002-07 | 0.67 | 0 | — | — | — (too little history) |
| 3 | El Niño | 2003-02 | 0.74 | 0 | 0 (0) | — | 1 (1) |
| 4 | La Niña | 2003-08 | −1.30 | 0 | 3 (3) | — | — (never ended) |
| 5 | La Niña | 2004-08 | −1.11 | 0 | 1.5 (1.5) | — | — (never ended) |
| 6 | La Niña | 2005-06 | −0.68 | 6 | 0 (6) | 4.06 (1.94) | 4 (2) |
| 7 | La Niña | 2006-07 | −0.76 | 0 | 1.5 (1.5) | 4.60 (4.60) | — (never ended) |
| 8 | El Niño | 2006-12 | 0.94 | 1 | 0 (1) | — | 1 (0) |
| 9 | La Niña | 2007-07 | −1.54 | 6 | 0 (6) | 0.00 (6) | — (never ended) |
| 10 | El Niño | 2008-08 | 0.69 | 1 | 0 (1) | 0.00 (1) | 1 (0) |
| 11 | El Niño | 2009-09 | 0.75 | 0 | 0.5 (0.5) | 0.48 (0.48) | 2 (2) |
| 12 | La Niña | 2010-11 | −1.24 | 4 | 1.5 (2.5) | 2.60 (1.40) | 13 (9) |
| 13 | La Niña | 2012-01 | −0.67 | 0 | 3 (3) | 2.35 (2.35) | 5 (5) |
| 14 | El Niño | 2012-07 | 0.94 | 0 | 0 (0) | 0.85 (0.85) | 3 (3) |
| 15 | La Niña | 2013-03 | −0.73 | 8 | 1.5 (6.5) | 1.78 (6.22) | 7 (1) |
| 16 | El Niño | 2014-09 | 1.15 | 2 | 0 (2) | 0.60 (1.40) | 3 (1) |
| 17 | El Niño | 2015-08 | 2.10 | **10** | 0 (10) | 4.44 (5.56) | 13 (3) |
| 18 | El Niño | 2017-04 | 1.29 | 0 | 0.5 (0.5) | 3.79 (3.79) | 12 (12) |
| 19 | La Niña | 2017-12 | −0.97 | 7 | 3 (4) | 3.00 (4.00) | 12 (5) |
| 20 | El Niño | 2019-03 | 0.78 | 0 | 0 (0) | 0.00 (0) | 3 (3) |
| 21 | La Niña | 2019-11 | −0.74 | 0 | 3.5 (3.5) | 3.41 (3.41) | 6 (6) |
| 22 | La Niña | 2020-10 | −1.19 | 8 | 3 (5) | 3.28 (4.72) | 14 (6) |
| 23 | La Niña | 2021-12 | −0.90 | **12** | 3.5 (8.5) | 3.34 (8.66) | 12 (0) |

**Scores on the 15 shared episodes:**

| Phase | Episodes | Median MAE | Median RMSE | **Regression MAE** | Regression RMSE | ARIMA MAE | ARIMA RMSE |
|---|---|---|---|---|---|---|---|
| El Niño | 7 | 2.00 | 3.88 | **1.87** | **2.65** | 3.43 | 5.01 |
| La Niña | 8 | 4.88 | 5.23 | **4.09** | **4.68** | 4.25 | 5.10 |
| All 15 | 15 | 3.53 | — | **3.05** | — | 3.87 | — |

MAE is the average error and RMSE the root mean square error, both in months. The "All" row is the average over the 15 episodes; her script prints only the phase rows.

### What the duration results show

**1. Regression is the best method in both phases,** but it only beats the median clearly for La Niña. A stronger ICEN at confirmation does go with a longer episode, which is the information regression adds. Its best forecast is the 2015–16 El Niño: ICEN 2.10 at confirmation, predicted 4.4 months left, against 10 actual. That's still too short, but much closer than the median's 0.

**2. Each method tends to err in one direction:**
- **The median forecasts too short.** Most past episodes had 0–3 months left at the forecast date, so its forecasts stay between 0 and 3.5 months. It misses every long episode: 15, 17, 19, 22 and 23, with errors of 4–10 months.
- **Regression is pulled towards the typical length.** It also forecasts too short for the long episodes (17, 22, 23), and too long for strong but short ones like episode 18 (3.8 predicted, 0 actual).
- **ARIMA forecasts too long more often than not.** It predicted too long in **12 of its 17 scored episodes**: 12 months for episode 18, which was already over, and 13 for episode 12, which had 4. But it's the only method that **gets the longest episodes right**: episode 23 exactly (12 for 12), episode 15 within 1, and episode 17 within 3.

**3. ARIMA wins on the long episodes but loses on the short ones.** Because ARIMA(1,0,1) pulls back towards normal slowly, it predicts long episodes. That pays off when an episode really is long and costs it when it isn't. For 4 strong La Niña episodes, the path never even recrossed −0.4 within 36 months.

**4. La Niña is much harder than El Niño.** Errors are about 4–5 months, against 2–3 for El Niño. Under the ±0.4 °C rule, La Niña episodes are longer (up to 17 months) and vary much more in length.

**5. The ±0.4 °C rule makes this harder than before.** Under the old > +0.5 / < −0.7 °C rule, the best errors were 1.83 months (El Niño) and 2.57 (La Niña). Now they're 1.87 and 4.09. The lower La Niña threshold produces longer episodes that are harder to predict.

**In short:** at the forecast date, the most useful single piece of information is how strong the episode is (ICEN at confirmation). The time-series path (ARIMA) helps only for the longest events, and none of her methods is reliable for long La Niñas.

### 7b. Added duration models

Both were added to `forecast_episode_duration.py` to fix the two weaknesses above: ARIMA's average path forecasts episodes as too long, and each method learns from only a handful of episodes.

**ARIMA sim: simulation instead of the average path**
- **How it works:** it uses the same ARIMA(1,0,1) fitted on the same ICEN history, but instead of the one average path it **simulates 1,000 ICEN paths**, 36 months ahead. For each path it finds the first month ICEN leaves the episode range. The forecast is the **median** of those months.
- **Why it's better:** the month the average path crosses the threshold is not the typical month real (noisy) paths cross it. A noisy path can cross early by chance even while the average is still inside the range, so the median end month comes sooner. That removes the forecast-too-long bias.
- **No end within 36 months:** if the median path never ends the episode, the forecast is capped at the window end and still scored. That never happened, so all 21 eligible episodes are scored, against 17 for the original ARIMA.

**Hazard model: a month-by-month end model, fitted on all phases together**
- **The training data:** every month of every past episode, from confirmation to its last month, becomes one row, labelled "ended this month" (1) or "carried on" (0). That's about 100+ rows instead of a handful of episodes.
- **The model:** regularised logistic regression (standardised inputs, C = 1) predicts the chance of ending in month *k* after confirmation. The inputs are:
  - *k*, the months since confirmation;
  - **strength**, the size of ICEN at confirmation;
  - **trend**, the change in ICEN from the episode's first month to confirmation, signed so that positive means strengthening;
  - the phase;
  - the calendar month, as sine and cosine.
- **The forecast:** chaining the monthly chances gives the probability of each possible last month. The forecast is the median. Months left = median last month − forecast date, with a minimum of 0.
- **Training data required:** it uses all past episodes whose end was known on the forecast date, from both phases together, and needs at least 5.

**Every episode** (months left; the **Actual** column is the truth):

| ID | Phase | Strength | Trend | **Actual** | Median | Regression | ARIMA | **Hazard** | **ARIMA sim** |
|---|---|---|---|---|---|---|---|---|---|
| 3 | El Niño | 0.74 | 0.26 | 0 | 0 | — | 1 | — | 0 |
| 4 | La Niña | 1.30 | 0.61 | 0 | 3 | — | — | — | 9 |
| 5 | La Niña | 1.11 | 0.22 | 0 | 1.5 | — | — | — | 5 |
| 6 | La Niña | 0.68 | −0.06 | 6 | 0 | 4.06 | 4 | 0 | 0 |
| 7 | La Niña | 0.76 | 0.24 | 0 | 1.5 | 4.60 | — | 3 | 2 |
| 8 | El Niño | 0.94 | 0.32 | 1 | 0 | — | 1 | 0 | 1 |
| 9 | La Niña | 1.54 | 0.95 | 6 | 0 | 0.00 | — | 0 | 7 |
| 10 | El Niño | 0.69 | 0.25 | 1 | 0 | 0.00 | 1 | 0 | 0 |
| 11 | El Niño | 0.75 | 0.28 | 0 | 0.5 | 0.48 | 2 | 1 | 1 |
| 12 | La Niña | 1.24 | 0.49 | 4 | 1.5 | 2.60 | 13 | 2 | 5 |
| 13 | La Niña | 0.67 | 0.08 | 0 | 3 | 2.35 | 5 | 1 | 1 |
| 14 | El Niño | 0.94 | 0.47 | 0 | 0 | 0.85 | 3 | 0 | 2 |
| 15 | La Niña | 0.73 | 0.20 | 8 | 1.5 | 1.78 | 7 | 0 | 3 |
| 16 | El Niño | 1.15 | 0.28 | 2 | 0 | 0.60 | 3 | 0 | 2 |
| 17 | El Niño | 2.10 | 1.22 | **10** | 0 | 4.44 | 13 | 2 | **9** |
| 18 | El Niño | 1.29 | 0.82 | 0 | 0.5 | 3.79 | 12 | 0 | 7 |
| 19 | La Niña | 0.97 | 0.45 | 7 | 3 | 3.00 | 12 | 2 | 5 |
| 20 | El Niño | 0.78 | 0.15 | 0 | 0 | 0.00 | 3 | 0 | 1 |
| 21 | La Niña | 0.74 | 0.14 | 0 | 3.5 | 3.41 | 6 | 2 | 2 |
| 22 | La Niña | 1.19 | 0.47 | 8 | 3 | 3.28 | 14 | 3 | 6 |
| 23 | La Niña | 0.90 | 0.49 | **12** | 3.5 | 3.34 | 12 | 2 | 5 |

Episodes 1–2 have no forecast from any method; — means no forecast.

**Scores on the same 15 shared episodes** (average error in months, RMSE in brackets):

| Phase | Episodes | Median | Regression | ARIMA | **Hazard** | **ARIMA sim** |
|---|---|---|---|---|---|---|
| El Niño | 7 | 2.00 (3.88) | 1.87 (2.65) | 3.43 (5.01) | **1.71** (3.16) | 1.86 (2.85) |
| La Niña | 8 | 4.88 (5.23) | 4.09 (4.68) | 4.25 (5.10) | 4.88 (5.69) | **3.25** (3.94) |
| **All** | 15 | 3.53 (4.65) | 3.05 (3.86) | 3.87 (5.06) | 3.40 (4.68) | **2.60** (3.47) |

**Direction of the errors on the 15 shared episodes:**

| Method | Too long | Too short | Exact | Average signed error |
|---|---|---|---|---|
| ARIMA (average path) | 11 | 2 | 2 | **+3.47 months** |
| **ARIMA sim** | 7 | 7 | 1 | **−0.60** |
| Regression | 5 | 9 | 1 | −1.60 |
| Median | 4 | 9 | 2 | −2.53 |
| Hazard | 3 | 9 | 3 | −2.87 |

**What the added models show:**
1. **ARIMA sim is the best duration method overall:** 2.60 months average error, 15% better than regression (3.05) and 33% better than ARIMA's average path (3.87).
   - It has the lowest error and RMSE for La Niña, the hard phase (3.25 against 4.09 for regression).
   - It's the only method without a lean in one direction (7 too long, 7 too short). The simulation alone turns ARIMA from forecasting +3.5 months too long on average into nearly unbiased.
   - It still gets the long events: 9 for the 15-month 2015–16 El Niño (actual 10) and 7 for the 2007 La Niña (actual 6).
   - It still sometimes forecasts too long, by 7 months for the 2017 El Niño and 9 for the 2003 La Niña.
2. **The hazard model is best for El Niño (1.71) but poor for La Niña (4.88).**
   - It learns that most episodes end within a few months of confirmation, and with a dozen or so past episodes it can't tell the long ones apart. It forecasts too short in 9 of 15 and never predicts more than 3 months.
   - So it's good at the typical short El Niño and misses the long La Niñas: it predicts 2 against an actual 12 for 2021–22.
   - With only 1 "ended" row per episode, it effectively has ~15–20 events to learn from, so more data is what it most needs.
3. **The pattern:** methods that use ICEN's whole path (ARIMA sim) handle the long episodes better. Methods driven by typical lengths (median, hazard, regression) handle the short ones better. A natural next step is to combine them, for example by adding the simulated ARIMA end month as an input to the hazard model.

**In short (with the added models):** simulating ICEN paths fixes ARIMA's main flaw and gives the best overall duration forecasts (2.6 months average error). The hazard model is promising for short El Niño episodes but needs more data than 2001–2022 provides.

---

## 8. Peak predictions (`forecast_peak_sst_arima_gam.py`)

### The question

**On the forecast date, how extreme will the drifter SST anomaly get over the rest of the episode?** For El Niño that's the highest anomaly to come, and for La Niña the lowest.

### How a forecast is made

For each episode with a forecast date from **January 2011 onward** (episodes 13–23):

1. **How many months to forecast.** The script uses **ARIMA's months-left prediction** from Section 7 as the horizon. That ties the peak forecast to the duration forecast, so a bad duration forecast weakens the peak forecast.
   - If ARIMA predicted 0 months left: "predicted episode already over", so no GAM forecast.
   - If ARIMA has no forecast: no GAM forecast.
2. **Which SST file.** It uses the file whose baseline ends **before** the forecast date:
   - forecasts in 2011–13 use the 2001–2010 baseline;
   - forecasts in 2014–17 use the 2001–2013 baseline;
   - forecasts in 2018–22 use the 2001–2017 baseline.
3. **The GAM forecast path.** For each month ahead, h = 1 … ARIMA months left, it fits a **separate model** (a direct forecast for each lead time). A GAM here is a regression where some inputs can have curved effects. For a target month t, the inputs are:
   - the SST anomaly h months before t, and h + 1 months before t: the latest two values known on the forecast date;
   - sine and cosine of the target month (season);
   - **ICEN from h + 2 months before t**, the latest available value, passed through a **quadratic spline** (3 knots, held flat beyond the range seen). This lets the effect of ICEN be curved, which is what makes the model a GAM.

   Each model is trained only on months whose SST was already known on the forecast date, and needs at least 36 training months. The forecast is the **maximum** of the path for El Niño, or the **minimum** for La Niña.
4. **Comparisons:**
   - **Persistence:** the SST anomaly in the forecast month ("it won't get more extreme than it is now").
   - **Historical median:** the median observed extreme over the remaining months of past same-phase episodes whose end was already known.
5. **The actual value.** The observed extreme of the SST anomaly over the months **after** the forecast date up to the episode's real end. The real end date is used **only** for this. Episodes with any missing SST month in that window aren't scored.

### Results

**Every episode** (°C; — means not computed):

| ID | Phase | Forecast date | Actual months left | ARIMA months left | **Actual extreme** | GAM | Persistence | Historical median |
|---|---|---|---|---|---|---|---|---|
| 13 | La Niña | 2012-01 | 0 | 5 | — (already over) | 0.122 | 0.309 | −0.480 |
| 14 | El Niño | 2012-07 | 0 | 3 | — (already over) | 0.487 | 0.629 | 0.112 |
| 15 | La Niña | 2013-03 | 8 | 7 | **−0.364** | −0.206 | −0.192 | −0.480 |
| 16 | El Niño | 2014-09 | 2 | 3 | **0.503** | 0.180 | 0.051 | 0.109 |
| 17 | El Niño | 2015-08 | 10 | 13 | **0.999** | 0.195 | 0.017 | 0.226 |
| 18 | El Niño | 2017-04 | 0 | 12 | — (already over) | 0.776 | 0.847 | 0.365 |
| 19 | La Niña | 2017-12 | 7 | 12 | **−0.313** | −0.042 | 0.012 | −0.283 |
| 20 | El Niño | 2019-03 | 0 | 3 | — (already over) | −0.011 | −0.069 | 0.209 |
| 21 | La Niña | 2019-11 | 0 | 6 | — (already over) | 0.021 | 0.048 | −0.367 |
| 22 | La Niña | 2020-10 | 8 | 14 | **−0.518** | −0.259 | −0.340 | −0.367 |
| 23 | La Niña | 2021-12 | 12 | 12 | — (SST gaps) | −0.250 | −0.350 | −0.375 |

**Coverage:**

| | Count |
|---|---|
| Episodes in the forecast period | 11 |
| Episodes that actually continued past the forecast date | 6 |
| Continued, but ARIMA predicted 0 left (missed) | 0 |
| GAM forecast issued although the episode had already ended | **5** (episodes 13, 14, 18, 20, 21) |
| Continued but incomplete SST, so unscored | 1 (episode 23) |
| **Scored** | **5** (episodes 15, 16, 17, 19, 22) |

**Absolute error for each scored episode (°C):**

| ID | Phase | GAM | Persistence | Historical median | Best |
|---|---|---|---|---|---|
| 15 | La Niña | 0.158 | 0.172 | 0.116 | Historical median |
| 16 | El Niño | **0.323** | 0.452 | 0.394 | GAM |
| 17 | El Niño | 0.804 | 0.982 | **0.773** | Historical median |
| 19 | La Niña | 0.271 | 0.325 | **0.030** | Historical median |
| 22 | La Niña | 0.259 | 0.178 | **0.151** | Historical median |

**Summary scores:**

| Phase | Episodes | ARIMA + GAM | Persistence | Historical median |
|---|---|---|---|---|
| El Niño | 2 | **0.564** (RMSE 0.613) | 0.717 (0.764) | 0.583 (0.613) |
| La Niña | 3 | 0.229 (0.235) | 0.225 (0.236) | **0.099** (0.111) |

Values are average errors in °C.

### What the peak results show

**1. The forecasts almost always underestimate how extreme the water gets.** In all 5 scored episodes, the GAM and persistence forecasts are closer to 0 than the actual extreme. The historical median is too mild in 4 of 5; it only overshoots for the 2013 La Niña (−0.48 against −0.36).
- The worst case is the **2015–16 El Niño**: the drifter SST anomaly reached **+1.00 °C**, but the GAM predicted +0.20, persistence +0.02 and the historical median +0.23.
- **Why the GAM does this:** its inputs are the latest SST and ICEN, which were still moderate in August 2015. Its training data has few strong warm events to learn from. And a regression always pulls extreme forecasts towards the average.

**2. The GAM beats persistence for El Niño but not for La Niña.**
- **El Niño:** 0.56 against 0.72 °C. The ICEN curve adds the knowledge that an ongoing El Niño tends to warm the water further.
- **La Niña:** about equal (0.229 against 0.225 °C). Cold anomalies in the drifter series are smaller and less tied to ICEN.

**3. The historical median is the best method overall.** It wins 4 of the 5 episodes and is best for La Niña by a wide margin (0.10 °C). La Niña extremes in the drifter series are similar from one episode to the next, around −0.3 to −0.5 °C, so "the typical past extreme" is a good guess. The GAM wins only episode 16 (2014 El Niño).

**4. The peak forecast depends on the duration forecast.**
- **Forecasts for episodes that had already ended:** ARIMA forecast too long, so 5 of the 11 GAM forecasts were for episodes that had in fact already ended. ARIMA predicted 3–12 more months for them. Those forecasts can't be scored, but in real use they'd be false warnings.
- **Wrong horizon length:** when ARIMA predicts too long (episodes 19 and 22: 12 and 14 months against 7 and 8), the GAM path covers months that aren't part of the episode. When it predicts too short (episode 15: 7 against 8), it can miss the actual extreme.
- **Under the old rule** there were 2 such forecasts for already-ended episodes, and ARIMA + GAM beat persistence for La Niña too (0.165 against 0.319). The ±0.4 °C rule makes ARIMA predict too long more often, and the peak forecast suffers.

**5. The sample is tiny.** Only 2 El Niño and 3 La Niña episodes are scored, so these rankings could easily change with more events.

**In short:** the ARIMA + GAM forecast helps somewhat for El Niño, but it consistently underestimates the extreme and inherits ARIMA's tendency to forecast episodes as too long. For La Niña, "a typical past extreme" works better than the model.

### 8b. Added peak models

Both were added to `forecast_peak_sst_arima_gam.py` to fix the main problem above: the GAM always predicts too mild an extreme.

**GAM sim: simulate whole paths, then take the extreme**
- **The problem:** the maximum of an **average** path is always milder than the typical maximum of a **real, noisy** path. The real SST wiggles above and below the average, and the extreme picks up those wiggles. That's why the original GAM forecasts were too mild in every episode.
- **The fix:**
  1. Take the GAM's average path, using the same models and horizon as before.
  2. Collect the GAM's own **past error paths**. For each training month, record the vector of errors at every lead time, so errors at neighbouring months stay linked, as real SST paths are.
  3. Simulate 1,000 paths: average path + a randomly chosen past error path.
  4. Take each simulated path's maximum (El Niño) or minimum (La Niña). The forecast is the **median** of these.
- **No future data:** the error paths come only from training months, all known on the forecast date.

**Blend:** the 50/50 average of the GAM sim and the historical median. The weight is fixed, not tuned, because 5 scored episodes can't support tuning.

**Every episode** (°C):

| ID | Phase | **Actual extreme** | GAM (average path) | **GAM sim** | **Blend** | Persistence | Historical median |
|---|---|---|---|---|---|---|---|
| 13 | La Niña | — (already over) | 0.122 | −0.055 | −0.268 | 0.309 | −0.480 |
| 14 | El Niño | — (already over) | 0.487 | 0.529 | 0.321 | 0.629 | 0.112 |
| 15 | La Niña | **−0.364** | −0.206 | **−0.347** | −0.414 | −0.192 | −0.480 |
| 16 | El Niño | **0.503** | 0.180 | **0.260** | 0.185 | 0.051 | 0.109 |
| 17 | El Niño | **0.999** | 0.195 | **0.532** | 0.379 | 0.017 | 0.226 |
| 18 | El Niño | — (already over) | 0.776 | 0.942 | 0.653 | 0.847 | 0.365 |
| 19 | La Niña | **−0.313** | −0.042 | **−0.321** | −0.302 | 0.012 | −0.283 |
| 20 | El Niño | — (already over) | −0.011 | 0.100 | 0.155 | −0.069 | 0.209 |
| 21 | La Niña | — (already over) | 0.021 | −0.230 | −0.299 | 0.048 | −0.367 |
| 22 | La Niña | **−0.518** | −0.259 | **−0.471** | −0.419 | −0.340 | −0.367 |
| 23 | La Niña | — (SST gaps) | −0.250 | −0.502 | −0.439 | −0.350 | −0.375 |

**Absolute error for each scored episode (°C):**

| ID | Phase | GAM | **GAM sim** | Blend | Persistence | Historical median |
|---|---|---|---|---|---|---|
| 15 | La Niña | 0.158 | **0.017** | 0.050 | 0.172 | 0.116 |
| 16 | El Niño | 0.323 | **0.243** | 0.318 | 0.452 | 0.394 |
| 17 | El Niño | 0.804 | **0.467** | 0.620 | 0.982 | 0.773 |
| 19 | La Niña | 0.271 | **0.008** | 0.011 | 0.325 | 0.030 |
| 22 | La Niña | 0.259 | **0.047** | 0.099 | 0.178 | 0.151 |

**Summary scores** (average error in °C, RMSE in brackets):

| Phase | Episodes | ARIMA + GAM | Persistence | Historical median | **GAM sim** | Blend |
|---|---|---|---|---|---|---|
| El Niño | 2 | 0.564 (0.613) | 0.717 (0.764) | 0.583 (0.613) | **0.355** (0.372) | 0.469 (0.493) |
| La Niña | 3 | 0.229 (0.235) | 0.225 (0.236) | 0.099 (0.111) | **0.024** (0.030) | 0.053 (0.064) |

**Is the improvement real?** The extreme of a simulated path grows with the number of months forecast, and the horizon comes from ARIMA, which often forecasts too many months (12 and 14 against 7 and 8 for episodes 19 and 22). To separate the two effects, the GAM sim was rerun with the **true** horizon. That's a diagnostic only; the true horizon isn't known in real forecasting.

| Average error (°C) | El Niño | La Niña |
|---|---|---|
| GAM average path, ARIMA horizon (original) | 0.564 | 0.229 |
| GAM average path, true horizon | 0.564 | 0.242 |
| GAM sim, true horizon | **0.408** | **0.072** |
| GAM sim, ARIMA horizon (as reported) | 0.355 | 0.024 |

- **Most of the gain is real.** Even with the true horizon, simulating the path cuts the error by about 30% for El Niño and 70% for La Niña.
- **Part of it is luck.** The rest, especially La Niña's drop from 0.072 to 0.024, comes from ARIMA's overlong horizons inflating the simulated extremes, which happens to offset the remaining underestimation. That wouldn't hold if ARIMA's horizons were accurate.

**What the added models show:**
1. **The GAM sim is the best peak method in all 5 scored episodes.**
   - **La Niña:** it's within 0.05 °C every time, beating even the historical median (0.024 against 0.099).
   - **El Niño:** it's the best method (0.355), but still well short for the 2015–16 event: 0.53 against an actual +1.00 °C. It's still too mild in 4 of 5 episodes, though much less so than before.
2. **The blend is second everywhere.** Mixing in the historical median helps when the model is unreliable, but here the GAM sim is already better than the median, so the blend only waters it down. With more episodes, a tuned weight might help.
3. **The forecasts for already-ended episodes remain.** The 5 forecasts for episodes that had already ended (13, 14, 18, 20 and 21) still come from ARIMA's average-path duration. Using the **ARIMA sim** duration (Section 7b) as the horizon would remove some of them, but it would also remove the lucky horizon effect above. It's the natural next change.

**In short (with the added models):** simulating whole paths fixes most of the underestimation. The GAM sim is the best peak method for both phases, though part of its La Niña advantage depends on ARIMA's overlong horizons, and strong El Niños are still underestimated.

---

## 9. SST by ENSO phase (`plot_icen_sst.py`)

The plot is saved as `ashita_humboldt_sst_icen_pm04.png`. It shows the location-corrected monthly drifter SST anomaly with a 3-month smoothed line, and ICEN with the ±0.4 °C lines, with the episodes shaded.

Average drifter SST anomaly in good-coverage months:

| Group | Months | Mean SST anomaly | Difference from neutral |
|---|---|---|---|
| Neutral (−0.4 < ICEN < +0.4) | 81 | +0.037 °C | — |
| El Niño episodes | 60 | +0.200 °C | **+0.163 °C** |
| La Niña episodes | 111 | −0.133 °C | **−0.170 °C** |

- **The drifter SST responds in both directions,** by about the same amount. This confirms the drifters detect coastal ENSO.
- **The response is small,** about ±0.17 °C on average, compared with ICEN values of 1–2 °C. The drifter series covers the whole Humboldt region, while ICEN measures only the warmest part, Niño 1+2 off Peru.

---

## 10. Overall conclusions

| Task | Best of her methods | **Best with the added models** | Takeaway |
|---|---|---|---|
| Next-month SST | Regression ≈ XGBoost, 0.195 °C (persistence 0.216) | — (no models added) | Lagged SST holds most of the signal, and ICEN adds almost nothing |
| **Duration** (months left) | Regression: 3.05 months (El Niño 1.87, La Niña 4.09) | **ARIMA sim: 2.60 months** (El Niño 1.86, La Niña 3.25). The hazard model is best for El Niño (1.71) | Simulating ICEN paths removes ARIMA's forecast-too-long bias. Strength at confirmation helps for short episodes. Long La Niñas are still the hardest |
| **Peak** SST to come | Historical median for La Niña (0.099 °C); GAM ≈ median for El Niño (0.56–0.58) | **GAM sim: El Niño 0.355, La Niña 0.024 °C** | Simulating whole paths fixes most of the underestimation, but part of the La Niña gain comes from ARIMA's overlong horizons, and strong El Niños are still too mild |

**Effect of moving to ±0.4 °C:**
- **More events:** 23 episodes instead of 19, and longer ones.
- **Duration:** La Niña gets harder to forecast (best error 2.57 → 4.09 months).
- **Peak:** ARIMA + GAM loses its La Niña advantage, and forecasts for already-ended episodes rise from 2 to 5.
- **Next-month SST:** overall results unchanged.

---

## 11. Limitations

- **Very few events:** 15 shared episodes for duration, 5 for peak (2 El Niño). None of these rankings is statistically secure.
- **Reconstructed inputs:** two of the three SST forecast files are my reconstruction. Her actual files may differ.
- **A stand-in for `data_cleaning.py`:** it gives the same `df` from a memory-safe cache. Her original can't run on an 8 GB laptop.
- **Ongoing episodes:** episode 23 (2021–22 La Niña) can't be scored for peak because of SST gaps.
- **ICEN is not drifter data.** Duration forecasts use ICEN only. Drifter data enters the next-month and peak forecasts through the SST anomaly series.
- **The threshold choice matters:** results change noticeably between ±0.4 °C and > +0.5 / < −0.7 °C. The group should agree on one definition.
- **The added models are tested on the same few episodes:** 15 for duration, 5 for peak. The ARIMA sim and GAM sim gains are large and consistent, but not statistically secure.
- **The GAM sim uses the model's errors on its own training months.** Those are a little smaller than its errors on new data, so the simulated range is slightly too narrow. Errors on held-out months would fix this.
- **The GAM sim depends on ARIMA's horizon:** part of its La Niña advantage comes from ARIMA's overlong horizons (see 8b).
- **The hazard model has very few events:** each past episode adds only one "ended" row, so about 15–20 events. A longer ICEN or Niño 1+2 record (back to the 1950s) would help it most.
- **The blend weight is fixed at 50/50,** not tuned.

## Next steps

1. **Use the ARIMA sim duration as the peak horizon:** fewer forecasts for already-ended episodes, and a fairer test of the GAM sim.
2. **Combine the duration methods:** for example, add the ARIMA sim end month as an input to the hazard model.
3. **Forecast the northern SST** (`sst_anom_north`, north of 30°S), where the coastal El Niño signal is strongest. This needs a change to her preprocessing script.
4. **Train duration models on a longer ICEN or Niño 1+2 record,** testing by leaving each episode out in turn.
5. **Report a likely range,** not just one number: the 10th–90th percentiles of the simulations already exist.

---

## Reproducing the results

1. **Relabel the ICEN data:** in `src/`, run `python relabel_icen.py`.
2. **Create the cache:** make sure `data/cache/forecast_obs.npz` exists by running Section 1 of `notebooks/archive/02_forecasting_pipeline.ipynb` once.
3. **Run the scripts in this order:**
   - `data_preprocessing_2010.py`, then the same script with `TRAIN_END_YEAR = 2013` and `2017` (and the matching output names);
   - `sst_monthly_anomalies.py`;
   - `forecast_monthly_sst.py`;
   - `forecast_episode_duration.py`;
   - `forecast_peak_sst_arima_gam.py`;
   - `plot_icen_sst.py`.

   On an 8 GB laptop, use a `data_cleaning.py` that loads `data/cache/forecast_obs.npz` instead of the full arrays.
4. **Or run `notebooks/archive/02_forecasting_pipeline.ipynb`.** It gives identical results for her original methods, plus ETS and BSTS duration methods. It doesn't yet include the hazard, ARIMA sim, GAM sim or blend models; those are only in the two scripts.

The added models use fixed random seeds (each episode's ID), so every run gives the same numbers.
