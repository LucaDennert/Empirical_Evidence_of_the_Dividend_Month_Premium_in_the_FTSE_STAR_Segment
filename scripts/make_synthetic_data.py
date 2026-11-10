"""
Generate a synthetic dataset with the same file layout as the original data.

The LSEG/Refinitiv data used in the thesis cannot be redistributed. This
script writes artificial files that mimic the LSEG Workspace exports and the
Kenneth French CSV files, so that the full pipeline can be run and inspected
without a data licence:

    python scripts/make_synthetic_data.py --out example_data
    python -m dmp --data-dir example_data --output-dir example_outputs

The numbers produced on synthetic data are meaningless: a pre-ex-date drift
proportional to the dividend yield is injected only to make the outputs
non-trivial.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

START, END = "2019-06-01", "2024-12-31"
HOLIDAYS = ["01-01", "12-25", "12-26", "05-01", "08-15", "12-24", "12-31"]


def calendar() -> pd.DatetimeIndex:
    days = pd.bdate_range(START, END)
    return days[~days.strftime("%m-%d").isin(HOLIDAYS)]


def write_french_csvs(days: pd.DatetimeIndex, rng: np.random.Generator, out: Path) -> pd.DataFrame:
    """Daily factors in percent, in the Kenneth French CSV layout."""
    # European factor dates differ slightly from the Italian calendar
    fdays = pd.bdate_range(START, END)
    fdays = fdays[~fdays.strftime("%m-%d").isin(["01-01", "12-25"])]
    n = len(fdays)
    f = pd.DataFrame({
        "Mkt-RF": rng.normal(0.04, 1.1, n),
        "SMB": rng.normal(0.0, 0.45, n),
        "HML": rng.normal(0.0, 0.55, n),
        "RMW": rng.normal(0.01, 0.35, n),
        "CMA": rng.normal(0.0, 0.3, n),
        "RF": np.clip(np.linspace(-0.002, 0.015, n), 0, None),
        "WML": rng.normal(0.02, 0.7, n),
    }, index=fdays).round(2)

    def dump(cols: list[str], name: str, title: str) -> None:
        body = f[cols].copy()
        body.index = body.index.strftime("%Y%m%d")
        text = f"{title}\nThis file was created synthetically for testing.\n\n" + body.to_csv(index_label="")
        (out / name).write_text(text)

    dump(["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"], "Europe_5_Factors_Daily.csv",
         "This file was created using the 202412 Bloomberg database.")
    dump(["WML"], "Europe_Mom_Factor_Daily.csv", "Missing data are indicated by -99.99.")
    return f / 100


def simulate_stock(days, factors, rng):
    """Prices with a yield-dependent pre-ex-date run-up and partial post-ex reversal."""
    n = len(days)
    mkt = factors["Mkt-RF"].reindex(days).fillna(0).to_numpy()
    beta = rng.uniform(0.6, 1.3)
    ret = beta * mkt + rng.normal(0, 0.017, n)

    # one or two dividends per year, usually in spring
    ex_idx = []
    for year in range(2020, 2025):
        if rng.random() < 0.15:
            continue
        month = rng.choice([4, 5, 5, 6])
        target = pd.Timestamp(year=year, month=month, day=int(rng.integers(1, 28)))
        ex_idx.append(int(days.searchsorted(target)))
    yields = np.array([rng.uniform(0.005, 0.07) for _ in ex_idx])

    for i, dy in zip(ex_idx, yields):
        ret[i - 15:i] += 0.35 * dy / 15                 # pre-ex run-up
        ret[i + 1:i + 11] -= 0.15 * dy / 10             # partial reversal

    price = 10 * np.exp(np.cumsum(np.log1p(ret)))
    dividends = []
    for i, dy in zip(ex_idx, yields):
        div = round(dy * price[i - 15], 4)
        price[i:] -= div * price[i:] / price[i]         # ex-date drop
        dividends.append((days[i], div))

    half_spread = rng.uniform(0.002, 0.012) * price
    bid, ask = price - half_spread, price + half_spread
    volume = rng.lognormal(10, 0.8, n)
    return pd.DataFrame({"Date": days, "Price": price, "Bid": bid, "Ask": ask,
                         "Volume": volume, "Turnover": volume * price}), dividends


def write_price_file(path: Path, ric: str, df: pd.DataFrame) -> None:
    """LSEG Price History layout: summary block, then the daily table (newest first)."""
    d = df[df["Date"] >= "2019-12-01"].iloc[::-1]
    summary = [[f"{ric} - Price History", None, None, None], [None] * 4,
               ["Summary", None, "Turnover", None],
               ["High", round(d["Price"].max(), 3), "High", round(d["Turnover"].max(), 2)],
               ["Low", round(d["Price"].min(), 3), "Low", round(d["Turnover"].min(), 2)],
               ["Avg", round(d["Price"].mean(), 3), "Avg", round(d["Turnover"].mean(), 2)],
               [None] * 4]
    header = ["Exchange Date", "Official Close Price", "Net", "%Chg", "Open", "Low", "High",
              "Volume", "Turnover", "Bid", "Ask"]
    table = pd.DataFrame({
        "Exchange Date": d["Date"].dt.date, "Official Close Price": d["Price"].round(4),
        "Net": None, "%Chg": None, "Open": None, "Low": None, "High": None,
        "Volume": d["Volume"].round(0), "Turnover": d["Turnover"].round(2),
        "Bid": d["Bid"].round(4), "Ask": d["Ask"].round(4),
    })
    rows = [r + [None] * (len(header) - len(r)) for r in summary] + [header] + table.values.tolist()
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def write_dividend_file(path: Path, ric: str, dividends) -> None:
    """LSEG Dividend History layout with dates as text (e.g. 13-Mar-2024)."""
    header = ["Ann. Date", "Ex-Date", "Market Ex-Date", "Pay Date", "Record Date",
              "Gross Amt (Unadj)", "Net Amt (Unadj)", "Currency"]
    fmt = lambda d: d.strftime("%d-%b-%Y")
    rows = [[f"{ric} - Dividend History"] + [None] * 7, [None] * 8, header]
    for ex, net in sorted(dividends, reverse=True):
        gross = round(net / (1 - 0.26), 4)
        rows.append([fmt(ex - pd.Timedelta(days=45)), fmt(ex), fmt(ex), fmt(ex + pd.Timedelta(days=2)),
                     fmt(ex + pd.Timedelta(days=1)), gross, net, "EUR"])
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=Path("example_data"))
    parser.add_argument("--n-stocks", type=int, default=25)
    parser.add_argument("--seed", type=int, default=2024)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    for sub in ("prices", "dividends", "factors"):
        (args.out / sub).mkdir(parents=True, exist_ok=True)

    days = calendar()
    factors = write_french_csvs(days, rng, args.out / "factors")
    for k in range(args.n_stocks):
        ric = f"SYN{k:02d}.MI"
        df, dividends = simulate_stock(days, factors, rng)
        write_price_file(args.out / "prices" / f"{ric}_PREZZO.xlsx", ric, df)
        write_dividend_file(args.out / "dividends" / f"{ric}_DIV.xlsx", ric, dividends)
    print(f"Synthetic data for {args.n_stocks} stocks written to {args.out.resolve()}")


if __name__ == "__main__":
    main()
