"""
Returns of the pre-ex-date strategy by dividend-yield cutoff (Section 5.1).

For each cutoff c, the sample contains all events with NetDY >= c. The
strategy return of an event is either the price return CR (Tables 5.1-5.2) or
the return net of the quoted spread CAR, buying at the ask and selling at the
bid (Tables 5.5-5.6).

Reported statistics, over the 15-day window:
    mean, standard deviation (ddof = 1), Sharpe ratio = mean / std of the
    return in excess of the cumulative risk-free rate, and the p-value of a
    right-tailed one-sample t-test (H0: mean <= 0).

Annualisation with A = 252 / 15 = 16.8 non-overlapping windows per year:
    linear mean = A * mean,  compound mean = (1 + mean)^A - 1,
    std = sqrt(A) * std,     Sharpe = sqrt(A) * Sharpe.
These figures assume i.i.d., non-overlapping windows and are illustrative only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .config import Config
from .inference import significance_stars

YIELD_TOLERANCE = 1e-9  # events exactly at a cutoff are included


def returns_by_cutoff(events: pd.DataFrame, return_col: str, excess_col: str, cfg: Config) -> pd.DataFrame:
    """Numeric summary table, one row per dividend-yield cutoff."""
    data = events.dropna(subset=[return_col, excess_col, "NetDY"])
    a = cfg.annualization_factor
    rows = []
    for cutoff in cfg.yield_cutoffs:
        sub = data[data["NetDY"] >= cutoff - YIELD_TOLERANCE]
        r, x = sub[return_col], sub[excess_col]
        n = len(sub)
        mean = r.mean() if n else np.nan
        std = r.std(ddof=1) if n > 1 else np.nan
        sharpe = x.mean() / x.std(ddof=1) if n > 1 and x.std(ddof=1) > 0 else np.nan
        p = stats.ttest_1samp(r, 0.0, alternative="greater").pvalue if n > 1 else np.nan
        rows.append({
            "cutoff": cutoff,
            "n_events": n,
            "mean": mean,
            "std": std,
            "sharpe": sharpe,
            "t_stat": mean / (std / np.sqrt(n)) if n > 1 and std > 0 else np.nan,
            "p_one_sided": p,
            "mean_ann_linear": a * mean,
            "mean_ann_compound": (1 + mean) ** a - 1,
            "std_ann": np.sqrt(a) * std,
            "sharpe_ann": np.sqrt(a) * sharpe,
        })
    return pd.DataFrame(rows)


def format_window_table(t: pd.DataFrame) -> pd.DataFrame:
    """Layout of Tables 5.1 / 5.5 (percentages, stars on the mean)."""
    return pd.DataFrame({
        "Cutoff DivYield (%)": (100 * t["cutoff"]).round(2),
        "N events": t["n_events"],
        "AvgReturn 15d (%)": [f"{100 * m:.3f}{significance_stars(p)}" if pd.notna(m) else ""
                              for m, p in zip(t["mean"], t["p_one_sided"])],
        "StdDev 15d (%)": (100 * t["std"]).round(3),
        "Sharpe 15d": t["sharpe"].round(3),
    })


def format_annualized_table(t: pd.DataFrame) -> pd.DataFrame:
    """Layout of Tables 5.2 / 5.6."""
    return pd.DataFrame({
        "Cutoff DivYield (%)": (100 * t["cutoff"]).round(2),
        "N events": t["n_events"],
        "AvgReturn (lin. ann., %)": (100 * t["mean_ann_linear"]).round(3),
        "AvgReturn (comp. ann., %)": (100 * t["mean_ann_compound"]).round(3),
        "StdDev (ann., %)": (100 * t["std_ann"]).round(3),
        "Sharpe (ann.)": t["sharpe_ann"].round(3),
    })
