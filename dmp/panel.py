"""
Construction of the daily stock panel.

For every stock, daily closing prices (and bid/ask quotes) are merged with its
dividend history. Each trading day carries the net and gross dividend going
ex on that day (zero otherwise) and an ex-date indicator.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .io_lseg import PriceFile

log = logging.getLogger(__name__)

PANEL_COLUMNS = ["Ticker", "Date", "Price", "Bid", "Ask", "Turnover",
                 "Return", "DivNet", "DivGross", "IsExDate"]


def build_panel(prices: list[PriceFile], dividends: pd.DataFrame) -> pd.DataFrame:
    """
    Return a long panel (one row per stock and trading day) sorted by ticker and date.

    Several dividends of the same stock with the same ex-date are summed.
    Dividends whose ex-date is not a trading day in the price file cannot be
    matched to a price and are reported in the log.
    """
    if dividends.empty:
        div_by_day = pd.DataFrame(columns=["Ticker", "Date", "DivNet", "DivGross"])
    else:
        div_by_day = (
            dividends.groupby(["Ticker", "ExDate"], as_index=False)[["DivNet", "DivGross"]]
            .sum(min_count=1)
            .rename(columns={"ExDate": "Date"})
        )

    frames = []
    for pf in prices:
        df = pf.daily.copy()
        df.insert(0, "Ticker", pf.ticker)
        df["Return"] = df["Price"].pct_change()

        divs = div_by_day[div_by_day["Ticker"] == pf.ticker]
        df = df.merge(divs[["Date", "DivNet", "DivGross"]], on="Date", how="left", indicator=True)
        df["IsExDate"] = df.pop("_merge").eq("both")
        df[["DivNet", "DivGross"]] = df[["DivNet", "DivGross"]].fillna(0.0)

        unmatched = set(divs["Date"]) - set(pf.daily["Date"])
        if unmatched:
            log.warning("%s: %d ex-date(s) not found among trading days and ignored: %s",
                        pf.ticker, len(unmatched), ", ".join(str(d.date()) for d in sorted(unmatched)))
        frames.append(df)

    panel = pd.concat(frames, ignore_index=True)
    panel["IsExDate"] = panel["IsExDate"].astype(bool)

    without_prices = set(div_by_day["Ticker"]) - set(panel["Ticker"])
    if without_prices:
        log.warning("Dividend files without a matching price file: %s", sorted(without_prices))

    log.info("Panel: %d stocks, %d stock-days, %d ex-dates",
             panel["Ticker"].nunique(), len(panel), int(panel["IsExDate"].sum()))
    return panel[PANEL_COLUMNS].sort_values(["Ticker", "Date"]).reset_index(drop=True)


def trading_calendar(panel: pd.DataFrame) -> pd.DatetimeIndex:
    """All dates on which at least one stock in the panel has a closing price."""
    return pd.DatetimeIndex(np.sort(panel["Date"].unique()))
