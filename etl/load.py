"""LOAD: replace the weekly_sales table in MySQL inside one transaction.

Re-running gives the same table (no duplicates pile up), and if something fails
half way the old data is left as it was. Every run is logged in etl_runs.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set - copy .env.example to .env and fill it in.")
    return create_engine(url, pool_pre_ping=True)


def load(df: pd.DataFrame, log: dict, engine) -> int:
    statements = [s for s in SCHEMA.read_text(encoding="utf-8").split(";")
                  if "\n".join(l for l in s.splitlines() if not l.strip().startswith("--")).strip()]
    with engine.begin() as conn:
        for s in statements:
            conn.execute(text(s))
        conn.execute(text("DELETE FROM weekly_sales"))
        df.to_sql("weekly_sales", conn, if_exists="append", index=False, chunksize=10000, method="multi")
        loaded = conn.execute(text("SELECT COUNT(*) FROM weekly_sales")).scalar()
        if loaded != len(df):
            raise RuntimeError(f"Row count check failed: {len(df)} rows prepared, {loaded} in MySQL")
        conn.execute(text("INSERT INTO etl_runs (run_at, rows_in, rows_loaded, report_json) "
                          "VALUES (:t, :i, :l, :r)"),
                     {"t": datetime.now().replace(microsecond=0), "i": log["train_rows_in"],
                      "l": loaded, "r": json.dumps(log)})
    return loaded
