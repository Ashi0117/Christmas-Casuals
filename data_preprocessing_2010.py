import numpy as np
import pandas as pd
from scipy.interpolate import BSpline

from data_cleaning import df

TRAIN_END_YEAR = 2010
OUTPUT_FILE = "sst_forecast_data_2011_2013.csv"

LAT_SPLINE = (-54, -4, 16)
LON_SPLINE = (-94, -65, 10)
CHUNK_SIZE = 20_000

# Apply the same SST and geographic filters as the other forecast files.
in_sst_range = df["sst_degC"].between(5.0, 35.0)
outside_study_area = (df["lat"] < -40) & (df["lon"] > -71)
readings = df.loc[in_sst_range & ~outside_study_area].copy()


def spline_basis(values, lower, upper, n_basis):
    degree = 3
    inner = np.linspace(lower, upper, n_basis - degree + 1)
    knots = np.r_[[lower] * degree, inner, [upper] * degree]
    return BSpline.design_matrix(
        np.clip(values, lower, upper), knots, degree
    ).toarray()


def design_matrix(lat, lon, doy):
    lat_basis = spline_basis(lat, *LAT_SPLINE)
    lon_basis = spline_basis(lon, *LON_SPLINE)
    spatial = (lat_basis[:, :, None] * lon_basis[:, None, :]).reshape(
        len(lat), -1
    )

    angle = 2 * np.pi * doy / 365.25
    seasonal = np.column_stack([
        np.ones_like(angle),
        np.cos(angle),
        np.sin(angle),
        np.cos(2 * angle),
        np.sin(2 * angle),
    ])

    return (seasonal[:, :, None] * spatial[:, None, :]).reshape(len(lat), -1)


# Fit normal SST using only 2001–2010 observations.
training = readings.loc[readings["year"].between(2001, TRAIN_END_YEAR)]

units = (
    training.assign(
        cell_lat=np.floor(training["lat"]),
        cell_lon=np.floor(training["lon"]),
    )
    .groupby(["year", "month", "cell_lat", "cell_lon"], as_index=False)
    .agg(
        lat=("lat", "mean"),
        lon=("lon", "mean"),
        doy=("doy", "mean"),
        sst=("sst_degC", "mean"),
    )
)

# Give each training year the same total weight.
units["weight"] = 1 / units.groupby("year")["sst"].transform("size")
units["weight"] /= units["weight"].mean()

n_lat, n_lon = LAT_SPLINE[2], LON_SPLINE[2]
lat_diff = np.diff(np.eye(n_lat), n=2, axis=0)
lon_diff = np.diff(np.eye(n_lon), n=2, axis=0)
spatial_penalty = (
    np.kron(lat_diff.T @ lat_diff, np.eye(n_lon))
    + np.kron(np.eye(n_lat), lon_diff.T @ lon_diff)
)

n_features = 5 * n_lat * n_lon
penalty = np.kron(np.eye(5), spatial_penalty) + 1e-6 * np.eye(n_features)

# Accumulate the fit one year at a time to limit memory use.
xtwx = np.zeros((n_features, n_features))
xtwy = np.zeros(n_features)

for _, year_data in units.groupby("year"):
    x = design_matrix(
        year_data["lat"].to_numpy(),
        year_data["lon"].to_numpy(),
        year_data["doy"].to_numpy(),
    )
    weighted_xt = x.T * year_data["weight"].to_numpy()
    xtwx += weighted_xt @ x
    xtwy += weighted_xt @ year_data["sst"].to_numpy()

beta = np.linalg.solve(xtwx + penalty, xtwy)

# Use the fitted 2001–2010 normal to calculate anomalies for all readings.
lat = readings["lat"].to_numpy()
lon = readings["lon"].to_numpy()
doy = readings["doy"].to_numpy()
baseline = np.empty(len(readings))

for start in range(0, len(readings), CHUNK_SIZE):
    batch = slice(start, start + CHUNK_SIZE)
    baseline[batch] = design_matrix(lat[batch], lon[batch], doy[batch]) @ beta

readings["sst_anom"] = readings["sst_degC"] - baseline

# Average within 2° cells, then combine the usable cells by area.
readings["cell_lat"] = np.floor(readings["lat"] / 2) * 2
readings["cell_lon"] = np.floor(readings["lon"] / 2) * 2
month_keys = ["year", "month"]

cells = (
    readings.groupby(month_keys + ["cell_lat", "cell_lon"], as_index=False)
    .agg(anomaly=("sst_anom", "mean"), n_readings=("sst_anom", "size"))
)
cells = cells.loc[cells["n_readings"].ge(24)].copy()
cells["area"] = np.cos(np.radians(cells["cell_lat"] + 1))
cells["weighted_anomaly"] = cells["anomaly"] * cells["area"]

monthly = cells.groupby(month_keys).agg(
    weighted_sum=("weighted_anomaly", "sum"),
    area_sum=("area", "sum"),
    n_cells=("anomaly", "size"),
)
monthly["sst_anom"] = monthly["weighted_sum"] / monthly["area_sum"]
monthly = monthly[["sst_anom", "n_cells"]]

# Keep all calendar months so gaps are visible to the forecast script.
calendar = pd.MultiIndex.from_product(
    [range(2001, 2023), range(1, 13)], names=month_keys
)
monthly = monthly.reindex(calendar)
monthly["n_drifters"] = readings.groupby(month_keys)["id"].nunique()

count_columns = ["n_cells", "n_drifters"]
monthly[count_columns] = monthly[count_columns].fillna(0).astype(int)
monthly["low_coverage"] = (
    monthly["n_cells"].lt(10) | monthly["n_drifters"].lt(5)
)

monthly.to_csv(OUTPUT_FILE)
print(f"Saved {len(monthly)} calendar months to {OUTPUT_FILE}")
print(f"Months with an SST anomaly: {monthly['sst_anom'].notna().sum()}")