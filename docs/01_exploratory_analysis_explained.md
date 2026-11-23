> **Note:** this document describes the archived notebook `notebooks/archive/01_exploratory_analysis.ipynb`, the earlier version of `4_exploratory_analysis.ipynb`. Cell numbers and file paths refer to that notebook, which keeps its drifter data in `data/cache/`. The current pipeline downloads the drifter arrays once in `2_data_cleaning.ipynb` (into `data/drifter/gdp1h/`), and notebook 4 loads the regional extract from there. See the top-level `README.md`.

# `01_exploratory_analysis.ipynb` explained

This file walks through the notebook from top to bottom: what each cell does, why, what it produces, and what the results show. Cell numbers count from 0, as in the notebook.

**The question:** how do coastal El Niño and La Niña events change the Humboldt Current's sea surface temperature (SST) and flow, measured with Clouddrift drifters? Can those changes be forecast, and do they show up in the fish catch?

---

## Quick reference

| Cells | Part | Main output |
|---|---|---|
| 0–2 | Load and clean the drifter data | `df`, about 2.5 million hourly readings |
| 3–6 | Location-corrected SST anomalies | `sst_monthly`, checks against ONI |
| 7–9 | SST vs ENSO indices; coastal events from Niño 1+2 | `coastal` event table, 3 figures |
| 10–12 | Current (velocity) anomalies | velocity columns in `sst_monthly` |
| 13–14 | Baseline forecasts once an event is flagged | skill tables, `fig3_forecast_skill.png` |
| 15–16 | Fish catch with coastal events, 1982–2019 | `fish_catch_coastal_enso.png` |
| 17–18 | Fish catch vs drifter SST, 2001–2022 | `fish_sst` table, `fish_vs_drifter_sst.png` |
| 19–20 | Linear model forecasting anchoveta catch | score table, `anchoveta_linear_model.png` |

**Run order:** cells 1–9 first. Cells 10–14 (currents and event forecasts) are independent of the fish section. Then run 16, 18 and 20 in that order, because each fish cell uses variables from the one before.

---

## Part 1: Loading and cleaning the drifter data (cells 0–2)

**Cell 0** (`pip install matplotlib`) is a one-off install. It isn't needed once matplotlib is installed, and it isn't valid Python, so skip it.

**Cell 1: building a regional extract.**
- The Clouddrift `gdp1h` dataset holds hourly readings from every drifter worldwide, about 197 million. The full arrays (position, time, SST and velocity) take up about 7 GB, which crashes an 8 GB laptop if loaded all at once.
- If they aren't already there, the cell downloads them to `data/cache/` as `.npy` files.
- It then reads them from disk in chunks of 2 million and keeps only readings that:
  - fall in the study box: **89°W–65°W, 49°S–4°S**;
  - fall in the study period: **2001–2022**;
  - have valid SST and both velocity components.
- The result is saved as `data/cache/humboldt_obs.npz` (112 MB), so later runs skip this step.

**Cell 2: the clean table `df`.**
- It converts SST from Kelvin to °C and works out speed as √(ve² + vn²).
- It adds year, month and day of year.
- It keeps SST between 5 and 35 °C. Real winter SST south of 40°S falls below 10 °C, so a higher minimum would wrongly remove cold readings. Values outside this range are sensor errors.
- It removes readings south of 40°S and east of 71°W. Those are in the Atlantic, east of the Andes, and not part of the Humboldt system.
- **Result:** 2,537,111 readings.

---

## Part 2: Location-corrected SST anomalies (cells 3–6)

**The problem.** Drifters aren't spread evenly, and the south of the region is much colder than the north. A month with more drifters in the south looks cold even if the ocean hasn't changed. The simple monthly average has a **0.92 correlation with the drifters' average latitude**, so it mostly tracks where the drifters were, not the ocean.

**The fix (cell 3).** Compare every reading with what is normal for that place and time of year, then average those differences (anomalies) instead of the raw temperatures.

