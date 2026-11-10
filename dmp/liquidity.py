"""
Liquidity of the FTSE STAR segment (Section 5.1): quoted bid-ask spreads and
average daily turnover.

    spread_bps = (Ask - Bid) / ((Ask + Bid) / 2) * 10,000

Days with non-positive quotes or spreads outside [0, max_spread_bps] are
discarded as data errors. Average daily turnover is taken from the summary
block of the LSEG Price History export ("Turnover -> Avg"); if absent, the
mean of the daily Turnover column over the sample period is used.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config
from .io_lseg import PriceFile


def daily_spreads(panel: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Daily quoted spread (bps) for every stock-day with valid quotes in the sample period."""
    d = panel[(panel["Date"] >= cfg.sample_start) & (panel["Date"] <= cfg.sample_end)]
    d = d[(d["Bid"] > 0) & (d["Ask"] > 0)].copy()
    mid = (d["Ask"] + d["Bid"]) / 2
    d["spread_bps"] = (d["Ask"] - d["Bid"]) / mid * 1e4
    d = d[(d["spread_bps"] >= 0) & (d["spread_bps"] <= cfg.max_spread_bps)]
    return d[["Ticker", "Date", "Bid", "Ask", "spread_bps"]].reset_index(drop=True)


def liquidity_by_stock(spreads: pd.DataFrame, prices: list[PriceFile], panel: pd.DataFrame,
                       cfg: Config) -> pd.DataFrame:
    """Per-stock spread statistics and average daily turnover."""
    stats = spreads.groupby("Ticker")["spread_bps"].agg(
        n_days="count", mean_spread_bps="mean", median_spread_bps="median",
        p95_spread_bps=lambda s: s.quantile(0.95), max_spread_bps="max",
    )

    in_sample = panel[(panel["Date"] >= cfg.sample_start) & (panel["Date"] <= cfg.sample_end)]
    daily_turnover = in_sample.groupby("Ticker")["Turnover"].mean()
    turnover = []
    for pf in prices:
        if pd.notna(pf.summary_avg_turnover):
            turnover.append((pf.ticker, pf.summary_avg_turnover, "summary block"))
        elif pd.notna(daily_turnover.get(pf.ticker, np.nan)):
            turnover.append((pf.ticker, daily_turnover[pf.ticker], "daily column"))
        else:
            turnover.append((pf.ticker, np.nan, "not available"))
    turnover = pd.DataFrame(turnover, columns=["Ticker", "avg_daily_turnover", "turnover_source"])

    return turnover.merge(stats.reset_index(), on="Ticker", how="left")[
        ["Ticker", "n_days", "mean_spread_bps", "median_spread_bps", "p95_spread_bps",
         "max_spread_bps", "avg_daily_turnover", "turnover_source"]
    ]


def liquidity_summary(spreads: pd.DataFrame, by_stock: pd.DataFrame) -> pd.DataFrame:
    """Segment-level figures, both pooled over stock-days and averaged across stocks."""
    rows = [
        ("Mean spread, pooled stock-days (bps)", round(spreads["spread_bps"].mean(), 1)),
        ("Median spread, pooled stock-days (bps)", round(spreads["spread_bps"].median(), 1)),
        ("Mean of per-stock mean spreads (bps)", round(by_stock["mean_spread_bps"].mean(), 1)),
        ("Median of per-stock median spreads (bps)", round(by_stock["median_spread_bps"].median(), 1)),
        ("Mean of per-stock average daily turnover (EUR)", round(by_stock["avg_daily_turnover"].mean(), 2)),
        ("Stocks with valid quotes", int(by_stock["n_days"].gt(0).sum())),
        ("Stock-days with valid quotes", int(len(spreads))),
    ]
    return pd.DataFrame({"Statistic": [r[0] for r in rows], "Value": pd.Series([r[1] for r in rows], dtype=object)})
