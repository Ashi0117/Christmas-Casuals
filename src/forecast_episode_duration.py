import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # project root
DATA = ROOT / "data"

ICEN_DELAY = 2
MIN_TRAIN_EPISODES = 3
MIN_ICEN_MONTHS = 24
ARIMA_ORDER = (1, 0, 1)
MAX_ARIMA_STEPS = 36

# Coastal El Niño / La Niña thresholds (°C); same rule as relabel_icen.py
ENSO_WARM = 0.4
ENSO_COLD = -0.4

STUDY_START = pd.Period("2001-01", freq="M")
STUDY_END = pd.Period("2022-12", freq="M")

FEATURES = ["ICEN at confirmation"]
TARGET = "Actual months left"

# ---- Added models -----------------------------------------------------------
# Hazard: a discrete-time hazard (survival) model. Every month of every past episode,
#   from its confirmation month to its last month, is one row; the label says whether
#   the episode ended in that month. Logistic regression gives the chance of ending in
#   month k after confirmation, from k, the episode's strength and trend at confirmation,
#   its phase and the calendar month. Chaining those chances gives the distribution of
#   the last month; the forecast is its median. All phases are pooled, so it learns from
#   ~100+ episode-months instead of a handful of same-phase episodes.
# ARIMA sim: the same ARIMA(1,0,1) fit, but instead of the single mean path it simulates
#   N_SIM_PATHS ICEN paths and takes the median month they leave the episode range. If the
#   median path never leaves within MAX_ARIMA_STEPS, the forecast is capped at the window end.
N_SIM_PATHS = 1000
MIN_HAZARD_EPISODES = 5
HAZARD_C = 1.0          # L2 regularisation strength (sklearn C); smaller = more shrinkage
HAZARD_FEATURES = ["months_since_confirmation", "strength", "trend", "is_el_nino",
                   "season_sin", "season_cos"]
METHODS = ["Median", "Regression", "ARIMA", "Hazard", "ARIMA sim"]


def load_icen():
    icen = pd.read_csv(DATA / "processed" / "icen_monthly.csv")
    dates = pd.to_datetime(
        icen[["Year", "Month"]]
        .rename(columns={"Year": "year", "Month": "month"})
        .assign(day=1)
    )
    icen["month"] = dates.dt.to_period("M")
    return icen.sort_values("month")


def build_episode_table(icen):
    episodes = []

    for episode_id, event in icen.dropna(subset=["Episode_ID"]).groupby("Episode_ID"):
        start = event["month"].iloc[0]
        end = event["month"].iloc[-1]

        if start < STUDY_START or end > STUDY_END:
            continue

        # The third qualifying ICEN value confirms the episode.
        confirmation = event.iloc[2]
        forecast_month = confirmation["month"] + ICEN_DELAY

        sign = 1 if confirmation["Episode"] == "El Niño" else -1
        episodes.append({
            "Episode_ID": int(episode_id),
            "Phase": confirmation["Episode"],
            "Confirmation": confirmation["month"],
            "Start": start,
            "End": end,
            "Forecast month": forecast_month,
            "End known month": end + 1 + ICEN_DELAY,
            "ICEN at confirmation": float(confirmation["ICEN"]),
            # Signed so that positive means a stronger / strengthening episode
            "Strength": sign * float(confirmation["ICEN"]),
            "Trend": sign * float(confirmation["ICEN"] - event["ICEN"].iloc[0]),
            TARGET: max(0, end.ordinal - forecast_month.ordinal),
        })

    return pd.DataFrame(episodes).sort_values("Forecast month").reset_index(drop=True)


def hazard_features(episode, months):
    """Feature rows for an episode at months_since_confirmation = 0, 1, ..., months - 1."""
    k = np.arange(months)
    calendar_month = np.array([(episode["Confirmation"] + int(j)).month for j in k])
    angle = 2 * np.pi * (calendar_month - 1) / 12
    return pd.DataFrame({
        "months_since_confirmation": k,
        "strength": episode["Strength"],
        "trend": episode["Trend"],
        "is_el_nino": float(episode["Phase"] == "El Niño"),
        "season_sin": np.sin(angle),
        "season_cos": np.cos(angle),
    })


def hazard_months_left(past, episode):
    """Median last month from a pooled discrete-time hazard model fitted on past episodes."""
    rows, ended = [], []
    for _, e in past.iterrows():
        lasted = e["End"].ordinal - e["Confirmation"].ordinal   # months after confirmation
        rows.append(hazard_features(e, lasted + 1))
        ended.append(np.r_[np.zeros(lasted), 1])
    model = make_pipeline(StandardScaler(), LogisticRegression(C=HAZARD_C))
    model.fit(pd.concat(rows)[HAZARD_FEATURES], np.concatenate(ended))

    horizon = MAX_ARIMA_STEPS + ICEN_DELAY + 1
    hazard = model.predict_proba(hazard_features(episode, horizon)[HAZARD_FEATURES])[:, 1]
    survival = np.cumprod(np.r_[1.0, 1 - hazard[:-1]])
    p_end = survival * hazard                    # chance the last month is k after confirmation
    reached = np.flatnonzero(np.cumsum(p_end) >= 0.5)
    k_median = reached[0] if reached.size else horizon - 1
    last_month = episode["Confirmation"] + int(k_median)
    return max(0, last_month.ordinal - episode["Forecast month"].ordinal)


