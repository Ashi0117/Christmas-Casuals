"""Relabel the coastal El Niño / La Niña columns in icen_monthly.csv.

Rule: coastal El Niño when ICEN >= +0.4 °C, coastal La Niña when ICEN <= -0.4 °C,
for at least 3 consecutive months. The original file used > +0.5 °C and < -0.7 °C.

Rewrites the ENSO, Episode and Episode_ID columns of icen_monthly.csv. The first run
keeps the original file as icen_monthly_original.csv, and every run relabels from that
original, so running it again gives the same result.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ENSO_WARM = 0.4     # coastal El Niño: ICEN at or above this (°C)
ENSO_COLD = -0.4    # coastal La Niña: ICEN at or below this (°C)
MIN_MONTHS = 3      # consecutive months needed for an episode

DATA = Path(__file__).resolve().parents[1] / "data"
LABELLED = DATA / "processed" / "icen_monthly.csv"
ORIGINAL = DATA / "raw" / "icen_monthly_original.csv"


def qualifying_runs(active):
    """True for months inside a run of at least MIN_MONTHS consecutive True values."""
    run_id = (active != active.shift()).cumsum()
    return active & active.groupby(run_id).transform("size").ge(MIN_MONTHS)


def relabel(icen):
    warm = qualifying_runs(icen["ICEN"] >= ENSO_WARM)
    cold = qualifying_runs(icen["ICEN"] <= ENSO_COLD)
    phase = pd.Series(np.select([warm, cold], ["El Niño", "La Niña"], ""), index=icen.index)
    in_episode = phase.ne("")
    new_episode = in_episode & phase.ne(phase.shift())
    out = icen.copy()
    out["ENSO"] = phase.where(in_episode, "Neutral")
    out["Episode"] = phase.where(in_episode, "No")
    out["Episode_ID"] = new_episode.cumsum().where(in_episode).astype("Int64")   # 1, 2, ... (blank outside episodes)
    return out


def main():
    if not ORIGINAL.exists():
        LABELLED.rename(ORIGINAL)
    icen = relabel(pd.read_csv(ORIGINAL))
    icen.to_csv(LABELLED, index=False, lineterminator="\r\n")   # same format as the original file

    episodes = (icen.dropna(subset=["Episode_ID"]).groupby("Episode_ID")
                .agg(phase=("Episode", "first"), start=("Date", "first"),
                     end=("Date", "last"), months=("ICEN", "size")))
    print(f"Relabelled {LABELLED} with ICEN >= {ENSO_WARM} / <= {ENSO_COLD} °C "
          f"for {MIN_MONTHS}+ months: {len(episodes)} episodes "
          f"({episodes['phase'].value_counts().to_dict()})")


if __name__ == "__main__":
    main()
