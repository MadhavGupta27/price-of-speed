"""Audit the Kaggle delivery datasets and extract only what survives the audit.

    uv run python scripts/audit_kaggle.py

Findings (written to results/data_audit_kaggle.json) justify, in the paper's
Data section, why geography comes from WorldPop/OSM/BBMP instead of Kaggle:
  * food-delivery: delivery point = restaurant + an identical lat/lon offset
    drawn from a handful of values -> synthetic geometry; distances/speeds unusable.
  * blinkit: Faker-style names/emails (example.com/.org) -> synthetic; excluded.
  * food-delivery traffic density is a (near-)deterministic function of the
    order hour and hours 01-07 are empty -> the temporal fields are generated too.
Retained only as an *illustrative* sensitivity range for the peak-hour demand
multiplier (data/processed/order_hour_profile.csv); never as calibrated evidence.
"""

import json

import pandas as pd

from orpaper.config import ROOT

FOOD = ROOT / "data/raw/kaggle_gauravmalik26_food-delivery-dataset/train.csv"
BLINKIT = ROOT / "data/raw/kaggle_akxiit_blinkit-sales-dataset"


def load_food() -> pd.DataFrame:
    df = pd.read_csv(FOOD)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        if df[c].dtype == object or str(df[c].dtype).startswith("str"):
            df[c] = df[c].astype(str).str.strip().replace({"NaN": pd.NA, "nan": pd.NA})
    return df


def audit_food(df: pd.DataFrame) -> dict:
    dlat = (df["Delivery_location_latitude"] - df["Restaurant_latitude"].abs()).round(6)
    dlon = (df["Delivery_location_longitude"] - df["Restaurant_longitude"].abs()).round(6)
    return {
        "rows": len(df),
        "share_identical_lat_lon_offset": round(float((dlat == dlon).mean()), 4),
        "distinct_offsets_deg": sorted(dlat[dlat == dlon].unique().tolist()),
        "rows_restaurant_lat_abs_lt_1": int((df["Restaurant_latitude"].abs() < 1).sum()),
        "rows_negative_restaurant_coords": int(((df["Restaurant_latitude"] < 0)
                                                | (df["Restaurant_longitude"] < 0)).sum()),
        "distinct_restaurant_points": int(df[["Restaurant_latitude", "Restaurant_longitude"]]
                                          .drop_duplicates().shape[0]),
        "verdict": "Delivery geometry is synthetic (restaurant + fixed diagonal offset); "
                   "do not use for distances, speeds or demand locations.",
    }


def audit_blinkit() -> dict:
    cust = pd.read_csv(BLINKIT / "blinkit_customers.csv")
    email_dom = cust["email"].str.split("@").str[1]
    placeholder = email_dom.isin(["example.com", "example.org", "example.net"]).mean()
    return {
        "customers": len(cust),
        "share_placeholder_email_domains": round(float(placeholder), 4),
        "verdict": "Synthetic (Faker-generated customers; RFC 2606 example domains). Excluded.",
    }


def hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    t = pd.to_datetime(df["Time_Orderd"], format="mixed", errors="coerce")
    hour = t.dt.hour
    prof = hour.value_counts().sort_index().rename("orders").to_frame()
    prof["share"] = prof["orders"] / prof["orders"].sum()
    prof["multiplier_vs_mean"] = prof["orders"] / prof["orders"].mean()
    traffic = pd.crosstab(hour, df["Road_traffic_density"], normalize="index").round(4)
    out = prof.join(traffic).reset_index().rename(columns={"Time_Orderd": "hour", "index": "hour"})
    return out


def main():
    df = load_food()
    audit = {"food_delivery": audit_food(df), "blinkit": audit_blinkit()}
    prof = hourly_profile(df)
    audit["food_delivery"]["peak_hour"] = int(prof.loc[prof["orders"].idxmax(), "hour"])
    audit["food_delivery"]["peak_multiplier_vs_mean_hour"] = round(float(prof["multiplier_vs_mean"].max()), 3)
    traffic_cols = [c for c in prof.columns if c in ("High", "Jam", "Low", "Medium")]
    audit["food_delivery"]["share_hours_single_traffic_level_ge_90pct"] = round(
        float((prof[traffic_cols].max(axis=1) >= 0.9).mean()), 3)
    audit["food_delivery"]["hours_with_no_orders"] = sorted(set(range(24)) - set(prof["hour"].dropna().astype(int)))
    audit["food_delivery"]["temporal_verdict"] = (
        "Traffic level is fixed by hour and night hours are empty: temporal fields are generated. "
        "Peak multiplier usable only as an illustrative sensitivity range.")
    audit["food_delivery"]["rows_unparseable_order_time"] = int(
        pd.to_datetime(df["Time_Orderd"], format="mixed", errors="coerce").isna().sum())

    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/data_audit_kaggle.json").write_text(json.dumps(audit, indent=2))
    out = ROOT / "data/processed/order_hour_profile.csv"
    prof.to_csv(out, index=False)
    print(json.dumps(audit, indent=2))
    print(f"\nWrote results/data_audit_kaggle.json and {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
