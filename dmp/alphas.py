"""
Factor-model alphas of the pre-ex-date returns (Section 5.2).

For each dividend-yield cutoff and each model in `FACTOR_MODELS`, the excess
window return of every event is regressed on the cumulative factors of the
same window (eq. 4.9):

    CR_i,T - CRF_T = alpha + sum_k beta_k * CFR_k,T + e_i,T

A positive and significant alpha (one-sided test, H1: alpha > 0) indicates a
pre-ex-date return that is not explained by exposure to the factors.

Annualised alphas (Table 5.8) are reported both linearly (16.8 * alpha, as in
the thesis) and with compounding ((1 + alpha)^16.8 - 1).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import FACTOR_MODELS, Config
from .inference import fit_ols, one_sided_pvalue, significance_stars
from .strategy_returns import YIELD_TOLERANCE

log = logging.getLogger(__name__)


def alphas_by_cutoff(events: pd.DataFrame, excess_col: str, cfg: Config) -> pd.DataFrame:
    """Long table: one row per (cutoff, model) with alpha, its inference and the fit."""
    regressors = sorted({f for factors in FACTOR_MODELS.values() for f in factors})
    data = events.dropna(subset=[excess_col, "NetDY"] + [f"CFR_{f}" for f in regressors])
    a = cfg.annualization_factor

    rows = []
    for cutoff in cfg.yield_cutoffs:
        sub = data[data["NetDY"] >= cutoff - YIELD_TOLERANCE]
        for model, factors in FACTOR_MODELS.items():
            row = {"cutoff": cutoff, "model": model, "n_events": len(sub)}
            if len(sub) < cfg.min_events_for_regression:
                rows.append(row)
                continue
            X = sub[[f"CFR_{f}" for f in factors]]
            res = fit_ols(sub[excess_col], X, cov_type=cfg.regression_cov_type)
            alpha = res.params["const"]
            row.update({
                "alpha": alpha,
                "se_alpha": res.bse["const"],
                "t_alpha": res.tvalues["const"],
                "p_alpha_one_sided": one_sided_pvalue(alpha, res.pvalues["const"]),
                "alpha_ann_linear": a * alpha,
                "alpha_ann_compound": (1 + alpha) ** a - 1,
                "r2": res.rsquared,
                "r2_adj": res.rsquared_adj,
                **{f"beta_{f}": res.params[f"CFR_{f}"] for f in factors},
            })
            rows.append(row)

    out = pd.DataFrame(rows)
    for col in ("alpha", "se_alpha", "t_alpha", "p_alpha_one_sided",
                "alpha_ann_linear", "alpha_ann_compound", "r2", "r2_adj"):
        if col not in out:
            out[col] = np.nan
    return out


def _wide(alphas: pd.DataFrame, value: pd.Series) -> pd.DataFrame:
    table = alphas.assign(value=value).pivot(index=["cutoff", "n_events"], columns="model", values="value")
    table = table[list(FACTOR_MODELS)].reset_index()
    table.insert(0, "Cutoff DivYield (%)", (100 * table.pop("cutoff")).round(2))
    table = table.rename(columns={"n_events": "N events", **{m: f"{m} (%)" for m in FACTOR_MODELS}})
    table.columns.name = None
    return table


def format_alpha_table(alphas: pd.DataFrame) -> pd.DataFrame:
    """Layout of Table 5.7: window alphas in percent with significance stars."""
    labels = [f"{100 * a:.2f}{significance_stars(p)}" if pd.notna(a) else "-"
              for a, p in zip(alphas["alpha"], alphas["p_alpha_one_sided"])]
    return _wide(alphas, pd.Series(labels, index=alphas.index))


def format_annualized_alpha_table(alphas: pd.DataFrame, method: str = "linear") -> pd.DataFrame:
    """Layout of Table 5.8: annualised alphas in percent (no stars)."""
    return _wide(alphas, (100 * alphas[f"alpha_ann_{method}"]).round(3))
