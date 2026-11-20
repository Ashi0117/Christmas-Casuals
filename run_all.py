"""Run the whole project: notebooks 1 to 6 in order, top to bottom.

    uv sync
    uv run python run_all.py            # all notebooks
    uv run python run_all.py 3 5        # only notebooks 3 to 5

Each notebook is executed in place, so its saved outputs and the files in
data/processed/ and figures/ are refreshed. The first run downloads the
Clouddrift gdp1h drifter arrays (about 8 GB) into data/cache/; later runs reuse them.
"""
import subprocess
import sys
import time
from pathlib import Path

NOTEBOOKS = Path(__file__).resolve().parent / "notebooks"
ORDER = [
    "1_enso_episodes.ipynb",
    "2_data_cleaning.ipynb",
    "3_sst_anomalies.ipynb",
    "4_exploratory_analysis.ipynb",
    "5_forecast_next_month_sst.ipynb",
    "6_forecast_duration_and_peak.ipynb",
]


def main():
    args = [int(a) for a in sys.argv[1:3]]
    first = args[0] if args else 1
    last = args[1] if len(args) > 1 else (first if args else len(ORDER))
    for name in ORDER[first - 1:last]:
        print(f"Running {name} ...", flush=True)
        start = time.time()
        subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
             "--ExecutePreprocessor.timeout=-1", "--ExecutePreprocessor.kernel_name=python3", name],
            cwd=NOTEBOOKS, check=True,
        )
        print(f"  done in {time.time() - start:.0f} s", flush=True)
    print("All notebooks ran successfully.")


if __name__ == "__main__":
    main()
