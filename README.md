<img width="2263" height="1019" alt="image" src="https://github.com/user-attachments/assets/5e952167-12ce-4f49-b2ac-2a22aa8b0315" /># DATA3001 Group 8 README
## Technical Documentation

install a b c
explain what the files do


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
<img width="1439" height="673" alt="Screenshot 2026-11-22 at 14 51 19" src="https://github.com/user-attachments/assets/2f33efe8-62f1-4797-904c-db4da7d3a9df" />
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
<img width="2263" height="1019" alt="image" src="https://github.com/user-attachments/assets/4f1fc5f3-5f22-451e-b812-1c842160cb99" />
We attempted to model fishing numbers using our ARIMA model, essentially 


## Findings

## Limitations
The primary limitation to our project was the few El Niño and La Niña events we had to work with. As previously mentioned, we had 

Secondly, the model's need for real-time data means that any delay in drifter observations will heavily limit the model's effectiveness and accuracy. If we apply this model to a real life context, fisheries need information about SST a few weeks to a month in advance to properly evaluate their business decisions.

## Future Work
<img width="2200" height="900" alt="image" src="https://github.com/user-attachments/assets/6f2848db-a57d-4e13-aa95-e5e641d6c7c5" />

Given more time, we would have investigated drifters in other regions and how they correlate with drifters in the Humboldt Current during El Niño or La Niña periods. The above image, 'sst_vs_oni.png' shows NOAA's Oceanic Niño Index (ONI) overlaid with our Humboldt SST anomaly data. There is little correlation between both plots, which led to our aforementioned decision to use ICEN values instead. We did not get the opportunity to investigate whether this lack of correlation was because of drifters and ONI measuring different phenomena or because of locational differences. If these drifters also had little correlation with ONI, we would have tried to benchmark our El Niño and La Niña events differently, perhaps not using traditional datasets.

## References

## AI Statements
Specific examples of where AI tools helped and where they were wrong.

Our group used AI for coding, research and some scriptwriting. As all members of our group had never worked with a dataset as complex as the GDP, we had trouble with the technical setup, which we found ChatGPT and Claude to be quite helpful for. When working with complex models such as GAMs and XGBoost, we also used AI to understand and troubleshoot them. We found that AI was very useful for most coding tasks.

For research, our group had very little previous knowledge or understanding of global climate patterns or oceanography. Thus, we used AI for a lot of our research into these topics. For example, we asked ChatGPT to explain potential time lags between observed El Niño effects and changes in our specified region. AI was somewhat useful for this, giving us vague time intervals, but we decided that we would go in a different direction to avoid these time lags completely. A lot of other research in understanding El Niño and La Niña, was done generally without AI, as we wanted to gain a more comprehensive understanding of why these phenomena occur.

For scriptwriting,
...
