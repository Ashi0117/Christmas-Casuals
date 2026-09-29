# Download all libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.gridspec import GridSpec

CACHE = Path("cache")
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3})
pd.set_option("display.width", 200)

VARS = ["lon", "lat", "time", "ve", "vn", "sst"]
if not all((CACHE / f"{v}.npy").exists() for v in VARS + ["rowsize", "id"]):
    from clouddrift.datasets import gdp1h
    CACHE.mkdir(exist_ok=True)
    ds = gdp1h()
    for v in VARS + ["rowsize", "id"]:
        np.save(CACHE / f"{v}.npy", ds[v].values)

# Selected specific variables of interest only 
lon = np.load(CACHE / "lon.npy"); lat = np.load(CACHE / "lat.npy")
time = np.load(CACHE / "time.npy")
ve = np.load(CACHE / "ve.npy"); vn = np.load(CACHE / "vn.npy")
sst = np.load(CACHE / "sst.npy")
rowsize = np.load(CACHE / "rowsize.npy"); ids = np.load(CACHE / "id.npy")

# Calculate the overall speed using sqrt(ve^2 + vn^2)
traj_of_obs = np.repeat(np.arange(len(rowsize)), rowsize)
speed = np.hypot(ve, vn)

# Convert SST from Kelvin to Celsius
sst_c = sst - 273.15

# Study time - 2001 to 2022
time_pd = pd.to_datetime(time)

in_period = ((time_pd >= "2001-01-01") &
    (time_pd < "2023-01-01"))

# Selected region - Humboldt Region 
R = dict(lon=(-89, -65), lat=(-49, -4))

in_R = ((lon >= R["lon"][0]) & (lon <= R["lon"][1])
        & (lat >= R["lat"][0]) & (lat <= R["lat"][1]))

# All observations 
study = in_R & in_period

# Observations where SST is available (67,5557 unavailable)
valid_sst = study & np.isfinite(sst_c)

# Observations where velocity is valid
valid_velocity = study & np.isfinite(ve) & np.isfinite(vn)

# Observations where SST and velocity are valid 
valid_sst_velocity = study & np.isfinite(sst_c) & np.isfinite(ve) & np.isfinite(vn)

# print(f"Total study observations: {study.sum():,}")
# print(f"Observations with SST: {valid_sst.sum():,}")
# print(f"Missing SST: {(study & ~np.isfinite(sst_c)).sum():,}")
