import numpy as np
import pandas as pd
from pathlib import Path

CACHE = Path("cache")

# --------------------------------------------------
# LOAD CLEANED DATA
# --------------------------------------------------

lon = np.load(CACHE / "lon.npy")
lat = np.load(CACHE / "lat.npy")
time = np.load(CACHE / "time.npy")
sst = np.load(CACHE / "sst.npy")
valid_sst = np.load(CACHE / "valid_sst.npy")

# Convert SST from Kelvin to Celsius
sst_c = sst - 273.15

# Convert time
time_pd = pd.to_datetime(time)


# --------------------------------------------------
# USE ONLY VALID SST OBSERVATIONS
# --------------------------------------------------

df = pd.DataFrame({
    "lon": lon[valid_sst],
    "lat": lat[valid_sst],
    "time": time_pd[valid_sst],
    "sst": sst_c[valid_sst]
})


# --------------------------------------------------
# CREATE 1° x 1° SPATIAL CELLS
# --------------------------------------------------

df["lon_cell"] = np.floor(df["lon"]).astype(int)
df["lat_cell"] = np.floor(df["lat"]).astype(int)

# Calendar month
df["month"] = df["time"].dt.month


# --------------------------------------------------
# CALCULATE NORMAL SST
# --------------------------------------------------

# Calculate the 2001-2022 mean SST for each
# spatial cell and calendar month

baseline = (
    df.groupby(
        ["lon_cell", "lat_cell", "month"]
    )["sst"]
    .agg(["mean", "count"])
    .reset_index()
)

baseline = baseline.rename(
    columns={
        "mean": "normal_sst",
        "count": "baseline_count"
    }
)


# --------------------------------------------------
# REQUIRE ENOUGH OBSERVATIONS
# --------------------------------------------------

# A cell/month needs at least 100 observations
# to calculate its normal SST

baseline.loc[
    baseline["baseline_count"] < 30,
    "normal_sst"
] = np.nan


# --------------------------------------------------
# ADD NORMAL SST TO EACH OBSERVATION
# --------------------------------------------------

df = df.merge(
    baseline,
    on=["lon_cell", "lat_cell", "month"],
    how="left"
)


# --------------------------------------------------
# CALCULATE SST ANOMALY
# --------------------------------------------------

df["sst_anomaly"] = (
    df["sst"] - df["normal_sst"]
)


# --------------------------------------------------
# REMOVE EXTREME ANOMALIES
# --------------------------------------------------

# Remove observations without a reliable baseline
# and extreme anomaly outliers

df = df[
    df["sst_anomaly"].between(-5, 5)
].copy()


# --------------------------------------------------
# CHECK FINAL DATA
# --------------------------------------------------

print("\nFinal SST anomaly statistics:")
print(df["sst_anomaly"].describe())

print("\nNumber of observations:")
print(len(df))


# --------------------------------------------------
# SAVE DATA
# --------------------------------------------------

df.to_csv(
    CACHE / "sst_anomaly.csv",
    index=False
)

print("\nSaved: cache/sst_anomaly.csv")