"""
Bengaluru Real Estate Price Prediction - Data Cleaning & Model Training
Trains Linear Regression and Random Forest, picks the better one, saves it
along with evaluation metrics (R2, MAE, RMSE) for the web app to use.
"""
import pandas as pd
import numpy as np
import pickle
import json
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("Loading dataset...")
df = pd.read_csv("Bengaluru_House_Data.csv")
print(f"Raw shape: {df.shape}")

# ---- 1. Keep only the 5 columns we actually need ----
df = df[["location", "size", "total_sqft", "bath", "price"]].copy()

# ---- 2. Extract BHK number from 'size' (e.g. "2 BHK" -> 2, "4 Bedroom" -> 4) ----
df.dropna(subset=["size"], inplace=True)
df["bhk"] = df["size"].apply(lambda x: int(str(x).split(" ")[0]))

# ---- 3. Convert total_sqft to a clean float (handles ranges like "2100 - 2850") ----
def convert_sqft(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        pass
    tokens = str(x).split("-")
    if len(tokens) == 2:
        try:
            return (float(tokens[0].strip()) + float(tokens[1].strip())) / 2
        except ValueError:
            return None
    return None  # drops rows with units like "34.46Sq. Meter"

df["total_sqft"] = df["total_sqft"].apply(convert_sqft)
df.dropna(subset=["total_sqft", "bath", "price"], inplace=True)

# ---- 4. Remove unrealistic rows ----
df = df[df["total_sqft"] / df["bhk"] >= 300]          # sqft per bedroom too small = bad data entry
df = df[df["bath"] <= df["bhk"] + 2]                   # more bathrooms than bedrooms+2 is unusual/bad data

# ---- 5. Clean up location text + bucket rare locations as "other" ----
df["location"] = df["location"].apply(lambda x: str(x).strip())
location_counts = df["location"].value_counts()
rare_locations = location_counts[location_counts <= 10].index
df["location"] = df["location"].apply(lambda x: "other" if x in rare_locations else x)

# ---- 6. Remove price-per-sqft outliers within each location (mean +/- 1 std) ----
df["price_per_sqft"] = df["price"] * 100000 / df["total_sqft"]

def remove_pps_outliers(data):
    out = pd.DataFrame()
    for key, subdf in data.groupby("location"):
        m = np.mean(subdf.price_per_sqft)
        s = np.std(subdf.price_per_sqft)
        reduced = subdf[(subdf.price_per_sqft > (m - s)) & (subdf.price_per_sqft <= (m + s))]
        out = pd.concat([out, reduced], ignore_index=True)
    return out

df = remove_pps_outliers(df)
print(f"Cleaned shape: {df.shape}")

# ---- 7. One-hot encode location ----
dummies = pd.get_dummies(df["location"])
df_model = pd.concat([df[["total_sqft", "bath", "bhk"]], dummies], axis=1)
X = df_model
y = df["price"]

feature_columns = list(X.columns)
locations = sorted([c for c in dummies.columns if c != "other"])

# ---- 8. Train/test split ----
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ---- 9. Train both models ----
lr = LinearRegression()
lr.fit(X_train, y_train)
lr_pred = lr.predict(X_test)

rf = RandomForestRegressor(n_estimators=200, random_state=42, max_depth=12, n_jobs=-1)
rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)

def metrics(y_true, y_pred):
    return {
        "r2": round(r2_score(y_true, y_pred), 4),
        "mae": round(mean_absolute_error(y_true, y_pred), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
    }

lr_metrics = metrics(y_test, lr_pred)
rf_metrics = metrics(y_test, rf_pred)

print("Linear Regression:", lr_metrics)
print("Random Forest:", rf_metrics)

# ---- 10. Pick the better model by R2 ----
if rf_metrics["r2"] >= lr_metrics["r2"]:
    best_model, best_name, best_metrics = rf, "Random Forest", rf_metrics
else:
    best_model, best_name, best_metrics = lr, "Linear Regression", lr_metrics

print(f"Selected model: {best_name}")

# ---- 11. Save everything the Flask app needs ----
with open("model.pkl", "wb") as f:
    pickle.dump(best_model, f)

with open("model_meta.json", "w") as f:
    json.dump({
        "model_name": best_name,
        "feature_columns": feature_columns,
        "locations": locations,
        "metrics": {"linear_regression": lr_metrics, "random_forest": rf_metrics, "selected": best_name},
        "rows_used_for_training": len(df),
        "rows_raw": 13320,
    }, f, indent=2)

# ---- 12. Save per-locality average stats for "Locality Insights" ----
locality_stats = (
    df.groupby("location")
    .agg(avg_price_lakhs=("price", "mean"), avg_price_per_sqft=("price_per_sqft", "mean"),
         avg_sqft=("total_sqft", "mean"), listings=("price", "count"))
    .round(1)
    .reset_index()
    .sort_values("listings", ascending=False)
)
locality_stats.to_json("locality_stats.json", orient="records")

print("Saved model.pkl, model_meta.json, locality_stats.json")