1. **The baseline model.** A smooth surface gives normal SST as a function of latitude, longitude and day of year:
   - smooth spline curves across latitude and longitude, combined into a map;
   - a separate map for the annual cycle and for the six-month cycle;
   - a smoothness penalty, because many 1° cells, especially in the north, have few drifters and miss some months.
2. **Fitting.** The model is fitted to monthly averages for each 1° cell, so one drifter's many hourly readings don't dominate. Each year gets equal total weight, and the fit is built one year at a time to save memory.
3. **Each year is left out of its own baseline.** Every reading is compared with a baseline fitted without its own year. Otherwise an unusual year would shift its own definition of normal and hide part of its signal.
4. **Monthly series.**
   - Anomalies are first averaged within 2° cells. A cell needs at least 24 readings, about one drifter-day, to count.
   - The cells are then averaged with area weighting, because cells cover less area further south.
   - This gives the main series `sst_anom`, plus `sst_anom_north` and `sst_anom_south`, split at 30°S.
5. **Coverage flag.** A month is marked `low_coverage` if it has fewer than 10 cells or fewer than 5 drifters.
6. **Back to temperature.** `sst_adjusted` adds the anomaly to the regional normal for that calendar month. `sst_simple` keeps the uncorrected average for comparison.

**Result:** 260 of 264 months have data, and 34 of them are low coverage.

**Cell 4: did the correction work?**

| Series | Std dev (°C) | Corr. with drifter latitude | Corr. with ONI, same month | Corr. with ONI 4 months later |
|---|---|---|---|---|
| Simple mean | 1.76 | **0.92** | 0.11 | 0.08 |
| `sst_anom` | 0.45 | **0.06** | 0.17 | 0.28 |
| `sst_anom_north` | 0.54 | 0.04 | 0.27 | 0.34 |
| `sst_anom_south` | 0.49 | 0.12 | 0.00 | 0.15 |

- **The sampling bias is gone:** the link to drifter latitude falls from 0.92 to 0.06.
- **The corrected series tracks El Niño better,** especially in the north. ONI is the standard index for El Niño in the central Pacific.
- **The link to ONI is stronger 4 months later.** The Humboldt SST changes before ONI does.

**Cell 5** plots the simple mean against the corrected series, then the corrected anomaly, the north and south anomalies, and ONI.

**Cell 6** checks the baseline against the raw 1° average map. They correlate at 0.967, with an RMS difference of 1.02 °C. The baseline reproduces the real temperature pattern, and the differences are mainly in poorly sampled cells.

---

## Part 3: SST against the El Niño indices (cells 7–9)

- **Cells 7–8** plot the whole-region and northern anomalies against ONI and save `sst_vs_oni.png` and `sst_north_vs_oni.png`.
- **Cell 9** switches to **Niño 1+2**, the SST index for the waters off Peru and Ecuador, which is closer to the Humboldt Current than ONI.
  - Niño 1+2 comes from NOAA CPC's `sstoi.indices`.
  - **Correlation with Niño 1+2:** 0.50 for the northern anomaly and 0.37 for the whole region. Both are clearly higher than with ONI.
  - **Coastal events:** a coastal El Niño is a run of at least 3 months where the centred 3-month average of Niño 1+2 is at or above **+0.4 °C**. A coastal La Niña is the same at or below **−1.0 °C**. These thresholds follow Peru's coastal El Niño index (ICEN).
  - **The `coastal` table:** 16 events in 2001–2022, 11 El Niño and 5 La Niña. The largest is the 15-month El Niño of April 2015 to June 2016.
  - **Output:** `sst_vs_nino12.png`, showing the drifter anomalies with Niño 1+2 and the events shaded. It also adds `nino12` to `sst_monthly`.

---

## Part 4: Current response (cells 10–12)

**Cell 10** explains the method, which is the same as for SST: a seasonal baseline for each velocity component, an anomaly for each reading, then area-weighted monthly series.

