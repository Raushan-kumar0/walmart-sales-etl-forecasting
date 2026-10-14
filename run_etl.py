"""Runs the ETL pipeline: Kaggle CSV files -> checks and cleaning -> MySQL table weekly_sales.

    python run_etl.py
"""
import json
from pathlib import Path

from etl.extract import extract
from etl.load import get_engine, load
from etl.transform import transform

ROOT = Path(__file__).resolve().parent


def main():
    print("Extract")
    frames = extract(ROOT / "data")
    print("Transform")
    df, log = transform(frames)
    print("Load")
    log["rows_loaded"] = load(df, log, get_engine())

    print("\nData quality report")
    for k, v in log.items():
        print(f"  {k:<46}{v:>10,}")
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "etl_report.json").write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
