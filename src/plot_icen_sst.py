import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # project root
DATA = ROOT / "data"

# sst_monthly_anomalies.csv is written by sst_monthly_anomalies.py
if not (DATA / "processed" / "sst_monthly_anomalies.csv").exists():
    subprocess.run([sys.executable, str(Path(__file__).with_name("sst_monthly_anomalies.py"))], check=True)

# Coastal El Niño / La Niña thresholds (°C); same rule as relabel_icen.py
ENSO_WARM = 0.4
ENSO_COLD = -0.4

sst = pd.read_csv(DATA / "processed" / "sst_monthly_anomalies.csv")
icen = pd.read_csv(DATA / "processed" / "icen_monthly.csv").rename(
    columns={"Year": "year", "Month": "month", "ICEN": "icen"}
)

# Match by calendar month. Keep every month so SST gaps stay visible.
plot_data = sst.merge(
    icen[["year", "month", "icen", "Episode", "Episode_ID"]],
    on=["year", "month"],
    how="left",
    validate="one_to_one",
).sort_values(["year", "month"])

plot_data["month_start"] = pd.to_datetime(
    plot_data[["year", "month"]].assign(day=1)
)
plot_data["plot_date"] = plot_data["month_start"] + pd.Timedelta(days=14)

# Hide low-coverage SST months without removing their ICEN values.
sst_anom = plot_data["sst_anom"].where(~plot_data["low_coverage"])

# Restart the smoothing after a gap.
segments = sst_anom.isna().cumsum()
sst_ema = sst_anom.groupby(segments).transform(
    lambda values: values.ewm(span=3, adjust=False).mean()
).where(sst_anom.notna())

fig, (ax_sst, ax_icen) = plt.subplots(
    2, 1, figsize=(14, 7), sharex=True, layout="constrained"
)
fig.suptitle("Humboldt SST anomalies and coastal ENSO, 2001–2022")

episode_colors = {"El Niño": "#f28b82", "La Niña": "#89a9e8"}

for _, episode in plot_data.dropna(subset=["Episode_ID"]).groupby("Episode_ID"):
    start = episode["month_start"].min()
    end = episode["month_start"].max() + pd.offsets.MonthBegin(1)
    color = episode_colors[episode["Episode"].iloc[0]]

    for ax in (ax_sst, ax_icen):
        ax.axvspan(start, end, color=color, alpha=0.25, linewidth=0)

ax_sst.plot(
    plot_data["plot_date"], sst_anom,
    color="0.60", linewidth=0.9, label="Monthly drifter SST anomaly"
)
ax_sst.plot(
    plot_data["plot_date"], sst_ema,
    color="#1f77b4", linewidth=1.8, label="EMA with 3-month span"
)
ax_sst.set_title("Humboldt SST anomalies adjusted for location and season", loc="left")
ax_sst.set_ylabel("SST anomaly (°C)")
ax_sst.legend(loc="upper right")

icen_line, = ax_icen.plot(
    plot_data["plot_date"], plot_data["icen"],
    color="black", linewidth=1.4, label="ICEN"
)
ax_icen.axhline(ENSO_WARM, color="#c0392b", linestyle="--", linewidth=0.9)
ax_icen.axhline(ENSO_COLD, color="#3155a6", linestyle="--", linewidth=0.9)
ax_icen.set_title("ICEN and coastal event thresholds", loc="left")
ax_icen.set_ylabel("ICEN (°C)")
ax_icen.set_xlabel("Year")
ax_icen.legend(
    handles=[
        icen_line,
        Patch(facecolor=episode_colors["El Niño"], alpha=0.25, label="Coastal El Niño"),
        Patch(facecolor=episode_colors["La Niña"], alpha=0.25, label="Coastal La Niña"),
    ],
    loc="upper right",
)

for ax in (ax_sst, ax_icen):
    ax.axhline(0, color="0.35", linewidth=0.8)
    ax.grid(alpha=0.2)

ax_icen.set_xlim(pd.Timestamp("2001-01-01"), pd.Timestamp("2023-01-01"))
fig.savefig(ROOT / "figures" / "humboldt_sst_icen.png", dpi=300)

usable = plot_data.loc[
    ~plot_data["low_coverage"] & plot_data["sst_anom"].notna()
]

neutral = usable.loc[usable["icen"].gt(ENSO_COLD) & usable["icen"].lt(ENSO_WARM), "sst_anom"]
el_nino = usable.loc[usable["Episode"].eq("El Niño"), "sst_anom"]
la_nina = usable.loc[usable["Episode"].eq("La Niña"), "sst_anom"]

summary = pd.DataFrame({
    "Group": ["Neutral", "El Niño", "La Niña"],
    "Months": [len(neutral), len(el_nino), len(la_nina)],
    "Mean SST anomaly (°C)": [neutral.mean(), el_nino.mean(), la_nina.mean()],
})

summary["Difference from neutral (°C)"] = (
    summary["Mean SST anomaly (°C)"] - neutral.mean()
)

print(summary.round(3).to_string(index=False))


plt.show()