**Cell 11: velocity anomalies.**
- **Only drogued readings are used.** A drogue is the underwater sail that makes a drifter move with the water. Once a drifter loses it, wind pushes the drifter directly and its velocity no longer represents the current.
  - Drogue-loss dates come from `data/cache/drogue_lost_date.npy`.
  - **50% of readings are drogued.**
- The same spline model gives baselines for eastward (`ve`) and northward (`vn`) velocity, with each year left out of its own baseline as before.
- **Result:** about 1.27 million velocity anomalies, with a typical size of 0.12–0.13 m/s.

**Cell 12: monthly velocity series.**
- **Current core:** 15–40°S, east of 80°W, giving `vn_anom_core` and `ve_anom_core`.
- **North of 30°S:** `vn_anom_north` and `ve_anom_north`.
- The Humboldt flows north, so a **negative `vn_anom` means weaker flow.**
- **Same-month correlation with Niño 1+2:**

| Series | Correlation |
|---|---|
| `vn_anom_core` | −0.12 |
| `ve_anom_core` | 0.04 |
| `vn_anom_north` | −0.01 |
| `ve_anom_north` | 0.02 |

- The core's northward flow weakens slightly in warm conditions, as expected, but the link is weak. Velocity is a much noisier signal than SST.

---

## Part 5: Baseline forecasts for coastal events (cells 13–14)

**What is forecast.** A coastal event counts as detected ("flagged") once it has lasted 3 months. At months 3, 4 and 5 of the event, three things are forecast:
- **duration:** the event's total length in months;
- **sst_peak:** the peak drifter SST anomaly north of 30°S, as a 3-month trailing average;
- **vn_mean:** the average northward-velocity anomaly in the current core over the event.

**Setup.**
- **Real-time event detection:** events are flagged with a *trailing* 3-month average of Niño 1+2, because the centred average looks one month ahead. This shifts the event dates in this table about a month later than in cell 9's table.
- **Signs:** anomalies are signed so that positive means the expected response. La Niña events are sign-flipped and pooled with El Niño, because 5 La Niña events are too few on their own.
- **Fair testing:** every forecast leaves the event being forecast out of the data it learns from.

**Three methods are compared.** There are only about 16 events, so none of them fits parameters:

| Method | How it forecasts |
|---|---|
| Climatology | The average of all other events |
| Persistence | The event ends now: duration = k, peak = peak so far, velocity = average so far |
| Baseline | Uses past events that also lasted at least k months ("analogs"): median length; peak so far plus the analogs' median further rise; velocity so far blended with the analogs' later months |

**Results (pooled, skill vs climatology: 1 = perfect, 0 = no better):**

| Target | k = 3 | k = 4 | k = 5 |
|---|---|---|---|
| Duration, baseline | 0.09 | 0.09 | 0.08 |
| Duration, persistence | −0.31 | −0.28 | 0.08 |
| Peak SST, baseline = persistence | 0.75 | 0.68 | 0.77 |
| Velocity, baseline | 0.51 | 0.74 | 0.85 |

**What the results show:**
- **Duration is the hard target.** The baseline only just beats climatology, with an error of about 1.3–1.4 months.
- **Peak SST:** the analogs' median further rise is 0, so the baseline equals persistence. Usually the drifter SST has already peaked by the time the event is flagged.
- **Velocity skill looks high,** but mostly because the months already observed make up much of a short event's average.

These results are the bar a real forecasting model has to beat. The figure is saved as `fig3_forecast_skill.png`, with bootstrap 95% intervals.

---

## Part 6: Fish catch and coastal events (cells 15–16)

**The data.** `data/raw/fish_data/fish_data.xlsx` holds Sea Around Us catch records for the Humboldt Current Large Marine Ecosystem (LME 13). It covers 1950–2019 in yearly tonnes per species, country and sector.
- **Anchoveta is about 57–69% of the catch,** depending on the period.
- Peru lands 68% and Chile 30%.

