import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer

from forecast_episode_duration import (
    ICEN_DELAY,
    build_episode_table,
    load_icen,
    make_forecasts,
)

FIRST_FORECAST = pd.Period("2011-01", freq="M")
MIDDLE_PERIOD_START = pd.Period("2014-01", freq="M")
LATER_PERIOD_START = pd.Period("2018-01", freq="M")

MIN_TRAIN_ROWS = 36
LINEAR_FEATURES = ["latest_sst", "previous_sst", "month_sin", "month_cos"]
FEATURES = [*LINEAR_FEATURES, "available_icen"]


def load_sst(filename):
    data = pd.read_csv(filename)
    dates = pd.to_datetime(data[["year", "month"]].assign(day=1))
    data.index = pd.PeriodIndex(dates, freq="M")

    sst = data["sst_anom"].where(data["low_coverage"].eq(False)).sort_index()
    calendar = pd.period_range(sst.index.min(), sst.index.max(), freq="M")
    return sst.reindex(calendar)


def make_gam():
    terms = ColumnTransformer([
        ("linear", "passthrough", LINEAR_FEATURES),
        (
            "icen_curve",
            SplineTransformer(
                n_knots=3,
                degree=2,
                include_bias=False,
                extrapolation="constant",
            ),
            ["available_icen"],
        ),
    ])
    return make_pipeline(terms, LinearRegression())


def forecast_sst_path(sst, icen, issue_month, months_left):
    """Fit a separate GAM for each lead time from the same issue month."""
    data = pd.DataFrame({"actual": sst, "ICEN": icen.reindex(sst.index)})
    angle = 2 * np.pi * (data.index.month - 1) / 12
    data["month_sin"] = np.sin(angle)
    data["month_cos"] = np.cos(angle)

    predictions = []

    for lead in range(1, months_left + 1):
        target_month = issue_month + lead
        if target_month not in data.index:
            return None, "Forecast extends beyond SST calendar"

        pairs = data.assign(
            latest_sst=data["actual"].shift(lead),
            previous_sst=data["actual"].shift(lead + 1),
            available_icen=data["ICEN"].shift(lead + ICEN_DELAY),
        )

        # Train only on SST outcomes available by the forecast month.
        train = pairs.loc[:issue_month].dropna(subset=["actual", *FEATURES])
        inputs = pairs.loc[[target_month], FEATURES]

        if len(train) < MIN_TRAIN_ROWS:
            return None, f"Too few training months at lead {lead}"
        if inputs.isna().any().any():
            return None, "Missing SST or ICEN at forecast date"

        gam = make_gam().fit(train[FEATURES], train["actual"])
        predictions.append(gam.predict(inputs)[0])

    return np.asarray(predictions), "Forecast issued"


def observed_extreme(sst, issue_month, end_month, extreme):
    """Calculate the observed extreme over the remaining episode months."""
    if end_month <= issue_month:
        return np.nan

    months = pd.period_range(issue_month + 1, end_month, freq="M")
    observed = sst.reindex(months)

    if observed.isna().any():
        return np.nan

    return extreme(observed.to_numpy())


def historical_median(episodes, sst, phase, issue_month, extreme):
    # Only use earlier same-phase episodes whose end was already known.
    past = episodes.loc[
        episodes["Phase"].eq(phase)
        & episodes["End known month"].le(issue_month)
        & episodes["Actual months left"].gt(0)
    ]

    extremes = [
        observed_extreme(sst, event["Forecast month"], event["End"], extreme)
        for _, event in past.iterrows()
    ]
    usable = pd.Series(extremes, dtype=float).dropna()
    return usable.median(), len(usable)


