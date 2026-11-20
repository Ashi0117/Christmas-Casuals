import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
import sys
from pathlib import Path

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"

# sst_anomaly.csv is written by sst_anomaly.py
if not (CACHE / "sst_anomaly.csv").exists():
    subprocess.run([sys.executable, str(Path(__file__).with_name("sst_anomaly.py"))], check=True)

# Load calculated SST anomalies
df = pd.read_csv(
    CACHE / "sst_anomaly.csv",
    parse_dates=["time"]
)

# --------------------------------------------------
# ENSO PERIODS
# --------------------------------------------------

# El Niño: March 2015 - May 2016
el_nino = (
    (df["time"] >= "2015-03-01")
    & (df["time"] < "2016-06-01")
)

# La Niña: March 2007 - May 2008
la_nina = (
    (df["time"] >= "2007-03-01")
    & (df["time"] < "2008-06-01")
)


# --------------------------------------------------
# CREATE MAPS
# --------------------------------------------------

fig, axes = plt.subplots(
    1, 2,
    figsize=(16, 7),
    sharex=True,
    sharey=True
)

# El Niño
hb1 = axes[0].hexbin(
    df.loc[el_nino, "lon"],
    df.loc[el_nino, "lat"],
    C=df.loc[el_nino, "sst_anomaly"],
    reduce_C_function=np.mean,
    gridsize=45,
    cmap="seismic",
    vmin=-2.7,
    vmax=2.7,
    mincnt=1
)

axes[0].set_xlim(-89, -65)
axes[0].set_ylim(-49, -4)
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")
axes[0].set_title("El Niño\nMarch 2015 – May 2016")


# La Niña
hb2 = axes[1].hexbin(
    df.loc[la_nina, "lon"],
    df.loc[la_nina, "lat"],
    C=df.loc[la_nina, "sst_anomaly"],
    reduce_C_function=np.mean,
    gridsize=45,
    cmap="seismic",
    vmin=-2.7,
    vmax=2.7,
    mincnt=1
)

axes[1].set_xlim(-89, -65)
axes[1].set_ylim(-49, -4)
axes[1].set_xlabel("Longitude")
axes[1].set_title("La Niña\nMarch 2007 – May 2008")


# --------------------------------------------------
# COLOUR BAR
# --------------------------------------------------

cbar = fig.colorbar(
    hb1,
    ax=axes,
    orientation="vertical",
    fraction=0.025,
    pad=0.04
)

cbar.set_label("Mean SST Anomaly (°C)")

fig.suptitle(
    "Humboldt Region: Sea Surface Temperature Anomalies",
    fontsize=15
)

plt.show()