**Cell 16** plots yearly catch for 1982–2019 in five panels: total, anchoveta, South American pilchard, Chilean jack mackerel and jumbo flying squid.
- The coastal events from Niño 1+2 are shaded, using the same rule as cell 9 with its `coastal_events` function and thresholds.
- The plot starts in 1982 because Niño 1+2 starts then. That way it includes the two extreme coastal El Niños, 1982–83 and 1997–98.
- **Output:** `fish_catch_coastal_enso.png`.

**What it shows:**
- **The two extreme El Niños match the big anchoveta crashes:**
  - catch fell to almost nothing in 1983–84;
  - it fell from 9 to 2 million t in 1998, then recovered to 10.5 million t in 1999.
- **Over 1982–2019, El Niño years usually bring a drop:**
  - median change in anchoveta catch: −25% in El Niño years vs +35% in neutral years (p = 0.01);
  - catch fell in 11 of 15 El Niño years;
  - total catch: −18% vs +16% (p = 0.003).
- **La Niña shows no matching increase.** There are only 6 La Niña years, too few to tell.
- **Jumbo squid does the opposite:** its catch fell in all 5 La Niña years that could be compared.
- **The other species follow long-term changes rather than events.** Pilchard collapsed in the 1990s, jack mackerel declined after 1997, and squid rose in the 2000s.

(The event-year comparison was run as a separate analysis. Only the figure is in the notebook.)

---

## Part 7: Fish catch against the drifter SST (cells 17–18)

**Cell 18** sets the catch against the location-corrected drifter SST anomaly from cell 3.
- **Yearly SST anomaly:** the average of good-coverage months, with at least 6 needed. This drops 2001 and 2003, which had too few drifters.
- **`fish_sst` table:** one row per year for 2001–2019, with catch for each species and the drifter SST anomaly.
- **The figure** (`fish_vs_drifter_sst.png`) has six panels:
  1. the drifter SST anomaly, with the monthly line and yearly-average bars;
  2. SST and anchoveta on one scale, both as standard deviations from their own average. Anchoveta is log-transformed and has the long-term trend removed first, so the panel shows year-to-year swings. This avoids a two-axis chart;
  3. to 6. catch for total, anchoveta, jack mackerel and squid. Pilchard is left out because it's near zero after 2001.

**Results:**
- **Correlation of the yearly catch change with same-year SST:**

| Catch | Correlation |
|---|---|
| Total | −0.06 |
| Anchoveta | −0.07 |
| Jack mackerel | +0.11 |
| Squid | −0.27 |

- **Anchoveta with the trend removed vs SST:** r = −0.13 over 17 years.
- **2014–2017 fits the expected pattern:** warm SST, up to +1.9 standard deviations, goes with a poor anchoveta catch, which rebounds in 2018 as SST falls.
- **2010 breaks the pattern:** the coldest year also has one of the worst catches.

**Why the link is weak in the drifter years:**
- The 2001–2019 period has no event as strong as 1983 or 1998.
- The catch data is yearly, so a 3–6 month event gets averaged away.
- Peru's fishing quotas and season closures drive much of the catch.

---

## Part 8: Linear model forecasting anchoveta (cells 19–20)

**Cell 20** tests whether drifter SST improves a one-year-ahead forecast of anchoveta catch.

| Model | Predicts log catch in year t from |
|---|---|
| Persistence (reference) | Last year's catch, no fitting |
| Catch only | Last year's catch |
| Catch + SST (forecast) | Last year's catch + last year's SST anomaly, all known before the year starts |
| Catch + SST (nowcast) | Last year's catch + the same year's SST anomaly |

**Testing.** Each year is predicted by a model fitted only on earlier years, with at least 6 years of training data. The data covers 2005–2019 (15 years with every input), and the forecasts cover 2011–2019 (9 years).

**Results:**

| Model | Typical error | Skill vs persistence |
|---|---|---|
| Persistence | ±52% (2.5 million t) | — |
| Catch only | ±52% | −1% |
| Catch + SST (forecast) | ±55% | −5% |
| Catch + SST (nowcast) | ±56% | −7% |

