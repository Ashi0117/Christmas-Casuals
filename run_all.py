"""Run the whole project: notebooks 0 to 6 in order, top to bottom.

    uv sync
    uv run python run_all.py            # all notebooks
    uv run python run_all.py 3 5        # only notebooks 3 to 5
    uv run python run_all.py 4          # only notebook 4

Each notebook is executed in place, so its saved outputs and the files in
data/processed/ and figures/ are refreshed. The first run downloads the
Clouddrift gdp1h drifter arrays (about 8 GB) into data/cache/; later runs reuse them.
"""
import json
import os
import subprocess
import tempfile
import sys
import time
from pathlib import Path

NOTEBOOKS = Path(__file__).resolve().parent / "notebooks"
ORDER = sorted(NOTEBOOKS.glob("[0-9]_*.ipynb"))   # 0_setup ... 6_forecast_duration_and_peak


def main():
    args = [int(a) for a in sys.argv[1:3]]
    first = args[0] if args else 0
    last = args[1] if len(args) > 1 else (first if args else 9)

    # Run the notebooks on this same Python. A temporary "python3" kernel that names
    # sys.executable goes first on JUPYTER_PATH, so Jupyter can't pick another Python
    # (for example base Anaconda) from PATH or from a user-level kernel.
    kernels = Path(tempfile.mkdtemp()) / "kernels" / "python3"
    kernels.mkdir(parents=True)
    (kernels / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Python 3 (project)", "language": "python"}))
    env = dict(os.environ, JUPYTER_PATH=os.pathsep.join(
        [str(kernels.parents[1]), *filter(None, [os.environ.get("JUPYTER_PATH")])]))

    for nb in ORDER:
        if not first <= int(nb.name[0]) <= last:
            continue
        print(f"Running {nb.name} ...", flush=True)
        start = time.time()
        subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
             "--ExecutePreprocessor.timeout=-1", "--ExecutePreprocessor.kernel_name=python3", nb.name],
            cwd=NOTEBOOKS, env=env, check=True,
        )
        print(f"  done in {time.time() - start:.0f} s", flush=True)
    print("All notebooks ran successfully.")


if __name__ == "__main__":
    main()
