import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from pathlib import Path
from matplotlib.colors import LogNorm

CACHE = Path("cache")

# Study region
LON_MIN, LON_MAX = -89, -65
LAT_MIN, LAT_MAX = -49, -4
GRID_SIZE = 2

# Load data
lon = np.load(CACHE / "lon.npy")
lat = np.load(CACHE / "lat.npy")
time = pd.to_datetime(np.load(CACHE / "time.npy"))
rowsize = np.load(CACHE / "rowsize.npy").astype(int)
ids = np.load(CACHE / "id.npy")

# Assign a drifter ID to each observation
if rowsize.sum() != len(lon):
    raise ValueError("rowsize does not match the observation count.")

drifter_id = np.repeat(ids, rowsize)

# All observations in the study region and period
# SST and velocity availability are examined separately in Figure 2
selected = (
    (time >= "2001-01-01")
    & (time < "2023-01-01")
    & np.isfinite(lon)
    & np.isfinite(lat)
    & (lon >= LON_MIN)
    & (lon <= LON_MAX)
    & (lat >= LAT_MIN)
    & (lat <= LAT_MAX)
)

df = pd.DataFrame({
    "lon": lon[selected],
    "lat": lat[selected],
    "drifter_id": drifter_id[selected],
})

if df.empty:
    raise ValueError("No observations found in the study region.")

# Grid edges clipped to the study boundary
lon_edges = np.append(
    np.arange(LON_MIN, LON_MAX, GRID_SIZE), LON_MAX
)
lat_edges = np.append(
    np.arange(LAT_MIN, LAT_MAX, GRID_SIZE), LAT_MAX
)

nx = len(lon_edges) - 1
ny = len(lat_edges) - 1

df["ix"] = pd.cut(
    df["lon"], lon_edges, labels=False, include_lowest=True
)
df["iy"] = pd.cut(
    df["lat"], lat_edges, labels=False, include_lowest=True
)
df[["ix", "iy"]] = df[["ix", "iy"]].astype(int)

# Each drifter counted once in each cell it visits
counts = (
    df.groupby(["iy", "ix"])["drifter_id"]
    .nunique()
    .reset_index(name="count")
)

grid = np.zeros((ny, nx))
grid[
    counts["iy"].to_numpy(),
    counts["ix"].to_numpy(),
] = counts["count"].to_numpy()

# Mask cells with no observations
coverage = np.ma.masked_where(grid == 0, grid)

projection = ccrs.PlateCarree()
cmap = plt.get_cmap("viridis").copy()
cmap.set_bad("lightgrey")

fig, ax = plt.subplots(
    figsize=(8, 10),
    subplot_kw={"projection": projection},
)
fig.subplots_adjust(bottom=0.12, top=0.90)

# Slightly wider extent to show the study boundary
ax.set_extent(
    [LON_MIN - 1, LON_MAX + 1, LAT_MIN - 1, LAT_MAX + 1],
    crs=projection,
)
ax.set_facecolor("lightgrey")

mesh = ax.pcolormesh(
    lon_edges,
    lat_edges,
    coverage,
    cmap=cmap,
    norm=LogNorm(vmin=1, vmax=max(2, grid.max())),
    shading="flat",
    transform=projection,
    zorder=1,
)

ax.add_feature(
    cfeature.LAND.with_scale("50m"),
    facecolor="beige",
    edgecolor="none",
    zorder=2,
)
ax.coastlines(resolution="50m", linewidth=0.8, zorder=3)
ax.add_feature(
    cfeature.BORDERS.with_scale("50m"),
    linewidth=0.4,
    zorder=3,
)

# Study-region boundary
ax.plot(
    [LON_MIN, LON_MAX, LON_MAX, LON_MIN, LON_MIN],
    [LAT_MIN, LAT_MIN, LAT_MAX, LAT_MAX, LAT_MIN],
    color="black",
    linestyle="--",
    linewidth=1.2,
    transform=projection,
    zorder=4,
)

gl = ax.gridlines(draw_labels=True, alpha=0.3)
gl.top_labels = False
gl.right_labels = False

cbar = fig.colorbar(mesh, ax=ax, pad=0.03, shrink=0.8)
cbar.set_label("Unique drifters per cell (logarithmic scale)")

ax.set_title(
    "Humboldt study-region drifter coverage\n2001–2022",
    pad=15,
)

fig.text(
    0.5, 0.035,
    f"{len(df):,} observations • "
    f"{df['drifter_id'].nunique():,} unique drifters\n"
    "2° cells (last latitude cell: 1°) • "
    "Grey ocean = no observations",
    ha="center",
    fontsize=9,
)

fig.savefig("humboldt_drifter_coverage.png", dpi=300)
plt.show()