def print_scores(results, forecast_columns, title):
    common = results.dropna(
        subset=["Actual extreme", *forecast_columns.values()]
    )

    print(f"\n{title} (°C)")
    if common.empty:
        print("No episodes had a usable observed extreme and all forecasts.")
        return

    scores = []

    for phase, cases in common.groupby("Phase"):
        for model, column in forecast_columns.items():
            errors = cases[column] - cases["Actual extreme"]
            scores.append({
                "Phase": phase,
                "Model": model,
                "Episodes": len(cases),
                "MAE": errors.abs().mean(),
                "RMSE": np.sqrt(errors.pow(2).mean()),
            })

    print(pd.DataFrame(scores).to_string(
        index=False, float_format="{:.3f}".format
    ))


def main():
    icen = load_icen()
    episodes = make_forecasts(build_episode_table(icen), icen)
    icen_series = icen.set_index("month")["ICEN"]

    sst_2011_2013 = load_sst("sst_forecast_data_2011_2013.csv")
    sst_2014_2017 = load_sst("sst_forecast_data_2014_2017.csv")
    sst_2018_2022 = load_sst("sst_forecast_data.csv")

    rows = []

    for _, episode in episodes.iterrows():
        issue = episode["Forecast month"]
        if issue < FIRST_FORECAST:
            continue

        # Choose an SST reference fitted before the forecast period began.
        if issue < MIDDLE_PERIOD_START:
            sst = sst_2011_2013
        elif issue < LATER_PERIOD_START:
            sst = sst_2014_2017
        else:
            sst = sst_2018_2022

        phase = episode["Phase"]
        extreme = np.max if phase == "El Niño" else np.min
        predicted_left = episode["ARIMA months left"]

        median, history_count = historical_median(
            episodes, sst, phase, issue, extreme
        )

        row = {
            "Episode_ID": episode["Episode_ID"],
            "Phase": phase,
            "Forecast month": issue,
            "Actual months left": int(episode["Actual months left"]),
            "ARIMA months left": predicted_left,
            "Actual extreme": np.nan,
            "GAM extreme": np.nan,
            "Persistence extreme": sst.get(issue, np.nan),
            "Historical median extreme": median,
            "Historical episodes used": history_count,
            "Status": "No ARIMA duration forecast",
        }

        if pd.notna(predicted_left):
            if predicted_left == 0:
                row["Status"] = "Predicted episode already over"
            else:
                path, status = forecast_sst_path(
                    sst, icen_series, issue, int(predicted_left)
                )
                row["Status"] = status
                if path is not None:
                    row["GAM extreme"] = extreme(path)

        # Use the actual end date only to calculate the observed outcome.
        row["Actual extreme"] = observed_extreme(
            sst, issue, episode["End"], extreme
        )
        rows.append(row)

    results = pd.DataFrame(rows)
    if results.empty:
        print("No episodes in the SST forecast period.")
        return

    print("\nRemaining SST extremes by episode (°C)")
    print(results.to_string(
        index=False, float_format="{:.3f}".format, na_rep="—"
    ))

    continued = results["Actual months left"].gt(0)
    gam_issued = results["GAM extreme"].notna()
    predicted_zero = results["ARIMA months left"].eq(0)

    print("\nForecast coverage")
    print(f"Episodes that actually continued: {continued.sum()}")
    print(
        "Predicted zero months left but continued: "
        f"{(predicted_zero & continued).sum()}"
    )
    print(
        "Any missing GAM forecast despite continuation: "
        f"{(~gam_issued & continued).sum()}"
    )
    print(
        "GAM forecast issued but no months actually remained: "
        f"{(gam_issued & ~continued).sum()}"
    )
    print(
        "Continuing episodes with incomplete observed SST: "
        f"{(continued & results['Actual extreme'].isna()).sum()}"
    )

    original_models = {
        "ARIMA + GAM": "GAM extreme",
        "Persistence": "Persistence extreme",
    }
    print_scores(results, original_models, "ARIMA + GAM vs. persistence")

    print_scores(
        results,
        {**original_models, "Historical median": "Historical median extreme"},
        "Three-way comparison on shared episodes",
    )


if __name__ == "__main__":
    main()