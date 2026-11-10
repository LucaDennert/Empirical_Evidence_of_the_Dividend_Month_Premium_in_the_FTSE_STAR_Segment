"""
Event-time profile of returns around the ex-date (Section 5.3, Figures 5.9-5.12).

Event time t is measured in trading days, with t = 0 at the ex-date and
t in [-15, +15]. For every event the daily simple return r_i,t = P_t / P_t-1 - 1
is collected; the cross-sectional average return at each t and its cumulative
sum are then computed:

    AR_t = (1 / N) * sum_i r_i,t          CAR_t = sum_{s <= t} AR_s

Returns are raw price returns (dividends are not added back), so the ex-date
drop reflects the dividend adjustment of the price. By default only events
with a complete window are used, so that every AR_t is averaged over the same
events.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import Config

log = logging.getLogger(__name__)


def event_windows(panel: pd.DataFrame, cfg: Config, min_yield: float | None = None) -> pd.DataFrame:
    """Matrix of daily returns: one row per event, one column per event day t."""
    pre, post, w = cfg.event_pre_days, cfg.event_post_days, cfg.window_days
    start, end = pd.Timestamp(cfg.sample_start), pd.Timestamp(cfg.sample_end)
    days = list(range(-pre, post + 1))

    rows, index = [], []
    for ticker, df in panel.groupby("Ticker", sort=True):
        df = df.reset_index(drop=True)
        returns = df["Return"].to_numpy()
        for i in df.index[df["IsExDate"]]:
            ex_date = df.at[i, "Date"]
            if not (start <= ex_date <= end):
                continue
            if min_yield is not None:
                if i < w or df.at[i, "DivNet"] / df.at[i - w, "Price"] < min_yield:
                    continue
            window = [returns[i + t] if 0 <= i + t < len(df) else np.nan for t in days]
            rows.append(window)
            index.append((ticker, ex_date))

    mat = pd.DataFrame(rows, columns=days,
                       index=pd.MultiIndex.from_tuples(index, names=["Ticker", "ExDate"]))
    if cfg.event_complete_windows_only:
        mat = mat.dropna()
    mat.columns.name = "t"
    return mat


def average_profile(windows: pd.DataFrame) -> pd.DataFrame:
    """Average return, cumulative average return and number of events at each t."""
    ar = windows.mean(axis=0)
    return pd.DataFrame({
        "t": windows.columns.astype(int),
        "avg_return": ar.to_numpy(),
        "cum_avg_return": ar.cumsum().to_numpy(),
        "n_events": windows.count(axis=0).to_numpy(),
    })


def plot_profile(profile: pd.DataFrame, title: str, path_daily, path_cumulative) -> None:
    """Bar chart of daily average returns and line chart of their cumulative sum (in %)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    color, ink, grid = "#2a78d6", "#52514e", "#e4e3df"
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": ink, "axes.labelcolor": ink,
                         "xtick.color": ink, "ytick.color": ink})

    def _axes():
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.axhline(0, color=ink, lw=0.8)
        ax.axvline(0, color=ink, lw=0.8, ls="--")
        ax.grid(axis="y", color=grid, lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_xlabel("Event day t (trading days, t = 0 ex-date)")
        ax.set_xticks(profile["t"][::3])
        return fig, ax

    n = int(profile["n_events"].min())
    fig, ax = _axes()
    ax.bar(profile["t"], 100 * profile["avg_return"], width=0.7, color=color)
    ax.set_ylabel("Average daily return (%)")
    ax.set_title(f"{title}: average daily price returns (N = {n})", loc="left")
    fig.tight_layout()
    fig.savefig(path_daily, dpi=200)
    plt.close(fig)

    fig, ax = _axes()
    ax.plot(profile["t"], 100 * profile["cum_avg_return"], color=color, lw=2, marker="o", ms=4)
    ax.set_ylabel("Cumulative average return (%)")
    ax.set_title(f"{title}: cumulative average price returns (N = {n})", loc="left")
    fig.tight_layout()
    fig.savefig(path_cumulative, dpi=200)
    plt.close(fig)
