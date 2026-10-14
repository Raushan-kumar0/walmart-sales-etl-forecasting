"""Runs the questions in sql/analysis_queries.sql, saves each result as CSV in outputs/,
and draws the weekly sales chart.

    python analysis.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import text

from etl.load import get_engine

ROOT = Path(__file__).resolve().parent


def named_queries(path: Path) -> dict:
    queries, name, lines = {}, None, []
    for line in path.read_text(encoding="utf-8").splitlines() + ["-- name: __end__"]:
        if line.startswith("-- name:"):
            if name:
                queries[name] = "\n".join(lines).strip().rstrip(";")
            name, lines = line.split(":", 1)[1].strip(), []
        elif name:
            lines.append(line)
    return queries


def main():
    engine = get_engine()
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "images").mkdir(exist_ok=True)
    with engine.connect() as conn:
        for name, sql in named_queries(ROOT / "sql" / "analysis_queries.sql").items():
            df = pd.read_sql(text(sql), conn)
            df.to_csv(ROOT / "outputs" / f"{name}.csv", index=False)
            print(f"\n== {name} ==\n{df.to_string(index=False)}")
        weekly = pd.read_sql(text("SELECT week_date, SUM(weekly_sales) AS total, MAX(is_holiday_week) AS holiday "
                                  "FROM weekly_sales GROUP BY week_date ORDER BY week_date"), conn)

    weekly["week_date"] = pd.to_datetime(weekly["week_date"])
    weekly["total"] = weekly["total"].astype(float) / 1e6
    fig, ax = plt.subplots(figsize=(10, 4), dpi=110)
    ax.plot(weekly["week_date"], weekly["total"], color="#1F3864", lw=1.2)
    hol = weekly[weekly["holiday"] == 1]
    ax.scatter(hol["week_date"], hol["total"], color="#C62828", zorder=3, s=18, label="Holiday week (flag in data)")
    ax.set_title("Walmart weekly sales, all 45 stores")
    ax.set_ylabel("Sales ($ millions)")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "weekly_sales.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