- **Fitted on all 15 years:** +1 °C of SST anomaly goes with a **17% lower catch the next year**. That's the expected direction, but it isn't statistically significant (p = 0.51, R² = 0.27).
- **Adding drifter SST makes the forecast slightly worse.** With 15 years, the extra coefficient adds more noise than signal.
- **Output:** `anchoveta_linear_model.png`, showing the actual catch and both models' forecasts.

### The code (cell 20)

This is copied exactly from the notebook. It needs `fish_sst` from cell 18, and the colour constants (`INK`, `BLUE`, `ORANGE`, `MUTED`, `GRID`) from cell 5.

```python
# ============================================================================
# LINEAR MODEL: PREDICT ANCHOVETA CATCH FROM LAGGED CATCH AND DRIFTER SST
# Needs the fish-vs-SST cell above (fish_sst: yearly catch + drifter SST anomaly).
#
# Target: log anchoveta catch in year t (log, so errors are proportional).
# Models, all fitted by ordinary least squares:
#   persistence     catch(t) = catch(t-1), no fitting; the reference to beat
#   catch only      log catch(t) ~ log catch(t-1)
#   catch + SST     log catch(t) ~ log catch(t-1) + SST anomaly(t-1)
#                   (a true forecast: everything is known before year t starts)
#   catch + SST now log catch(t) ~ log catch(t-1) + SST anomaly(t)
#                   (a nowcast: needs the SST of the year being predicted)
# Testing: expanding window. Each year is predicted by a model trained only on
# earlier years, so no future data leaks in. All models are scored on the same years.
# ============================================================================
import statsmodels.api as sm

MIN_TRAIN_YEARS = 6

anch = pd.DataFrame({"log_anch": np.log(fish_sst["Anchoveta"]), "sst": fish_sst["sst_anom"]})
anch["log_anch_lag1"] = anch["log_anch"].shift(1)
anch["sst_lag1"] = anch["sst"].shift(1)
anch = anch.dropna()            # years with every input (SST is missing for 2001 and 2003)

anch_models = {
    "Catch only": ["log_anch_lag1"],
    "Catch + SST (forecast)": ["log_anch_lag1", "sst_lag1"],
    "Catch + SST (nowcast)": ["log_anch_lag1", "sst"],
}

rows = []
for i in range(MIN_TRAIN_YEARS, len(anch)):
    train, test = anch.iloc[:i], anch.iloc[[i]]
    row = {"year": test.index[0], "actual": test["log_anch"].iloc[0],
           "Persistence": test["log_anch_lag1"].iloc[0]}
    for name, inputs in anch_models.items():
        fit = sm.OLS(train["log_anch"], sm.add_constant(train[inputs])).fit()
        row[name] = fit.predict(sm.add_constant(test[inputs], has_constant="add")).iloc[0]
    rows.append(row)
anch_pred = pd.DataFrame(rows).set_index("year")

methods = ["Persistence", *anch_models]
log_err = anch_pred[methods].sub(anch_pred["actual"], axis=0)
tonnes_err = np.exp(anch_pred[methods]).sub(np.exp(anch_pred["actual"]), axis=0) / 1e6
anch_scores = pd.DataFrame({
    "MAE (log)": log_err.abs().mean(),
    "Typical error (%)": (np.exp(log_err.abs().mean()) - 1) * 100,
    "MAE (million t)": tonnes_err.abs().mean(),
    "Skill vs persistence": 1 - log_err.abs().mean() / log_err["Persistence"].abs().mean(),
})
print(f"Years used: {anch.index.min()}–{anch.index.max()} ({len(anch)}); "
      f"forecast years: {anch_pred.index.min()}–{anch_pred.index.max()} ({len(anch_pred)})")
print("\nOut-of-sample errors (each year predicted from earlier years only)")
print(anch_scores.round(3).to_string())

# The full-sample fit, to read the coefficients (not a test of skill)
full_fit = sm.OLS(anch["log_anch"], sm.add_constant(anch[anch_models["Catch + SST (forecast)"]])).fit()
print("\nCatch + SST (forecast), fitted on all years")
print(full_fit.summary2().tables[1][["Coef.", "Std.Err.", "P>|t|"]].round(3).to_string())
sst_effect = (np.exp(full_fit.params["sst_lag1"]) - 1) * 100
print(f"R² = {full_fit.rsquared:.2f}, n = {int(full_fit.nobs)}. "
      f"+1 °C of SST anomaly goes with a {sst_effect:+.0f}% change in next year's catch "
      f"(p = {full_fit.pvalues['sst_lag1']:.2f}).")

# Figure: actual catch and the out-of-sample predictions
fig, ax = plt.subplots(figsize=(11, 4.8), constrained_layout=True)
x = pd.to_datetime([f"{y}-07-01" for y in anch_pred.index])
lines = [("actual", "Actual catch", INK, 2.4), ("Catch only", "Catch only", BLUE, 1.8),
         ("Catch + SST (forecast)", "Catch + SST (forecast)", ORANGE, 1.8)]
for col, label, color, lw in lines:
    ax.plot(x, np.exp(anch_pred[col]) / 1e6, color=color, lw=lw, marker="o", ms=6, mec="white", mew=1.5,
            label=label)
ax.set_ylim(bottom=0)

# Direct labels at the line ends, nudged apart so they never overlap
ends = sorted(((np.exp(anch_pred[col].iloc[-1]) / 1e6, label) for col, label, _, _ in lines))
min_gap = 0.06 * ax.get_ylim()[1]
placed = []
for y, label in ends:
    y = max(y, placed[-1] + min_gap) if placed else y
    placed.append(y)
    ax.annotate(label, (x[-1], y), xytext=(10, 0), textcoords="offset points", va="center",
                fontsize=8.5, color=INK)
ax.set_xlim(x[0] - pd.Timedelta(days=200), x[-1] + pd.Timedelta(days=900))
ax.set_ylabel("Million tonnes", color=MUTED)
ax.set_title("Anchoveta catch: actual vs one-year-ahead linear model forecasts", loc="left", color=INK)
ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1, 1), ncols=3, fontsize=8.5, labelcolor=MUTED)
ax.grid(False, axis="x")
ax.grid(True, axis="y", color=GRID, lw=0.7)
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(colors=MUTED)
fig.savefig("anchoveta_linear_model.png", dpi=200, bbox_inches="tight", pad_inches=0.2)
plt.show()
```

