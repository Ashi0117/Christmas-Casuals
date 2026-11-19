import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

CACHE = Path("cache")

# Load data
lon = np.load(CACHE / "lon.npy")
lat = np.load(CACHE / "lat.npy")
sst = np.load(CACHE / "sst.npy")
valid_sst = np.load(CACHE / "valid_sst.npy")

# Convert SST from Kelvin to Celsius
sst_c = sst - 273.15

# Humboldt region
R = dict(lon=(-94, -65), lat=(-54, -4))

# Plot
plt.figure(figsize=(12, 7))

hb = plt.hexbin(
    lon[valid_sst],
    lat[valid_sst],
    C=sst_c[valid_sst],
    reduce_C_function=np.mean,
    gridsize=45,
    cmap="turbo",
    vmin=4,
    vmax=30,
    mincnt=1
)

# Colour bar
cbar = plt.colorbar(hb)
cbar.set_label("Mean SST (°C)")

# EXACT boundaries from your cleaning
plt.xlim(R["lon"][0], R["lon"][1])
plt.ylim(R["lat"][0], R["lat"][1])

plt.xlabel("Longitude (°)")
plt.ylabel("Latitude (°)")

plt.title(
    "Mean Sea Surface Temperature in the Humboldt Study Region\n"
    "2001–2022"
)

plt.show()