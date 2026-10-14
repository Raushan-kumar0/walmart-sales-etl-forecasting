"""
Weekly sales forecasting with moving averages, tested against what actually sold.

Methods compared (each forecasts next week using only earlier weeks):
  naive           next week = this week
  MA-4/8/12       next week = average of the last 4 / 8 / 12 weeks
  seasonal naive  next week = the same week last year (52 weeks earlier)
  seasonal + recent level
                  same week last year, scaled by how the last 4 weeks compare
                  with the same 4 weeks a year earlier (catches growth or decline)

Backtest: the last 52 weeks of data (Nov 2011 - Oct 2012), so it includes the
holiday season. Error = MAPE (average % miss). Done for all stores together and
for each store type (A, B, C).

    python forecast.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sqlalchemy import text

from etl.load import get_engine

ROOT = Path(__file__).resolve().parent
BACKTEST_WEEKS = 52
HORIZON = 4


def forecasts(s: pd.Series) -> dict[str, pd.Series]:
    past = s.shift(1)
    return {
        "Naive": past,
        "MA-4": past.rolling(4).mean(),
        "MA-8": past.rolling(8).mean(),
        "MA-12": past.rolling(12).mean(),
        "Seasonal naive": s.shift(52),
        # last year's pattern x this year's level
        "Seasonal + level": s.shift(52) * (past.rolling(4).mean() / s.shift(53).rolling(4).mean()),
    }


def mape(actual, pred):
    return float(np.mean(np.abs(actual - pred) / np.abs(actual)) * 100)


def main():
    with get_engine().connect() as conn:
        df = pd.read_sql(text("SELECT week_date, store_type, SUM(weekly_sales) AS sales "
                              "FROM weekly_sales GROUP BY week_date, store_type"), conn)
    df["week_date"] = pd.to_datetime(df["week_date"])
    df["sales"] = df["sales"].astype(float)
    wide = df.pivot(index="week_date", columns="store_type", values="sales").sort_index()
    wide.columns = [f"Type {c}" for c in wide.columns]
    wide.insert(0, "All stores", wide.sum(axis=1))
    test = wide.index[-BACKTEST_WEEKS:]

    rows = []
    for col in wide.columns:
        for method, pred in forecasts(wide[col]).items():
            rows.append({"series": col, "method": method, "MAPE_pct": round(mape(wide[col][test], pred[test]), 1)})
    bt = pd.DataFrame(rows)
    table = bt.pivot(index="series", columns="method", values="MAPE_pct")[
        ["Naive", "MA-4", "MA-8", "MA-12", "Seasonal naive", "Seasonal + level"]]
    print(f"Backtest MAPE % over the last {BACKTEST_WEEKS} weeks ({test[0].date()} to {test[-1].date()}), lower is better:")
    print(table.to_string())

    # Holiday season vs the rest: where does each method break down?
    season = (test.month >= 11) | (test.month == 1)
    s, f = wide["All stores"], forecasts(wide["All stores"])
    split = pd.DataFrame({m: {"Nov-Jan weeks": mape(s[test][season], f[m][test][season]),
                              "Other weeks": mape(s[test][~season], f[m][test][~season])} for m in f}).round(1)
    print("\nAll stores, MAPE % by part of the year:")
    print(split.to_string())

    # Next 4 weeks for all stores
    future = pd.date_range(wide.index[-1] + pd.Timedelta(weeks=1), periods=HORIZON, freq="7D")
    nxt = pd.DataFrame({
        "week_date": future.date,
        "MA-4 forecast ($M)": round(s.iloc[-4:].mean() / 1e6, 1),           # flat: same value every week
        "Seasonal naive forecast ($M)": [round(s.get(d - pd.Timedelta(weeks=52), np.nan) / 1e6, 1) for d in future],
    })
    level = s.iloc[-4:].mean() / s.shift(52).iloc[-4:].mean()   # this year's last 4 weeks vs same weeks last year
    nxt["Seasonal + level forecast ($M)"] = (nxt["Seasonal naive forecast ($M)"] * level).round(1)
    print("\nNext 4 weeks, all stores:")
    print(nxt.to_string(index=False))

    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    table.to_csv(out / "forecast_backtest_mape.csv")
    split.to_csv(out / "forecast_mape_by_season.csv")
    nxt.to_csv(out / "forecast_next_4_weeks.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=110)
    window = wide.index[-BACKTEST_WEEKS - 10:]
    ax.plot(window, s[window] / 1e6, color="#888888", lw=1.3, label="Actual")
    ax.plot(test, f["MA-4"][test] / 1e6, color="#C62828", lw=1.8, label="4-week moving average")
    ax.plot(test, f["Seasonal naive"][test] / 1e6, color="#1F3864", lw=1.2, ls="--", label="Same week last year")
    ax.plot(test, f["Seasonal + level"][test] / 1e6, color="#2E7D32", lw=1.2, label="Same week last year x recent level")
    ax.set_title("All stores: weekly sales vs forecasts (backtest period)")
    ax.set_ylabel("Sales ($ millions)")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(ROOT / "images" / "forecast_backtest.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