def simulated_months_left(fitted, last_month, phase, forecast_month, seed):
    """Median month that simulated ICEN paths leave the episode range."""
    sims = np.asarray(fitted.simulate(MAX_ARIMA_STEPS, anchor="end", repetitions=N_SIM_PATHS,
                                      rng=np.random.default_rng(seed))).reshape(MAX_ARIMA_STEPS, -1)
    future = pd.period_range(last_month + 1, periods=MAX_ARIMA_STEPS, freq="M")
    outside = sims < ENSO_WARM if phase == "El Niño" else sims > ENSO_COLD
    first_exit = np.where(outside.any(axis=0), outside.argmax(axis=0), np.inf)
    median_exit = np.quantile(first_exit, 0.5, method="lower")
    if np.isinf(median_exit):
        return max(0, future[-1].ordinal - forecast_month.ordinal), "Scored (capped at window end)"
    return max(0, (future[int(median_exit)] - 1).ordinal - forecast_month.ordinal), "Scored"


def make_forecasts(results, icen):
    series = icen.set_index("month")["ICEN"]
    calendar = pd.period_range(series.index.min(), series.index.max(), freq="M")
    series = series.reindex(calendar)

    results["Past episodes used"] = 0
    results["Median months left"] = float("nan")
    results["Regression months left"] = float("nan")
    results["ARIMA months left"] = float("nan")
    results["ARIMA status"] = "Insufficient ICEN history"
    results["Hazard months left"] = float("nan")
    results["ARIMA sim months left"] = float("nan")
    results["ARIMA sim status"] = "Insufficient ICEN history"

    for i, episode in results.iterrows():
        forecast_month = episode["Forecast month"]
        phase = episode["Phase"]

        # The benchmarks learn from same-phase episodes with known end dates.
        past = results.loc[
            results["Phase"].eq(phase)
            & results["End known month"].le(forecast_month)
        ]
        results.loc[i, "Past episodes used"] = len(past)

        if not past.empty:
            results.loc[i, "Median months left"] = past[TARGET].median()

        if len(past) >= MIN_TRAIN_EPISODES:
            model = LinearRegression().fit(past[FEATURES], past[TARGET])
            prediction = model.predict(results.loc[[i], FEATURES])[0]
            results.loc[i, "Regression months left"] = max(0.0, prediction)

        # Hazard model: pooled over both phases, so it uses every known past episode
        known = results.loc[results["End known month"].le(forecast_month)]
        if len(known) >= MIN_HAZARD_EPISODES:
            results.loc[i, "Hazard months left"] = hazard_months_left(known, episode)

        # At the issue date, only ICEN through the confirmation month is available.
        last_available_month = forecast_month - ICEN_DELAY
        history = series.loc[:last_available_month]

        if history.count() < MIN_ICEN_MONTHS:
            continue

        fitted = ARIMA(history, order=ARIMA_ORDER).fit()
        if not fitted.mle_retvals.get("converged", True):
            results.loc[i, "ARIMA status"] = "Fit did not converge"
            continue

        sim_left, sim_status = simulated_months_left(
            fitted, last_available_month, phase, forecast_month, seed=int(episode["Episode_ID"])
        )
        results.loc[i, "ARIMA sim months left"] = sim_left
        results.loc[i, "ARIMA sim status"] = sim_status

        path = fitted.forecast(steps=MAX_ARIMA_STEPS)
        # The episode ends once the forecast leaves the episode range
        outside_phase = path.lt(ENSO_WARM) if phase == "El Niño" else path.gt(ENSO_COLD)
        exit_months = path.index[outside_phase]

        if exit_months.empty:
            results.loc[i, "ARIMA status"] = "No exit within forecast window"
            continue

        # Count only episode months after the forecast month.
        last_episode_month = exit_months[0] - 1
        results.loc[i, "ARIMA months left"] = max(
            0, last_episode_month.ordinal - forecast_month.ordinal
        )
        results.loc[i, "ARIMA status"] = "Scored"

    for method in METHODS:
        results[f"{method} error"] = (
            results[f"{method} months left"] - results[TARGET]
        ).abs()

    return results


def main():
    icen = load_icen()
    results = make_forecasts(build_episode_table(icen), icen)

    print("\nDuration forecasts by episode")
    print(
        results.drop(columns="End known month").to_string(
            index=False, float_format="{:.2f}".format, na_rep="—"
        )
    )

    print("\nARIMA forecast status")
    print(pd.DataFrame({m: results[f"{m} status"].value_counts() for m in ["ARIMA", "ARIMA sim"]})
          .fillna(0).astype(int).to_string())

    # Score every method on exactly the same episodes.
    shared = results.dropna(subset=[f"{m} error" for m in METHODS])

    print("\nDuration MAE and RMSE in months on the same episodes")
    if shared.empty:
        print("No episodes had forecasts from every method.")
        return

    groups = {"El Niño": shared[shared["Phase"].eq("El Niño")],
              "La Niña": shared[shared["Phase"].eq("La Niña")], "All": shared}
    summary = pd.DataFrame({
        name: {"Episodes": len(g),
               **{f"{m}_{k}": (g[f"{m} error"].mean() if k == "MAE"
                               else g[f"{m} error"].pow(2).mean() ** 0.5)
                  for m in METHODS for k in ["MAE", "RMSE"]}}
        for name, g in groups.items()}).T
    print(summary.to_string(float_format="{:.2f}".format))


if __name__ == "__main__":
    main()