### Printed output

```text
Years used: 2005–2019 (15); forecast years: 2011–2019 (9)

Out-of-sample errors (each year predicted from earlier years only)
                        MAE (log)  Typical error (%)  MAE (million t)  Skill vs persistence
Persistence                 0.416             51.529            2.530                 0.000
Catch only                  0.421             52.349            2.555                -0.013
Catch + SST (forecast)      0.436             54.718            2.652                -0.050
Catch + SST (nowcast)       0.443             55.662            2.747                -0.065

Catch + SST (forecast), fitted on all years
               Coef.  Std.Err.  P>|t|
const          8.985     3.687  0.031
log_anch_lag1  0.425     0.234  0.094
sst_lag1      -0.189     0.275  0.506
R² = 0.27, n = 15. +1 °C of SST anomaly goes with a -17% change in next year's catch (p = 0.51).
```

### Year-by-year forecasts (million tonnes)

Each forecast comes from a model trained only on the years before it.

| Year | Actual | Persistence | Catch only | Catch + SST (forecast) |
|---|---|---|---|---|
| 2011 | 10.51 | 4.91 | 4.51 | 5.08 |
| 2012 | 5.76 | 10.51 | 8.73 | 10.37 |
| 2013 | 6.76 | 5.76 | 8.08 | 7.49 |
| 2014 | 3.94 | 6.76 | 7.79 | 7.61 |
| 2015 | 4.66 | 3.94 | 6.08 | 6.18 |
| 2016 | 3.52 | 4.66 | 5.81 | 5.30 |
| 2017 | 4.16 | 3.52 | 4.47 | 3.27 |
| 2018 | 7.42 | 4.16 | 4.81 | 4.37 |
| 2019 | 4.60 | 7.42 | 6.81 | 6.79 |

