"""TRANSFORM: check, clean and join the three files into one weekly sales table.

Rules
 - Text "NA" / empty -> missing; numbers and dates parsed; "TRUE"/"FALSE" -> booleans.
 - Duplicate (store, dept, week) rows in train -> removed (keep first).
 - Rows with a missing store, dept, date or sales value -> removed.
 - Negative weekly sales (returns bigger than sales that week) are KEPT but flagged,
   because they are real - dropping them would overstate sales.
 - MarkDown1-5: missing means "no markdown data" (Walmart only started recording them
   in Nov 2011), so they become 0 and a flag says whether markdown data existed.
 - features.csv also covers the Kaggle test period (after Oct 2012); only weeks that
   exist in train are kept.
 - Every sales row must find its store and its (store, week) features, otherwise it is reported.
"""
import pandas as pd

MARKDOWNS = [f"MarkDown{i}" for i in range(1, 6)]


def _blank_to_na(df):
    return df.apply(lambda s: s.str.strip().replace({"": pd.NA, "NA": pd.NA}))


def transform(frames: dict) -> tuple[pd.DataFrame, dict]:
    log = {}
    train = _blank_to_na(frames["train"])
    feats = _blank_to_na(frames["features"])
    stores = _blank_to_na(frames["stores"])
    log["train_rows_in"] = len(train)

    # --- train ---------------------------------------------------------------
    train["Store"] = pd.to_numeric(train["Store"], errors="coerce").astype("Int64")
    train["Dept"] = pd.to_numeric(train["Dept"], errors="coerce").astype("Int64")
    train["Date"] = pd.to_datetime(train["Date"], format="%Y-%m-%d", errors="coerce")
    train["Weekly_Sales"] = pd.to_numeric(train["Weekly_Sales"], errors="coerce")
    train["IsHoliday"] = train["IsHoliday"].str.upper().eq("TRUE")

    missing = train[["Store", "Dept", "Date", "Weekly_Sales"]].isna().any(axis=1)
    log["rows_missing_key_values_removed"] = int(missing.sum())
    train = train[~missing]

    before = len(train)
    train = train.drop_duplicates(subset=["Store", "Dept", "Date"], keep="first")
    log["duplicate_rows_removed"] = before - len(train)
    log["negative_sales_rows_flagged"] = int((train["Weekly_Sales"] < 0).sum())

    # --- features --------------------------------------------------------------
    feats["Store"] = pd.to_numeric(feats["Store"], errors="coerce").astype("Int64")
    feats["Date"] = pd.to_datetime(feats["Date"], format="%Y-%m-%d", errors="coerce")
    for col in ["Temperature", "Fuel_Price", "CPI", "Unemployment"] + MARKDOWNS:
        feats[col] = pd.to_numeric(feats[col], errors="coerce")
    log["features_rows_in"] = len(feats)
    feats = feats[feats["Date"].between(train["Date"].min(), train["Date"].max())]
    log["features_rows_outside_train_period_dropped"] = log["features_rows_in"] - len(feats)
    log["markdown_values_missing_set_to_0"] = int(feats[MARKDOWNS].isna().sum().sum())
    feats["has_markdown_data"] = feats[MARKDOWNS].notna().any(axis=1)
    feats[MARKDOWNS] = feats[MARKDOWNS].fillna(0)
    feats["total_markdown"] = feats[MARKDOWNS].sum(axis=1).round(2)
    log["cpi_or_unemployment_missing_in_train_period"] = int(feats[["CPI", "Unemployment"]].isna().any(axis=1).sum())

    # --- stores ---------------------------------------------------------------
    stores["Store"] = pd.to_numeric(stores["Store"], errors="coerce").astype("Int64")
    stores["Size"] = pd.to_numeric(stores["Size"], errors="coerce").astype("Int64")

    # --- join -------------------------------------------------------------------
    df = (train
          .merge(feats[["Store", "Date", "Temperature", "Fuel_Price", "CPI", "Unemployment",
                        "total_markdown", "has_markdown_data"]], on=["Store", "Date"], how="left", indicator="f")
          .merge(stores, on="Store", how="left", indicator="s"))
    log["sales_rows_without_features"] = int((df["f"] != "both").sum())
    log["sales_rows_without_store_info"] = int((df["s"] != "both").sum())

    out = pd.DataFrame({
        "store": df["Store"].astype(int),
        "dept": df["Dept"].astype(int),
        "week_date": df["Date"].dt.date,
        "weekly_sales": df["Weekly_Sales"].round(2),
        "is_negative_sales": df["Weekly_Sales"] < 0,
        "is_holiday_week": df["IsHoliday"],
        "store_type": df["Type"],
        "store_size": df["Size"].astype("Int64"),
        "temperature": df["Temperature"],
        "fuel_price": df["Fuel_Price"],
        "cpi": df["CPI"].round(4),
        "unemployment": df["Unemployment"],
        "total_markdown": df["total_markdown"],
        "has_markdown_data": df["has_markdown_data"],
    }).sort_values(["week_date", "store", "dept"]).reset_index(drop=True)
    log["rows_out"] = len(out)
    return out, log
