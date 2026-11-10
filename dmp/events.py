"""
Event-level dataset: one observation per dividend (stock i, ex-date T).

For each event the following quantities are computed (equation numbers refer
to Chapter 4 of the thesis; t is measured in trading days, t = 0 at the ex-date):

    CR_i,T   = P_i,T-1 / P_i,T-15 - 1                     price return       (4.1)
    CAR_i,T  = Bid_i,T-1 / Ask_i,T-15 - 1                 bid-ask return     (4.2)
    CFR_k,T  = prod_{t=T-15}^{T-1} (1 + F_k,t) - 1        cumulative factor  (4.3)
    CRF_T    = prod_{t=T-15}^{T-1} (1 + rf_t) - 1         cumulative risk-free rate
    DY_i,T   = D^net_i,T / P_i,T-15                       net dividend yield

The yield is measured with the price at T-15 so that the signal is known when
the position is opened and is not mechanically affected by the run-up.

Factor windows use the trading days of the STAR panel: the cumulative factors
are compounded over the last 15 factor observations dated strictly before the
ex-date, restricted to days on which the Italian market was open.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import FACTOR_COLUMNS, Config

log = logging.getLogger(__name__)

FACTOR_REGRESSORS = [c for c in FACTOR_COLUMNS if c != "RF"]


def compound(returns: pd.Series | np.ndarray) -> float:
    """Cumulative return over a window: prod(1 + r) - 1."""
    return float(np.prod(1.0 + np.asarray(returns, dtype=float)) - 1.0)


def cumulative_factors(factors: pd.DataFrame, ex_date: pd.Timestamp, cfg: Config) -> dict[str, float] | None:
    """Cumulative factor returns (CFR) and risk-free rate (CRF) over the event window."""
    start = ex_date - pd.Timedelta(days=cfg.factor_lookback_calendar_days)
    window = factors.loc[(factors.index >= start) & (factors.index < ex_date)].tail(cfg.window_days)
    if len(window) < cfg.window_days:
        return None
    out = {f"CFR_{k}": compound(window[k]) for k in FACTOR_REGRESSORS}
    out["CRF"] = compound(window["RF"])
    return out


def build_event_dataset(panel: pd.DataFrame, factors: pd.DataFrame,
                        calendar: pd.DatetimeIndex, cfg: Config) -> pd.DataFrame:
    """Return the event-level dataset used for Tables 5.1-5.8."""
    w = cfg.window_days
    start, end = pd.Timestamp(cfg.sample_start), pd.Timestamp(cfg.sample_end)
    factors = factors.loc[factors.index.isin(calendar)]

    rows, skipped = [], {"short_history": 0, "no_factor_window": 0}
    for ticker, df in panel.groupby("Ticker", sort=True):
        df = df.reset_index(drop=True)
        for i in df.index[df["IsExDate"]]:
            ex_date = df.at[i, "Date"]
            if not (start <= ex_date <= end):
                continue
            if i < w:
                skipped["short_history"] += 1
                continue

            entry, exit_ = df.loc[i - w], df.loc[i - 1]          # rows T-15 and T-1
            cfr = cumulative_factors(factors, ex_date, cfg)
            if cfr is None:
                skipped["no_factor_window"] += 1
                continue

            cr = exit_["Price"] / entry["Price"] - 1.0
            valid_quotes = entry["Ask"] > 0 and exit_["Bid"] > 0
            car = exit_["Bid"] / entry["Ask"] - 1.0 if valid_quotes else np.nan

            rows.append({
                "Ticker": ticker,
                "ExDate": ex_date,
                "EntryDate": entry["Date"],
                "ExitDate": exit_["Date"],
                "PriceEntry": entry["Price"],
                "PriceExit": exit_["Price"],
                "DivNet": df.at[i, "DivNet"],
                "DivGross": df.at[i, "DivGross"],
                "NetDY": df.at[i, "DivNet"] / entry["Price"],
                "GrossDY": df.at[i, "DivGross"] / entry["Price"],
                "CR": cr,
                "CAR": car,
                **cfr,
                "CR_excess": cr - cfr["CRF"],
                "CAR_excess": car - cfr["CRF"],
            })

    events = pd.DataFrame(rows)
    log.info("Events: %d retained (%d with fewer than %d prior trading days, %d without a full factor window)",
             len(events), skipped["short_history"], w, skipped["no_factor_window"])
    if not events.empty:
        log.info("Average net dividend yield: %.2f%%; events with bid/ask quotes: %d",
                 100 * events["NetDY"].mean(), int(events["CAR"].notna().sum()))
    return events
