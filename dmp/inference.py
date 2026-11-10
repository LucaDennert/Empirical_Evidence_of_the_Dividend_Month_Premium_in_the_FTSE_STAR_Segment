"""
Statistical inference helpers: OLS estimation and one-sided tests.

Regressions are estimated with statsmodels. With ``cov_type="nonrobust"``
standard errors are the classical OLS ones and p-values use the t
distribution; with ``cov_type="HC1"`` standard errors are
heteroskedasticity-robust (White, with small-sample correction) and p-values
use the normal distribution, as is the statsmodels default for robust
covariances.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def fit_ols(y: pd.Series, X: pd.DataFrame, cov_type: str = "nonrobust"):
    """Regress `y` on a constant and `X`, dropping rows with missing values."""
    data = pd.concat([y.rename("_y"), X], axis=1).dropna()
    exog = sm.add_constant(data.drop(columns="_y"), has_constant="add")
    return sm.OLS(data["_y"], exog).fit(cov_type=cov_type)


def one_sided_pvalue(estimate: float, p_two_sided: float) -> float:
    """p-value of H0: beta <= 0 against H1: beta > 0, from the two-sided p-value."""
    if np.isnan(p_two_sided):
        return np.nan
    return p_two_sided / 2 if estimate >= 0 else 1 - p_two_sided / 2


def significance_stars(p: float) -> str:
    """*** p <= 0.01, ** p <= 0.05, * p <= 0.10."""
    if p is None or np.isnan(p):
        return ""
    return "***" if p <= 0.01 else "**" if p <= 0.05 else "*" if p <= 0.10 else ""
