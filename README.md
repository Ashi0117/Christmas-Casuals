# DATA3001 Group 8 README
## 🔧 Technical Documentation

### 📑 Table of Contents

**Technical Documentation**
- [Research Questions](#-research-questions)
- [Data Description](#-data-description)
- [Usage](#-usage)
- [Workflow](#-workflow)
- [Repository Structure](#-repository-structure)

**Final Report**
- [Introduction](#introduction)
- [Exec Summary](#exec-summary)
- [Brief Overview of El Nino and La Nina](#brief-overview-of-el-nino-and-la-nina)
- [Region Analysis](#region-analysis)
- [Initial Data Analysis](#initial-data-analysis)
- [Feature Engineering](#feature-engineering)
- [Coastal ENSO Indicator](#coastal-enso-indicator)
- [Data Cleaning and Preprocessing](#data-cleaning-and-preprocessing)
- [Forecasting Models](#forecasting-models)
- [Fish](#fish)
- [Findings](#findings)
- [Limitations](#limitations)
- [Future Work](#future-work)
- [References](#references)
- [AI Statements](#ai-statements)

### 🔍 Research Questions

We study how El Niño and La Niña change sea surface temperature (SST) and surface currents in the Humboldt Current off Peru and Chile. We then ask whether knowing that one of these events is under way improves forecasts:

| | Research question |
|---|---|
| **RQ1** | How large are the anomalous shifts in surface velocity (u′, v′) and SST across the Humboldt Current during El Niño and La Niña? |
| **RQ2** | Once an El Niño or La Niña is confirmed, can we predict how long it will last? |
| **RQ3** | Can we predict its effect on SST: the most extreme SST anomaly still to come? |

### 📓 Data Description

**Episode rule.** A coastal **El Niño** is ICEN ≥ +0.4 °C for at least 3 consecutive months, and a coastal **La Niña** is ICEN ≤ −0.4 °C for at least 3 consecutive months. This gives **23 episodes in 2001–2022: 10 El Niño and 13 La Niña.**

#### Size & Shape

| Data product | Rows | Row meaning |
|---|---|---|
| `data/drifter/humboldt_sst_readings.npz` | 2,537,111 | One hourly drifter reading in the study box (89°W–65°W, 49°S–4°S), with SST, velocity and the drifter's drogue-loss date |
| `data/processed/sst_forecast_data*.csv` | 264 each | One calendar month, 2001–2022 |
| `data/processed/icen_monthly_pm04.csv` | 309 | One calendar month, Jan 2001 – Sep 2026 |

#### Quality Notes

- **Sampling bias:** drifters are not spread evenly, and the south is much colder than the north, so raw averages are biased. Use the anomaly columns.
- **Coverage gaps:** months with fewer than 10 grid cells or 5 drifters are flagged `low_coverage` and are left out of training and scoring.
- **Drogue loss:** about half of the velocity readings come from drifters that have lost their drogue and are pushed by the wind. Velocity analysis uses drogued readings only.
- **Faulty SST:** readings outside 5–35 °C are dropped.

#### Table 1: monthly SST anomaly files (`sst_forecast_data*.csv`)

| Column | Description |
|---|---|
| `year`, `month` | Calendar month |
| `sst_anom` | Area-weighted regional SST anomaly (°C) against a baseline fitted only on earlier years |
| `n_cells` | Number of 2° grid cells with at least 24 readings that month |
| `n_drifters` | Number of distinct drifters that month |
| `low_coverage` | True if `n_cells` < 10 or `n_drifters` < 5 |

#### Table 2: ICEN episode file (`icen_monthly_pm04.csv`)

| Column | Description |
|---|---|
| `Date`, `Year`, `Month`, `Month_Name`, `season` | Calendar month and its centred 3-month season (e.g. DJF) |
| `ICEN` | Coastal El Niño index (°C) |
| `ENSO` | El Niño, La Niña or Neutral, using the ±0.4 °C, 3-month rule |
| `Episode` | El Niño, La Niña or No |
| `Episode_ID` | Episode number in time order (blank outside episodes) |

### 🏭 Usage

#### Environment

The project uses Python ≥ 3.11 and `uv`. The key packages are numpy, pandas, scipy, scikit-learn, statsmodels, xgboost, matplotlib and openpyxl. You need clouddrift only for the first download and cartopy only for the study-region map.

```bash
uv sync
```

If you don't use `uv`, run `notebooks/0_setup.ipynb` once first: it creates a project environment, installs the pinned packages and registers the Jupyter kernel.

On macOS, xgboost also needs `brew install libomp`.

#### Drifter data

The drifter data isn't in git. Run `2_data_cleaning.ipynb` first: it downloads the Clouddrift `gdp1h` arrays (about 8 GB) into `data/drifter/gdp1h/` and writes the regional extract to `data/drifter/`. Notebooks 3 and 4 read only that extract, so once it exists the `gdp1h/` arrays are needed only to rebuild it. If a download is interrupted, rerun the notebook and it picks up the missing arrays.

#### Standalone scripts

Standalone Python versions of the pipeline are in `src/`. The forecasting scripts include the extra hazard, ARIMA sim, GAM sim and blend models, and all scripts run from any folder:

```bash
python src/relabel_icen.py                  # ICEN episodes
python src/forecast_monthly_sst.py          # next-month SST
python src/forecast_episode_duration.py     # duration (RQ2), about 5 seconds
python src/forecast_peak_sst_arima_gam.py   # peak SST (RQ3)
```

The three forecasting scripts only need the CSVs in `data/processed/`.

### 🔄 Workflow

To replicate the results, run the notebooks in `notebooks/` in the order listed below. Run every cell top to bottom within each notebook. Each notebook opens with what it does, its inputs and its outputs, and explains each step in its markdown cells.

**Environment:** Python ≥ 3.11 with the packages in `pyproject.toml` (see [Usage](#-usage)).

#### `0_setup.ipynb`: Setup

**What it does**
- Checks the Python version and creates a project environment (`.venv/`) if one isn't already running, without touching base Python or Anaconda.
- Installs the exact package versions in `requirements.txt` and registers the **Christmas Casuals (.venv)** Jupyter kernel.
- On macOS, installs `libomp` for xgboost if it is missing, then checks that every package imports.

Skip this notebook if you use `uv sync`.

#### `1_enso_episodes.ipynb`: El Niño / La Niña episodes

**What it does**
- Reads Peru's coastal El Niño index (ICEN), monthly from January 2001.
- Labels each month El Niño, La Niña or Neutral with the ±0.4 °C, 3-month rule, and numbers each episode.
- Prints the episode table: 28 episodes in 2001–2026, 23 of them in the 2001–2022 study period.

**Outputs**
- `data/processed/icen_monthly_pm04.csv`

#### `2_data_cleaning.ipynb`: Drifter data cleaning

**What it does**
- Downloads the Clouddrift `gdp1h` arrays it needs into `data/drifter/gdp1h/` on the first run (needs internet and about 9.5 GB of free disk). This is the only notebook that downloads data.
- Opens the global `gdp1h` arrays without loading them into memory, and reads them in chunks of 2 million readings.
- Keeps readings in the study box (89°W–65°W, 49°S–4°S) and period (2001–2022), with valid velocity.
- Converts SST from Kelvin to °C and drops faulty values (outside 5 to 35 °C) and readings on the Atlantic side of the Andes (south of 40°S, east of 71°W).
- Recovers each reading's drifter ID and saves each drifter's drogue-loss date for the velocity analysis.

**Outputs**
- `data/drifter/humboldt_sst_readings.npz`: the regional extract, used by notebooks 3 and 4. The first run downloads the data and takes a while; later runs load the extract in seconds.

#### `3_sst_anomalies.ipynb`: SST anomalies (feature engineering)

**What it does**
- Fits the normal SST for each place and time of year (B-splines in latitude and longitude, with annual and six-month cycles), using **only years before each forecast period**, so no future information leaks in.
- Subtracts it from every reading, averages the anomalies in 2° cells and combines the cells with area weighting.
- Flags low-coverage months.

**Outputs**
- `data/processed/sst_forecast_data_2011_2013.csv` (baseline 2001–2010)
- `data/processed/sst_forecast_data_2014_2017.csv` (baseline 2001–2013)
- `data/processed/sst_forecast_data.csv` (baseline 2001–2017)

#### `4_exploratory_analysis.ipynb`: Exploratory analysis (RQ1)

**What it does**
- Loads the regional extract from notebook 2 and computes location-corrected SST anomalies.
- Compares the SST anomaly with ONI and Niño 1+2.
- Measures the current response to El Niño and La Niña, using drogued drifters only.
- Compares fish catch with coastal events and drifter SST, and tests anchoveta catch forecasts.

It needs the extract from notebook 2, plus `oni.ascii.txt`, `sstoi.indices` and `fish_data.xlsx` from `data/raw/`. It does not depend on notebooks 1 or 3.

**Outputs**
- The figures in `figures/` (SST vs ONI and Niño 1+2, forecast skill, fish catch, anchoveta models).

#### `5_forecast_next_month_sst.ipynb`: Next-month SST forecast

**What it does**
- Trains on 2001–2017 and tests on 2018–2022 (58 months).
- Compares persistence, linear regression on lagged SST and season, regression plus lagged ICEN, and XGBoost.
- Reports MAE and RMSE overall and by ENSO phase.

**Outputs**
- Error tables (printed).

#### `6_forecast_duration_and_peak.ipynb`: Duration and peak SST forecasts (RQ2 and RQ3)

**What it does**
- **Duration:** once an episode is confirmed (its 3rd month, plus 2 months for ICEN to be published), forecasts how many months it has left. ARIMA(1,0,1) is fitted to the ICEN history and forecast forward; the first month it crosses back inside ±0.4 °C is the predicted end. ETS and BSTS are tested too.
- **Peak SST:** ARIMA's predicted end sets the horizon. A Generalised Additive Model (recent SST anomalies, season and a curved effect of ICEN) forecasts the monthly SST anomaly, and the highest (El Niño) or lowest (La Niña) point is the forecast peak.
- **Baselines:** historical median and linear regression for duration; persistence and historical median for the peak.
- **Evaluation:** MAE and RMSE on exactly the same episodes for every method (15 for duration, 5 for the peak), using only information available on the forecast date.

Duration and peak share one notebook because the peak forecast reuses the duration code and its ARIMA forecasts.

**Outputs**
- Episode-by-episode forecast tables and MAE / RMSE summaries (printed).

#### Summary

Raw drifter readings → regional extract → location-corrected SST anomalies → El Niño / La Niña episodes from ICEN → next-month, duration and peak-SST forecasts compared against simple baselines.

### 📁 Repository Structure

```
Christmas-Casuals/
├── README.md
├── main_README.md             ← this file: technical documentation and final report
├── pyproject.toml / uv.lock / requirements.txt / .python-version
├── notebooks/                 ← run in order, 0 to 6
│   ├── 0_setup.ipynb
│   ├── 1_enso_episodes.ipynb
│   ├── 2_data_cleaning.ipynb
│   ├── 3_sst_anomalies.ipynb
│   ├── 4_exploratory_analysis.ipynb
│   ├── 5_forecast_next_month_sst.ipynb
│   ├── 6_forecast_duration_and_peak.ipynb
│   └── archive/               the earlier combined notebooks
├── src/                       ← standalone scripts (forecasting, plotting, preprocessing)
├── data/
│   ├── drifter/               downloaded by notebook 2, not in git (gdp1h/ arrays and regional extract)
│   ├── raw/                   ICEN, ONI, Niño 1+2, fish catch
│   └── processed/             relabelled ICEN, monthly SST anomaly files
├── figures/                   all figures (archive_oni/ holds early ONI-based figures)
└── docs/
    ├── 01_exploratory_analysis_explained.md
    ├── 02_forecasting_pipeline_explained.md
    ├── forecasting_results.md
    └── presentation_speech.docx
```

The two `docs/*_explained.md` walkthroughs describe the earlier combined notebooks in `notebooks/archive/`: `01` matches notebook 4, and `02` covers notebooks 1–3, 5 and 6. `docs/forecasting_results.md` documents the standalone scripts in `src/`.




# DATA3001 Group 8 Final Report - How do El Niño and La Niña affect the Humboldt current?

## Introduction

Our group will investigate how El Niño and La Niña affect near-surface temperature and currents in the Humboldt Current system, using Global Drifter Program (GDP) observations from 2001 to 2022. We will compare drifter sea surface temperature (SST) and velocity across El Niño, La Niña and neutral phases, build models to test whether ENSO information improves predictions of these variables, and use the results to estimate the economic cost of ENSO-driven disruption to the region's fisheries. Our final product is a set of ENSO-phase comparisons, an evaluated model, and a business case linking ocean anomalies to fishery losses.

## Exec Summary

We found a b and c

## Brief Overview of El Nino and La Nina

El Niño and La Niña are two opposite phases of the El Niño Southern Oscillation, a weather phenomenon which affect ocean temperatures across the Pacific. Under normal conditions, trade winds push warm surface water westward, allowing colder, nutrient-rich water to rise near the coast of South America, in a process called upwelling. During El Niño, these trade winds weaken, so less cold water reaches the surface and the eastern Pacific becomes warmer. During La Niña, the trade winds become stronger, bringing more cold water to the surface and creating cooler conditions.
These changes can affect marine ecosystems and fisheries, especially in the Humboldt Current region, which is the focus of our study.

To define an El Niño or La Niña event, we initially used NOAA's Oceanic Niño Index (ONI for short), which takes SST readings from a pre-defined region named Niño 3.4. We followed NOAA's definition of El Niño or La Niña as a shift of ±0.5°C in the corresponding direction. These figures can be found at https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/.


## Region Analysis
<img width="3200" height="1800" alt="image" src="https://github.com/user-attachments/assets/af329a58-1aa7-4b30-98c8-c7457a92b6c8" />

Figure 1: Map of the Humboldt Current overlaid with our region box. Base map is from Natural Earth, overlay done using Cartopy in Python.

Our group was fascinated by El Niño and La Niña and we wanted to investigate whether the impact these phenomena would have on drifters. We also wanted to choose a region that had a tangible economic impact to aid our business case. The Humboldt Current checked both of these requirements, as it is close to the Niño 3.4 region and provides 20-30% of the world's marine catch. We defined our region as shown in the image above, with coordinates 89-65°W and 4-49°S.

The Humboldt Current flows northward along the west coast of South America, past Chile and Peru. Upwelling brings cold, nutrient-rich seawater to the surface, providing ideal conditions for marine life and making this region extremely rich in fishery resources. This region is heavily influenced by the El Niño-Southern Oscillation (ENSO). During El Niño events, warmer surface waters weaken the upwelling, reducing nutrient availability and disrupting fish populations and fishing activities. In contrast, La Niña typically brings cooler conditions, which help strengthen upwelling and increase marine productivity.

In this analysis, we utilized approximately 2.64 million observations from 695 drifters, with about 99% of the records collected between 2001 and 2022. These observations allowed us to compare sea surface temperatures and current speeds under different ENSO conditions.


## Initial Data Analysis
Before building any models, we explored how the Humboldt current responds to El Niño and La Niña. We looked at 2 variables from the drifter data, the Sea surface temperature and wave velocity, and compared periods of El Niño and La Niña against neutral periods.

SST:
We calculated sea surface temperature anomalies, meaning how far the temperature is from what is normal for that location and time of year. 

<img width="1439" height="673" alt="Screenshot 2026-10-01 at 12 56 09 pm" src="https://github.com/user-attachments/assets/14b232cb-7e4d-4cde-a88c-a221527edade" />
Figure 1 compares the El Niño of March 2015 to May 2016 with the La Niña of March 2007 to May 2008. During El Niño, sea surface temperature rises by 1 to 2 degrees Celsius in places. During La Niña, it falls by a similar amount. In both events the strongest effect occurs between 15 and 30 degrees south. The maps also show considerable variation between neighbouring areas, so the response is not uniform across the region.

Wave Velocity:
<img width="1216" height="970" alt="image" src="https://github.com/user-attachments/assets/365998e4-b9c4-4890-a3f6-4b920bb30e71" />

In neutral conditions, trade winds influence the waves to flow westward in the north. Figure 2 shows drifter velocity. The top left panel gives the average flow from 2001 to 2022. Westward flow is shown in red and eastward flow in blue.


## Feature Engineering
<img width="936" height="869" alt="image" src="https://github.com/user-attachments/assets/0432a621-ce16-4b93-8c75-9d9a53968d2a" />


While exploring SST patterns, we noticed that any modelling we tried was largely unsuccessful due to the location of drifters being the main indicator of SST. As we see in the figure above (mean_sst.png), we see that drifters in the northern part of our region were generally warmer, with average temperatures ranging from 10 degrees to 24 degrees Celsius. This is largely due to the northerly flow of the Humboldt Current bringing warmer surface waters northward, while upwelling causes colder waters to rise up. We decided that we would create a new variable, **insert new variable** to mitigate this. This involved finding the mean drifter temperatures for each 1 degree by 1 degree grid, then subtracting this temperature from all observations taken inside the grid, effectively neutralising the effect of location on temperature. Thus, any further variation in temperature could be assigned to seasonality or an El Niño or La Niña event.

## Coastal ENSO Indicator
We identified coastal El Niño and La Niña episodes using the Coastal El Niño Index (ICEN). Since, our study focuses on the Humboldt Current, ICEN was more appropriate as its geographic focus allows us to identify warm or cold events more accurately than ENSO conditions in the central equatorial Pacific where timing and intensity are slightly different because of time lag. Like Oceanic Nino Index (ONI), ICEN calculates the three-month moving of sea surface temperature anomalies in the Niño 1+2 region instead of Niño 3.4 region. 

As detailed in 1_enso_episodes.ipynb, an El Niño episode required ICEN to be greater to or equal to +0.4°C for at least three consecutive months while a La Niña episode required ICEN to be less than or equal to -0.4°C. We considered the third month as a confirmation and issued the duration forecast two months later to account for the assumed publication delay. 

## Data Cleaning and Preprocessing
Here, we refer to the notebook 2_data_cleaning.ipynb. For our study, we used hourly drifter sea surface temperature (SST) which were converted from Kelvin to degrees Celsius. We filtered extreme values and outliers using a range of -2 to 35°C.

As explained in feature engineering, each SST was changed to account for ocean conditions, latitude and longitude. Then, we calculated SST anomaly as the observed temperature minus the expected temperature at a location and time of the year. Months represented by fewer than 10 cells or fewer than 5 drifters were flagged as having low coverage and were not used.

## Forecasting Models 
The episode-duration and peak forecasting models are implemented in notebook 6_forecast_duration_and_peak.ipynb.

### Remaining Episode Duration
We compared five forecasting methods using ICEN and historical episode outcomes, namely:
1. Historical Median
2. Linear Regression
3. ARIMA
4. Exponential Smoothing
5. Bayesian Structural Time Series

We used two benchmarks: the historical median and linear regression. The historical median used the median remaining duration of earlier episodes of the same phase whose end dates were known. Linear regression used the ICEN value in the third qualifying month to predict remaining duration. 

We then evaluated three time-series models that forecast future ICEN values and predict the episode end. ARIMA(1,0,1) forecasted a single monthly ICEN path over 36 months and identified the first month in which the predicted index was no longer in the episode's threshold range. The range was defined as the first month in which the predicted ICEN fell below +0.4°C for an El Niño while it was greater than -0.4°C for a La Niña. Exponential smoothing simulated future monthly ICEN paths and used the median first threshold-crossing time across the simulations. Lastly, Bayesian structural time series model simulated monthly ICEN paths from a bayesian time-series model and used the same median crossing rule as ETS. 

We compared the five methods on 15 episodes with a duration estimate from every model, including seven El Niño and eight La Niña episodes. We evaluated accuracy using mean absolute error (MAE) and root mean squared error (RMSE) in months, and reported results overall and by ENSO phase.

### Remaining Peak SST anomaly
We forecast the most extreme monthly regional SST anomaly after the forecast month and before the coastal ENSO episode ended. We defined the extreme as the highest monthly anomaly for El Niño and the lowest monthly anomaly for La Niña.

We selected ARIMA as our prediction model for duration episode and therefore the end date predicted by ARIMA determined how many months aheads to forecast SST. When ARIMA estimated zero months remaining, we did not predict any SST anomaly.

Our two benchmarks here were persistence and historical median. The former used the regional SST anomaly in the forecast month as the predicted value. The latter used the medium of the observed remaining extremes from earlier episodes whose end dates were known.

Our final model was a generalised additive model (GAM). A strong coastal El Niño may affect SST differently from a weak one. Therefore, the non-linearity of a GAM could show how the effect of ICEN changes across its range while still accounting for recent SST anomalies and season. Using the information available in the forecast month, we fitted separate GAMs to predict SST anomalies over different periods and up to the episode end predicted by ARIMA. Each model used the two most recent monthly regional SST anomalies, seasonal factor of the target month and a smooth effect of the latest ICEN value. We then selected the highest or lowest value of predicted monthly SST anomaly depending on the phase. 

For evaluation, we calculated the observed extreme measured from the month after forecast to the actual end of the episode. We included only episodes with usable SST data for every month in that period. As for episode duration, we used MAE and RMSE in °C for each ENSO phase. ARIMA + GAM and persistence were compared on 5 episodes consisting of 2 El Niño and 3 La Niña. The historical median was performed on 4 episodes only.

## Fish
<img width="2263" height="3057" alt="image" src="https://github.com/user-attachments/assets/bd0e9ecf-d9db-47a6-9ce8-53d7b60c17e4" />

We wanted to link fishing data to our model in order to potentially quantify the effect of El Niño and La Niña on fisheries in the Humboldt Current. We obtained data from Sea Around Us, whose website has been linked in our references. They provided catch data for each individual species in the Humboldt Current from the 1980s to 2019, however we only used Peruvian anchoveta data. Peruvian anchoveta is the most caught fish in the world and typically accounts for more than 80% of the catch in the Humboldt Current, hence we used its catch numbers as our primary fish metric.

Our first attempt to model catch data and El Niño and La Niña was somewhat uninformative, as shown above in the second graph. We expected to see a negative correlation between SST and anchoveta numbers, as a higher SST would create less favourable conditions for fish due to reduced upwelling. This was somewhat observed, as the two sets of data returned a negative correlation coefficient of -0.13. During the extremely strong El Niño in 2016, anchoveta numbers went down more than one standard deviation, which supported our hypothesis. However, other El Niño and La Niña did not get picked up by the data. Other species shown in the graph provided similarly uncertain results.

<img width="2263" height="1019" alt="image" src="https://github.com/user-attachments/assets/ce2525b2-78e0-4246-b4fe-d6b1be0b4f8a" />
We then attempted to model the catch numbers for anchoveta using an ARIMA model. We compared it to two baseline persistent models, which are showed above, one of them including SST and the other without. Our model performed marginally better than the persistent models, however there was very little correlation once again. Other attempts at modelling produces similar results, showing little correlation between SST and fish catch data. Hence, we were not able to successfully model or tangibly quantify the effect of El Niño and La Niña on fishing activity in the Humboldt Current.

## Findings
<img width="2200" height="760" alt="image" src="https://github.com/user-attachments/assets/17de79f3-75d8-4d12-b9b0-96f57593c7f8" />

Our findings cover two forecasting targets. We want to estimate the remaining duration of an event and the strongest SST anomaly occurring after the forecast date which is the peak for an ENSO event. First, for episode duration, we compared ARIMA against historical median and linear regression as benchmarks and we evaluated all three on the same episodes. If we consider La Nina events, ARIMA achieved the lowest mean absolute error at 2.57 months compared with 2.67 months for linear regression and 3.07 months for the historical median. ARIMA also had the lowest RMSE which suggests fewer large errors overall. For El Nino, ARIMA performed as equally good as the historical median and they both achieved a mean absolute error of 1.83 months. However, linear regression had the lowest RMSE. Therefore, we can see that ARIMA was not consistently the strongest duration model across both phases.

Next, we asked: within the remaining event, what is the strongest SST anomaly we can expect? For the remaining SST extreme, we used ARIMA’s predicted duration to define the forecast window and then we applied GAM to forecast monthly drifter SST anomalies. We selected the warmest predicted anomaly for El Niño and the coldest for La Niña.

Compared with persistence, for El Niño, the average absolute error fell from 0.786 to 0.608 degrees Celsius, an improvement of around 23%. For La Niña, it fell from 0.319 to 0.165 degrees—a reduction of almost half. Thus showing that the model was more effective than carrying the current value forward. 

However, the historical median performed best for the single El Niño event available for the three-model comparison. For La Niña, ARIMA plus GAM outperformed both benchmarks. So, the more complex model offered a clearer advantage for La Niña, while a simple historical benchmark remained valuable for El Niño.
The evaluation included only one El Nino and three La Nina events with complete SST observations so these comparisons describe a small set of events. Therefore, limiting how broadly we can generalise the differences for peak SST.  
Overall, ARIMA estimated remaining duration with average absolute errors of around 1.8 to 2.6 months, matching or improving on the historical median in both phases. Our combined ARIMA–GAM model also improved SST-extreme forecasts over persistence, with the strongest advantage for La Niña.

## Limitations
The primary limitation to our project was the few El Niño and La Niña events we had to work with. In total, we had 23 total events to work with, of which we assigned 5 episodes to be test episodes. With such a small model evaluation dataset, we were aware that any evaluation would have high variance and uncertainty regarding the actual performance of these models. We tried to counteract this by combining different model types for episode duration and peak forecasting, however we still acknowledge that this is a major limitation.

## Future Work
<img width="2200" height="900" alt="image" src="https://github.com/user-attachments/assets/6f2848db-a57d-4e13-aa95-e5e641d6c7c5" />

Given more time, we would have investigated drifters in other regions and how they correlate with drifters in the Humboldt Current during El Niño or La Niña periods. The above image, 'sst_vs_oni.png' shows NOAA's Oceanic Niño Index (ONI) overlaid with our Humboldt SST anomaly data. There is little correlation between both plots, with drifter data missing most major peaks and troughs, including the major 2015-2016 El Niño. This lack of correlation led to our aforementioned decision to use ICEN values instead, which matched up with our data better. We did not get the opportunity to investigate whether this lack of correlation was because of drifters and ONI measuring different phenomena or because of locational differences. For example, we would have looked into drifters near Mexico or Australia, which were similar distances from the ONI measurement region. If these drifters also had little correlation with ONI, we would have tried to benchmark our El Niño and La Niña events differently, perhaps not using traditional datasets.

The GDP dataset also contained 6-hourly observations from 2022 to 2025, however we only used hourly data from 2001 to 2022. We did not initially anticipate needing this extra data, as we failed to consider that number of El Niño and La Niña events was more important than number of individual drifter observations. This dataset would have given us an extra El Niño event from May 2023 to June 2024, which would have been quite valuable. Changing our model to incorporate 6-hourly data would have required restructuring our data and models, which we ran out of time to do.

## References

Sea Around Us. (n.d.). Sea Around Us: Fisheries, ecosystems and biodiversity data. https://www.seaaroundus.org/

National Oceanic and Atmospheric Administration. (n.d.). Atlantic Oceanographic and Meteorological Laboratory. https://www.aoml.noaa.gov/

Instituto del Mar del Perú. (n.d.). Servicio de Información Oceanográfica del Fenómeno El Niño (SIO-FEN). https://siofen.imarpe.gob.pe/


## AI Statements
Our group used AI for coding, research and some scriptwriting. As all members of our group had never worked with a dataset as complex as the GDP, we had trouble with the technical setup, which we found ChatGPT and Claude to be quite helpful for. When working with complex models such as GAMs and XGBoost, we also used AI to understand and troubleshoot them. We found that AI was very useful for most coding tasks. We used Claude to compile our code and to create the final GitHub repository. Claude was somewhat useful for this, however we encountered some technical errors regarding setup. There were some technical gaps in understanding for Claude when working with the GDP dataset, perhaps due to a lack of technical documentation.

For research, our group had very little previous knowledge or understanding of global climate patterns or oceanography. Thus, we used AI for a lot of our research into these topics. For example, we asked ChatGPT to explain potential time lags between observed El Niño effects and changes in our specified region. AI was somewhat useful for this, giving us vague time intervals, but we decided that we would go in a different direction to avoid these time lags completely. A lot of other research in understanding El Niño and La Niña, was done generally without AI, as we wanted to gain a more comprehensive understanding of why these phenomena occur.

For scriptwriting, we used AI for some of it, however more than 80% of the script and final report was written by us. AI was a useful tool for writing, helping us cut down some parts of our speech and also turn bullet points into proper paragraphs.