**Reading the forecasts:**
- **All three methods miss the big swings** in 2011, 2012 and 2018. None of them can predict a jump the year before it happens.
- **The SST model's worst miss is 2012.** It forecast 10.4 million t after the big 2011 catch, against an actual 5.8 million t.
- **SST helps a little in 2013 and 2016,** where the SST model is closer than the catch-only model. Over the nine years it's slightly worse.

### Reading the coefficients

| Term | Coefficient | p | Meaning |
|---|---|---|---|
| `const` | 8.985 | 0.03 | Intercept on the log scale |
| `log_anch_lag1` | 0.425 | 0.09 | Last year's catch carries over only partly: a catch 10% above normal predicts about 4% above normal the next year |
| `sst_lag1` | −0.189 | 0.51 | +1 °C of SST anomaly → e^−0.189 − 1 ≈ −17% next year. The direction is as expected, but it can't be told apart from zero |

R² = 0.27 means last year's catch and SST together explain about a quarter of the year-to-year variation in log catch, when fitted to all 15 years.

**Conclusion:** the current data gives no evidence that drifter SST improves anchoveta catch forecasts. Testing against persistence makes that a sound negative result.

---

## Overall findings

1. **Correcting for drifter location is essential.** Without it, monthly SST mostly reflects where the drifters were (r = 0.92 with latitude). After it, the anomaly tracks coastal El Niño (r = 0.50 with Niño 1+2 in the north).
2. **The drifter SST responds to coastal events,** most strongly north of 30°S. The current's response is real but weak and noisy.
3. **Forecasting events once they're detected:** event length is hard to forecast. Peak SST and average current are mostly already set by month 3.
4. **Fish:**
   - Strong coastal El Niños cause large anchoveta crashes (1983, 1998), and El Niño years usually bring lower catch over 1982–2019.
   - In the 2001–2019 drifter years, the link is too weak to detect or to improve forecasts.
   - Jumbo squid is the most promising species for a follow-up, because it showed the most consistent link to SST.

## Limitations

- **Short record:** there are about 16 coastal events and 15–19 years where catch and drifter data overlap. That limits every statistical test.
- **Catch measures fishing, not fish.** Quotas and season closures, especially for Peru's anchoveta, affect catch alongside the ocean.
- **Coarse catch data:** catch is only available by year and ends in 2019, while the drifter data runs monthly to 2022.
- **Coverage gaps:** 34 months have low drifter coverage. Half of the velocity readings are unusable because the drifter had lost its drogue.

## Files

**Inputs:**
- `data/cache/*.npy`, `data/cache/humboldt_obs.npz`, `data/cache/drogue_lost_date.npy`: drifter data.
- `data/raw/oni.ascii.txt`: the Oceanic Niño Index.
- `data/raw/sstoi.indices`: NOAA CPC Niño 1+2.
- `data/raw/fish_data/fish_data.xlsx`: catch data.

**Figures created:**
- `sst_vs_oni.png`
- `sst_north_vs_oni.png`
- `sst_vs_nino12.png`
- `fig3_forecast_skill.png`
- `fish_catch_coastal_enso.png`
- `fish_vs_drifter_sst.png`
- `anchoveta_linear_model.png`

**Environment:** Python ≥ 3.11 with the project packages (`uv sync`, or run `notebooks/0_setup.ipynb`). The notebook needs numpy, pandas, scipy, matplotlib, statsmodels, `openpyxl` for the Excel file, and clouddrift for the first download.
