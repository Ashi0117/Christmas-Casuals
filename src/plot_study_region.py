"""Map of South America with the Humboldt Current study region boxed.

Run from the project root:
    python src/plot_study_region.py
Saves figures/study_region_map.png (slide-ready, 16:9).
"""
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # project root
DATA = ROOT / "data"

# Study region (Humboldt Current)
lon_min, lon_max = -89, -65
lat_min, lat_max = -49, -4

BLUE = "#2a78d6"
TEXT1, TEXT2 = "#0b0b0b", "#52514e"
SURF = "#fcfcfb"
OCEAN, LAND = "#e8eff8", "#ecebe6"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13})
fig = plt.figure(figsize=(16, 9), facecolor=SURF)
ax = fig.add_axes([0.30, 0.06, 0.45, 0.82], projection=ccrs.PlateCarree())
ax.set_extent([-100, -30, -58, 15], crs=ccrs.PlateCarree())

ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor=OCEAN)
ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor=LAND)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6, edgecolor="#8a8984")
ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4, edgecolor="#b5b4ad")

# Study box: light fill + solid outline
ax.add_patch(mpatches.Rectangle(
    (lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
    transform=ccrs.PlateCarree(), facecolor=BLUE, alpha=0.12, edgecolor="none"))
ax.add_patch(mpatches.Rectangle(
    (lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
    transform=ccrs.PlateCarree(), facecolor="none", edgecolor=BLUE, linewidth=2.5))

ax.text(lon_min + 1, lat_min + 1.2, "Study region",
        transform=ccrs.PlateCarree(), color=BLUE, fontsize=14, fontweight="bold")
ax.text(lon_min + 1, lat_min - 2.6,
        f"{abs(lon_min)}–{abs(lon_max)}°W, {abs(lat_max)}–{abs(lat_min)}°S",
        transform=ccrs.PlateCarree(), color=TEXT2, fontsize=12)

# Light reference labels
for name, lon, lat in [("PERU", -75.5, -10), ("CHILE", -71.5, -30),
                       ("Pacific\nOcean", -95, -25)]:
    ax.text(lon, lat, name, transform=ccrs.PlateCarree(), color=TEXT2,
            fontsize=11, ha="center", va="center", style="italic")

gl = ax.gridlines(draw_labels=True, linewidth=0.5, color="#d4d3cd", linestyle="-")
gl.top_labels = gl.right_labels = False
gl.xlabel_style = gl.ylabel_style = {"color": TEXT2, "size": 11}
for s in ax.spines.values():
    s.set_edgecolor("#c3c2b7")

fig.text(0.06, 0.93, "Study region: the Humboldt Current",
         fontsize=22, fontweight="bold", color=TEXT1)
fig.text(0.06, 0.885,
         "Drifter SST observations were limited to the box off the west coast of South America",
         fontsize=14, color=TEXT2)
fig.text(0.06, 0.02, "Basemap: Natural Earth (1:50m), via Cartopy.", fontsize=11, color=TEXT2)

fig.savefig(ROOT / "figures" / "study_region_map.png", dpi=200, facecolor=SURF)
print("Saved study_region_map.png")
