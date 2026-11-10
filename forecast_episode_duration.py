import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA

ICEN_DELAY = 2
MIN_TRAIN_EPISODES = 3
MIN_ICEN_MONTHS = 24
ARIMA_ORDER = (1, 0, 1)
MAX_ARIMA_STEPS = 36

STUDY_START = pd.Period("2001-01", freq="M")
STUDY_END = pd.Period("2022-12", freq="M")

FEATURES = ["ICEN at confirmation"]
TARGET = "Actual months left"


def load_icen():
    icen = pd.read_csv("icen_monthly.csv")
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

        episodes.append({
            "Episode_ID": int(episode_id),
            "Phase": confirmation["Episode"],
            "Start": start,
            "End": end,
            "Forecast month": forecast_month,
            "End known month": end + 1 + ICEN_DELAY,
            "ICEN at confirmation": float(confirmation["ICEN"]),
            TARGET: max(0, end.ordinal - forecast_month.ordinal),
        })

    return pd.DataFrame(episodes).sort_values("Forecast month").reset_index(drop=True)


def make_forecasts(results, icen):
    series = icen.set_index("month")["ICEN"]
    calendar = pd.period_range(series.index.min(), series.index.max(), freq="M")
    series = series.reindex(calendar)

    results["Past episodes used"] = 0
    results["Median months left"] = float("nan")
    results["Regression months left"] = float("nan")
    results["ARIMA months left"] = float("nan")
    results["ARIMA status"] = "Insufficient ICEN history"

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

        # At the issue date, only ICEN through the confirmation month is available.
        last_available_month = forecast_month - ICEN_DELAY
        history = series.loc[:last_available_month]

        if history.count() < MIN_ICEN_MONTHS:
            continue

        fitted = ARIMA(history, order=ARIMA_ORDER).fit()
        if not fitted.mle_retvals.get("converged", True):
            results.loc[i, "ARIMA status"] = "Fit did not converge"
            continue

        path = fitted.forecast(steps=MAX_ARIMA_STEPS)
        outside_phase = path.le(0.5) if phase == "El Niño" else path.ge(-0.7)
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

    for method in ["Median", "Regression", "ARIMA"]:
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
    print(results["ARIMA status"].value_counts().to_string())

    # Score all three methods on exactly the same episodes.
    shared = results.dropna(
        subset=["Median error", "Regression error", "ARIMA error"]
    )

    print("\nDuration MAE in months on the same episodes")
    if shared.empty:
        print("No episodes had forecasts from all three methods.")
        return

    summary = shared.groupby("Phase").agg(
    Episodes=("Episode_ID", "size"),
    Median_MAE=("Median error", "mean"),
    Median_RMSE=("Median error", lambda e: e.pow(2).mean() ** 0.5),
    Regression_MAE=("Regression error", "mean"),
    Regression_RMSE=("Regression error", lambda e: e.pow(2).mean() ** 0.5),
    ARIMA_MAE=("ARIMA error", "mean"),
    ARIMA_RMSE=("ARIMA error", lambda e: e.pow(2).mean() ** 0.5),
)
    print(summary.to_string(float_format="{:.2f}".format))


if __name__ == "__main__":
    main()