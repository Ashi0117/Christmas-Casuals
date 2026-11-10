# ============================================================================
# LOCATION-CORRECTED MONTHLY SST ANOMALIES
# Place this directly after the cell that builds `df`.
# Needs numpy, pandas and scipy 1.8 or newer.
#
# THE PROBLEM
# Drifters are not spread evenly, and the south of the region is much colder
# than the north. A month with more southern drifters therefore looks cold even
# if the ocean has not changed. The simple monthly mean has a 0.92 correlation
# with the drifters' mean latitude, so it mostly tracks where they were.
#
# THE FIX
# Compare each reading with what is normal for that place and time of year,
# then average those differences (anomalies) instead of the raw temperatures.
#
# WHAT THIS CELL CREATES
# In df (one row per hourly reading):
#   sst_baseline    normal SST for that location and day of year (C)
#   sst_anom        sst_degC minus sst_baseline (C)
#
# In sst_monthly (one row per month, 2001 to 2022):
#   sst_anom        regional anomaly, the main corrected series (C)
#   sst_anom_north  anomaly north of 30S (C)
#   sst_anom_south  anomaly south of 30S (C)
#   sst_adjusted    regional normal for that calendar month plus sst_anom (C)
#   sst_simple      uncorrected monthly mean, kept for comparison (C)
#   mean_lat        mean latitude of that month's readings
#   n_drifters      number of drifters in the month
#   n_cells         number of 2-degree cells used in the month
#   low_coverage    True if under 10 cells or under 5 drifters; treat with care
#   date            15th of the month, for plotting
# ============================================================================
from scipy.interpolate import BSpline
from data_cleaning import df
import pandas as pd
import numpy as np



# ---- Step 1: filters --------------------------------------------------------
# Real winter SST south of 40S falls below 10 C, so a 10 C minimum makes the far
# south look about 1.9 C too warm. If df was built with that minimum, start again
# from the clean arrays so those cold readings return.


df = df[(df["sst_degC"] >= 5.0) & (df["sst_degC"] <= 35.0)]
# The region's box also catches the Atlantic east of the Andes, which is not part of the Humboldt system
df = df[~((df["lat"] < -40) & (df["lon"] > -71))].reset_index(drop=True)


# ---- Step 2: the baseline model ---------------------------------------------
# SST(lat, lon, day of year) = smooth map + smooth maps of the annual and
# semi-annual cycles. A smooth fit is needed because many 1-degree cells, mainly
# in the north, have only a few drifters and do not cover every calendar month.
LAT_SPLINE = (-54, -4, 16)
LON_SPLINE = (-94, -65, 10)
SMOOTHING = 1.0              # larger values give a smoother map
N_HARMONICS = 2              # 1 = annual cycle, 2 = adds the semi-annual cycle




def spline_basis(x, lo, hi, n, degree=3):
   """Smooth curves along one axis, which combine to form the map."""
   inner = np.linspace(lo, hi, n - degree + 1)
   knots = np.r_[[lo] * degree, inner, [hi] * degree]
   return BSpline.design_matrix(np.clip(x, lo, hi - 1e-9), knots, degree).toarray()




def seasonal_terms(doy):
   """Constant term plus sine and cosine waves for each seasonal cycle."""
   w = 2 * np.pi * doy / 365.25
   terms = [np.ones_like(w)]
   for k in range(1, N_HARMONICS + 1):
       terms += [np.cos(k * w), np.sin(k * w)]
   return np.column_stack(terms)




def design_matrix(lat, lon, doy):
   """Combine latitude, longitude and season so each season gets its own map."""
   A, B, H = spline_basis(lat, *LAT_SPLINE), spline_basis(lon, *LON_SPLINE), seasonal_terms(doy)
   surface = (A[:, :, None] * B[:, None, :]).reshape(len(lat), -1)
   return (H[:, :, None] * surface[:, None, :]).reshape(len(lat), -1)




def roughness_penalty():
   """Penalise sharp changes between neighbouring map points."""
   D = lambda n: np.diff(np.eye(n), 2, axis=0)
   na, nb = LAT_SPLINE[2], LON_SPLINE[2]
   spatial = (np.kron(D(na).T @ D(na), np.eye(nb))
              + np.kron(np.eye(na), D(nb).T @ D(nb)))
   return np.kron(np.eye(1 + 2 * N_HARMONICS), spatial)




def predict(beta, lat, lon, doy, chunk=20_000):
   """Normal SST for any set of points, in chunks to keep memory use low."""
   out = np.empty(len(lat))
   for i in range(0, len(lat), chunk):
       s = slice(i, i + chunk)
       out[s] = design_matrix(lat[s], lon[s], doy[s]) @ beta
   return out




# ---- Step 3: fit the baseline -----------------------------------------------
# Fit to 1-degree cell monthly averages, so a drifter's many hourly readings do
# not dominate. Each year gets equal total weight, so data-rich years do not
# define what is normal.
units = (df.assign(cell_lat=np.floor(df["lat"]), cell_lon=np.floor(df["lon"]))
          .groupby(["cell_lat", "cell_lon", "year", "month"])
          .agg(lat=("lat", "mean"), lon=("lon", "mean"), doy=("doy", "mean"), sst=("sst_degC", "mean"))
          .reset_index())
unit_weight = (1 / units.groupby("year")["sst"].transform("size")).to_numpy()
unit_weight = unit_weight * len(units) / unit_weight.sum()


