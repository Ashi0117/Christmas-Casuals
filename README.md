# DATA3001 Group 8 README
## Technical Documentation

install a b c
explain what the files do


# DATA3001 Group 8 Final Report - How do El Niño and La Niña affect the Humboldt current?

## Introduction

Our group will investigate how El Niño and La Niña affect near-surface temperature and currents in the Humboldt Current system, using Global Drifter Program (GDP) observations from 2001 to 2022. We will compare drifter sea surface temperature (SST) and velocity across El Niño, La Niña and neutral phases, build models to test whether ENSO information improves predictions of these variables, and use the results to estimate the economic cost of ENSO-driven disruption to the region's fisheries. Our final product is a set of ENSO-phase comparisons, an evaluated model, and a business case linking ocean anomalies to fishery losses.

## Exec Summary

We found a b and c

## Brief Overview of El Nino and La Nina

El Niño and La Niña are two opposite phases of ENSO, which affect ocean temperatures across the Pacific. 
Under normal conditions, trade winds push warm surface water westward. This allows colder, nutrient-rich water to rise near the coast of South America, in a process called upwelling. During El Niño, these trade winds weaken, so less cold water reaches the surface and the eastern Pacific becomes warmer. During La Niña, the trade winds become stronger, bringing more cold water to the surface and creating cooler conditions.
These changes can affect marine ecosystems and fisheries, especially in the Humboldt Current region, which is the focus of our study.


## Region Analysis

The Humboldt Current flows northward along the west coast of South America, past Chile and Peru.
As the map on the left shows, upwelling brings cold, nutrient-rich water to the surface. This supports marine life and makes the region highly productive for fishing.
The figure on the right shows global marine catches, including the Southeast Pacific, labelled Area 87. This highlights the importance of the region for global fisheries.
El Niño can reduce upwelling and disrupt fish populations and fishing activity.
For our analysis, we have about 2.64 million observations from 695 drifters, with roughly 99 percent of the observations recorded between 2001 and 2022.


## Initial Data Analysis
<img width="1439" height="673" alt="Screenshot 2026-10-01 at 12 56 09 pm" src="https://github.com/user-attachments/assets/14b232cb-7e4d-4cde-a88c-a221527edade" />

## Feature Engineering
As this map shows, average temperature varies a lot across the region and as has a larger seasonal component changing around 6 degrees over the year. Therefore the raw regional average rose and fell with drifter density and time of year, not with real climate events.
So we used temperature anomalies instead. For each reading, we subtracted it by its normal temperature for that location and time of year. What’s left is how much warmer or colder the water is than usual, so a month with more drifters in the north compares fairly with one that has more in the south.

While exploring SST patterns, we noticed that any modelling we tried was largely unsuccessful due to the location of drifters being the main indicator of SST. As we see in the figure above (mean_sst.png), we see that drifters in the northern part of our region were generally warmer, with average temperatures ranging from 10 degrees to 24 degrees Celsius. This is largely due to the northerly flow of the Humboldt Current bringing warmer surface waters northward, while upwelling causes colder waters to rise up. We decided that we would create a new variable, **insert new variable** to mitigate this. This involved finding the mean drifter temperatures for each 1 degree by 1 degree grid, then subtracting this temperature from all observations taken inside the grid, effectively neutralising the effect of location on temperature.
## Episode Duratio

## Peak

## Fish

## Findings

## Limitations

## Future Work

## References

## AI Statements
Specific examples of where AI tools helped and where they were wrong.

Our group used AI for coding, research and some scriptwriting. As all members of our group had never worked with a dataset as complex as the GDP, we had trouble with the technical setup, which we found ChatGPT and Claude to be quite helpful for. When working with complex models such as GAMs and XGBoost, we also used AI to understand and troubleshoot them. We found that AI was very useful for most coding tasks.

For research, our group had very little previous knowledge or understanding of global climate patterns or oceanography. Thus, we used AI for a lot of our research into these topics. For example, we asked ChatGPT to explain potential time lags between observed El Niño effects and changes in our specified region. AI was somewhat useful for this, giving us vague time intervals, but we decided that we would go in a different direction to avoid these time lags completely. A lot of other research in understanding El Niño and La Niña, was done generally without AI, as we wanted to gain a more comprehensive understanding of why these phenomena occur.

For scriptwriting,
...
