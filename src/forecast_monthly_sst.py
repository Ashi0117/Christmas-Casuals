import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # project root
DATA = ROOT / "data"

sst = pd.read_csv(DATA / "processed" / "sst_forecast_data.csv")
icen = pd.read_csv(DATA / "processed" / "icen_monthly.csv").rename(
    columns={"Year": "year", "Month": "month"}
)

data = sst.merge(
    icen[["year", "month", "ENSO", "Episode"]],
    on=["year", "month"],
    how="left",
    validate="one_to_one",
)

data["date"] = pd.to_datetime(data[["year", "month"]].assign(day=1))
data = data.set_index("date").sort_index().asfreq("MS")

# Keep gaps so the forecast always uses the previous calendar month.
data["actual"] = data["sst_anom"].where(data["low_coverage"].eq(False))
data["persistence"] = data["actual"].shift(1)

# Use the target month's ICEN label to group the errors after forecasting.
data["phase"] = data["Episode"].where(
    data["Episode"].isin(["El Niño", "La Niña"])
)
data.loc[data["ENSO"].eq("Neutral"), "phase"] = "Neutral"

test = data.loc["2018-01":"2022-12"].dropna(
    subset=["actual", "persistence"]
).copy()
test["absolute_error"] = (test["actual"] - test["persistence"]).abs()

print(f"Test months: {len(test)}")
print(f"Overall persistence MAE: {test['absolute_error'].mean():.3f} °C")

summary = (
    test.groupby("phase")["absolute_error"]
    .agg(Months="size", MAE="mean")
    .reindex(["El Niño", "La Niña", "Neutral"])
)
print("\nPersistence by phase (MAE in °C)")
print(summary.round(3).to_string())


# For a forecast of March, lag 1 is February and lag 2 is January.
data["sst_lag1"] = data["persistence"]
data["sst_lag2"] = data["actual"].shift(2)

# Encode the target month so December and January are close together.
angle = 2 * np.pi * (data.index.month - 1) / 12
data["month_sin"] = np.sin(angle)
data["month_cos"] = np.cos(angle)

features = ["sst_lag1", "sst_lag2", "month_sin", "month_cos"]
required = ["actual", *features]

train = data.loc[:"2017-12"].dropna(subset=required)
test_common = data.loc["2018-01":"2022-12"].dropna(subset=required).copy()

model = LinearRegression()
model.fit(train[features], train["actual"])
test_common["regression"] = model.predict(test_common[features])

print(f"\nTraining months: {len(train)}")
print(f"Shared test months: {len(test_common)}")
for name in ["persistence", "regression"]:
    mae = (test_common["actual"] - test_common[name]).abs().mean()
    print(f"{name.title()} MAE: {mae:.3f} °C")


data = data.join(icen.set_index(["year", "month"])["ICEN"], on=["year", "month"])

# ICEN is a centred 3-month index. Allow an extra month for publication.
# For a March forecast, this uses the ICEN value labelled December.
data["icen_lag3"] = data["ICEN"].shift(3)

features_with_icen = [*features, "icen_lag3"]
required = ["actual", *features_with_icen]

train_apped = data.loc[:"2017-12"].dropna(subset=required)
test_apped = data.loc["2018-01":"2022-12"].dropna(subset=required).copy()

print(f"\nTest months shared by all models: {len(test_apped)}")
mae = (test_apped["actual"] - test_apped["persistence"]).abs().mean()
print(f"Persistence MAE: {mae:.3f} °C")

for label, inputs in [
    ("Regression without ICEN", features),
    ("Regression with ICEN", features_with_icen),
]:
    model = LinearRegression().fit(train_apped[inputs], train_apped["actual"])
    prediction = model.predict(test_apped[inputs])
    mae = (test_apped["actual"] - prediction).abs().mean()
    print(f"{label} MAE: {mae:.3f} °C")

from xgboost import XGBRegressor

xgb = XGBRegressor(
    n_estimators=100,
    max_depth=2,
    learning_rate=0.05,
    objective="reg:squarederror",
    random_state=42,
)

xgb.fit(train_apped[features_with_icen], train_apped["actual"])
test_apped["xgboost"] = xgb.predict(test_apped[features_with_icen])

mae = (test_apped["actual"] - test_apped["xgboost"]).abs().mean()
print(f"XGBoost with ICEN MAE: {mae:.3f} °C")

test_apped["regression_with_icen"] = model.predict(
    test_apped[features_with_icen]
)

predictions = test_apped[
    ["persistence", "regression_with_icen", "xgboost"]
].rename(columns={"regression_with_icen": "regression"})

errors = predictions.sub(test_apped["actual"], axis=0)

overall = pd.DataFrame({
    "MAE (°C)": errors.abs().mean(),
    "RMSE (°C)": errors.pow(2).mean().pow(0.5),
})

print(f"\nOverall one-month forecast errors ({len(errors)} test months)")
print(overall.round(3).to_string())

for phase in ["El Niño", "La Niña", "Neutral"]:
    phase_errors = errors.loc[test_apped["phase"].eq(phase)]

    summary = pd.DataFrame({
        "MAE (°C)": phase_errors.abs().mean(),
        "RMSE (°C)": phase_errors.pow(2).mean().pow(0.5),
    })

    print(f"\n{phase} ({len(phase_errors)} test months)")
    print(summary.round(3).to_string())

