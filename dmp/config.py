"""
Central configuration of the replication package.

Every parameter that affects the empirical results is defined here, so that the
analysis can be audited and modified in a single place. The default values
reproduce the specification used in the thesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def _default_cutoffs() -> tuple[float, ...]:
    """Net dividend-yield cutoffs: 0% to 5.5% in steps of 0.25% (in decimals)."""
    return tuple(float(x) for x in np.round(np.arange(0.0, 0.055 + 1e-9, 0.0025), 4))


@dataclass(frozen=True)
class Config:
    # ------------------------------------------------------------------ paths
    data_dir: Path = Path("data")
    output_dir: Path = Path("outputs")
    prices_subdir: str = "prices"        # LSEG price-history exports (<RIC>_PREZZO.xlsx)
    dividends_subdir: str = "dividends"  # LSEG dividend-history exports (<RIC>_DIV.xlsx)
    factors_subdir: str = "factors"      # Kenneth French daily European factors

    # If the factors are supplied as a single tidy file (Date + factor columns)
    # instead of the original Kenneth French CSVs, set this flag to state whether
    # that file is expressed in percent (as in the French library) or in decimals.
    tidy_factors_in_percent: bool = False

    # ----------------------------------------------------------- sample period
    sample_start: str = "2020-01-01"
    sample_end: str = "2024-12-31"

    # ------------------------------------------------------- strategy window
    # Holding window [T-15, T-1]: buy at the close of T-15, sell at the close
    # of T-1, where T is the ex-dividend date (eq. 4.1 in the thesis).
    window_days: int = 15
    trading_days_per_year: int = 252

    # Factor windows are built from the last `window_days` factor observations
    # strictly before the ex-date, searched within this many calendar days.
    factor_lookback_calendar_days: int = 30

    # ---------------------------------------------- cross-sectional analysis
    yield_cutoffs: tuple[float, ...] = field(default_factory=_default_cutoffs)
    min_events_for_regression: int = 10
    # "nonrobust" (classical OLS standard errors, as in the thesis) or "HC1"
    regression_cov_type: str = "nonrobust"

    # ---------------------------------------------------------- event study
    event_pre_days: int = 15
    event_post_days: int = 15
    event_yield_threshold: float = 0.0375
    # Keep only events whose full [-pre, +post] window is observed, so that
    # every event-time average is computed on the same set of events.
    event_complete_windows_only: bool = True

    # ------------------------------------------------------------ liquidity
    # Quoted spreads outside [0, max_spread_bps] are treated as data errors.
    max_spread_bps: float = 2000.0

    # ------------------------------------------------------- derived values
    @property
    def annualization_factor(self) -> float:
        """Number of non-overlapping 15-day windows in a year (252 / 15 = 16.8)."""
        return self.trading_days_per_year / self.window_days

    @property
    def prices_dir(self) -> Path:
        return Path(self.data_dir) / self.prices_subdir

    @property
    def dividends_dir(self) -> Path:
        return Path(self.data_dir) / self.dividends_subdir

    @property
    def factors_path(self) -> Path:
        return Path(self.data_dir) / self.factors_subdir


# Factor models estimated in Section 5.2 (eq. 4.9). Keys are the labels used in
# the output tables; values are the cumulative-factor regressors.
FACTOR_MODELS: dict[str, list[str]] = {
    "CAPM": ["MKT_RF"],
    "FF3": ["MKT_RF", "SMB", "HML"],
    "C4F": ["MKT_RF", "SMB", "HML", "UMD"],
    "FF5": ["MKT_RF", "SMB", "HML", "RMW", "CMA"],
}

FACTOR_COLUMNS: list[str] = ["MKT_RF", "SMB", "HML", "RMW", "CMA", "UMD", "RF"]