# Build the fit one year at a time, so the full matrix never sits in memory
XtWX_year, XtWy_year = {}, {}
for year in sorted(units["year"].unique()):
   k = (units["year"] == year).to_numpy()
   Xk = design_matrix(units["lat"].to_numpy()[k], units["lon"].to_numpy()[k], units["doy"].to_numpy()[k])
   XtWX_year[year] = (Xk.T * unit_weight[k]) @ Xk
   XtWy_year[year] = (Xk.T * unit_weight[k]) @ units["sst"].to_numpy()[k]
XtWX, XtWy = sum(XtWX_year.values()), sum(XtWy_year.values())
penalty = SMOOTHING * roughness_penalty() + 1e-6 * np.eye(XtWX.shape[0])


# Fit using all years; used only for the regional normal in Step 6
beta_full = np.linalg.solve(XtWX + penalty, XtWy)


# ---- Step 4: anomaly for each reading ---------------------------------------
# Each year is compared with a baseline fitted WITHOUT that year. Otherwise an
# unusual year would shift its own definition of normal and hide part of its signal.
df["sst_baseline"] = np.nan
for year, rows in df.groupby("year").indices.items():
   beta = np.linalg.solve(XtWX - XtWX_year[year] + penalty, XtWy - XtWy_year[year])
   df.iloc[rows, df.columns.get_loc("sst_baseline")] = predict(
       beta, df["lat"].to_numpy()[rows], df["lon"].to_numpy()[rows], df["doy"].to_numpy()[rows].astype(float))
df["sst_anom"] = df["sst_degC"] - df["sst_baseline"]


# ---- Step 5: combine anomalies into monthly series --------------------------
# Average within 2-degree cells first, so a cluster of drifters counts as one
# location. Then average the cells, weighted by area, as cells shrink further south.
CELL_DEG = 2
MIN_READINGS = 24        # a cell needs about one drifter-day of readings in the month
NORTH_SOUTH_SPLIT = -30


cells = df.assign(cell_lat=np.floor(df["lat"] / CELL_DEG) * CELL_DEG,
                 cell_lon=np.floor(df["lon"] / CELL_DEG) * CELL_DEG)
cell_month = (cells.groupby(["year", "month", "cell_lat", "cell_lon"])["sst_anom"]
                  .agg(anom="mean", n="size").reset_index())
cell_month = cell_month[cell_month["n"] >= MIN_READINGS]
cell_month["centre_lat"] = cell_month["cell_lat"] + CELL_DEG / 2
cell_month["area"] = np.cos(np.radians(cell_month["centre_lat"]))




def area_mean(c):
   """Area-weighted mean of the cell anomalies for each month."""
   keys = [c["year"], c["month"]]
   return (c["anom"] * c["area"]).groupby(keys).sum() / c["area"].groupby(keys).sum()




all_months = pd.MultiIndex.from_product([range(2001, 2023), range(1, 13)], names=["year", "month"])
north = cell_month["centre_lat"] >= NORTH_SOUTH_SPLIT
sst_monthly = pd.DataFrame({
   "sst_anom": area_mean(cell_month),
   "sst_anom_north": area_mean(cell_month[north]),
   "sst_anom_south": area_mean(cell_month[~north]),
}).reindex(all_months)


by_month = df.groupby(["year", "month"])
sst_monthly["n_drifters"] = by_month["id"].nunique()
sst_monthly["n_cells"] = cell_month.groupby(["year", "month"]).size()
sst_monthly[["n_drifters", "n_cells"]] = sst_monthly[["n_drifters", "n_cells"]].fillna(0).astype(int)
sst_monthly["low_coverage"] = (sst_monthly["n_cells"] < 10) | (sst_monthly["n_drifters"] < 5)


# ---- Step 6: convert back to a temperature ----------------------------------
# sst_adjusted = the region's normal SST for that calendar month + sst_anom.
# The normal always uses the same fixed cells, so it cannot move with the drifters.
fixed_cells = (cells.groupby(["cell_lat", "cell_lon"])
                   .agg(lat=("lat", "mean"), lon=("lon", "mean")).reset_index())
fixed_area = np.cos(np.radians(fixed_cells["cell_lat"] + CELL_DEG / 2))
mid_month_doy = pd.date_range("2001-01-15", periods=12, freq=pd.DateOffset(months=1)).dayofyear.to_numpy(float)
regional_normal = pd.Series(
   [np.average(predict(beta_full, fixed_cells["lat"].to_numpy(), fixed_cells["lon"].to_numpy(),
                       np.full(len(fixed_cells), d)), weights=fixed_area) for d in mid_month_doy],
   index=pd.RangeIndex(1, 13, name="month"))
sst_monthly["sst_adjusted"] = sst_monthly.index.get_level_values("month").map(regional_normal) + sst_monthly["sst_anom"]


# Uncorrected values, kept for comparison
sst_monthly["sst_simple"] = by_month["sst_degC"].mean()
sst_monthly["mean_lat"] = by_month["lat"].mean()
sst_monthly["date"] = pd.to_datetime({"year": sst_monthly.index.get_level_values("year"),
                                     "month": sst_monthly.index.get_level_values("month"),
                                     "day": 15}).to_numpy()


print(f"Readings used: {len(df):,}")
print(f"Months with data: {sst_monthly['sst_anom'].notna().sum()} of {len(sst_monthly)}; "
     f"low coverage: {(sst_monthly['low_coverage'] & sst_monthly['sst_anom'].notna()).sum()}")
print(sst_monthly.head())
sst_monthly.to_csv("sst_monthly_anomalies.csv")
