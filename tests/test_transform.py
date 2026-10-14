"""Tests for the cleaning and joining rules, using tiny hand-made tables (no database needed)."""
import pandas as pd

from etl.transform import transform


def frames():
    train = pd.DataFrame({
        "Store": ["1", "1", "1", "2"],
        "Dept": ["1", "1", "2", "1"],
        "Date": ["2012-01-06", "2012-01-06", "2012-01-06", "2012-01-06"],
        "Weekly_Sales": ["100.5", "100.5", "-20", ""],         # duplicate, a return-heavy week, a missing value
        "IsHoliday": ["FALSE", "FALSE", "FALSE", "FALSE"],
    })
    md = {f"MarkDown{i}": ["NA", "NA"] for i in range(1, 6)}
    md["MarkDown1"] = ["50", "NA"]
    features = pd.DataFrame({
        "Store": ["1", "1"], "Date": ["2012-01-06", "2013-05-03"],     # second row is outside the sales period
        "Temperature": ["40", "60"], "Fuel_Price": ["3.1", "3.5"], **md,
        "CPI": ["211.1", "NA"], "Unemployment": ["7.1", "NA"], "IsHoliday": ["FALSE", "FALSE"],
    })
    stores = pd.DataFrame({"Store": ["1", "2"], "Type": ["A", "C"], "Size": ["150000", "40000"]})
    return {"train": train, "features": features, "stores": stores}


def test_cleaning_and_join():
    df, log = transform(frames())
    assert log["rows_missing_key_values_removed"] == 1
    assert log["duplicate_rows_removed"] == 1
    assert log["negative_sales_rows_flagged"] == 1
    assert log["features_rows_outside_train_period_dropped"] == 1
    assert len(df) == 2
    assert df["is_negative_sales"].tolist() == [False, True]       # negative sales kept, but flagged
    assert df["total_markdown"].tolist() == [50.0, 50.0]          # missing markdowns count as 0
    assert df["store_type"].tolist() == ["A", "A"]
    assert log["sales_rows_without_features"] == 0


def test_same_result_every_run():
    a, _ = transform(frames())
    b, _ = transform(frames())
    pd.testing.assert_frame_equal(a, b)
