"""Unit tests for the core computations (run with `pytest`)."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from dmp.config import Config
from dmp.event_study import average_profile, event_windows
from dmp.events import build_event_dataset, compound
from dmp.io_factors import read_french_csv
from dmp.io_lseg import PriceFile, read_dividend_file, read_price_file
from dmp.inference import fit_ols, one_sided_pvalue
from dmp.panel import build_panel, trading_calendar
from dmp.strategy_returns import returns_by_cutoff

CFG = replace(Config(), sample_start="2020-01-01", sample_end="2020-12-31")


# --------------------------------------------------------------------- fixtures
@pytest.fixture
def toy():
    """One stock, 40 trading days, a dividend of 0.5 going ex on day 25."""
    dates = pd.bdate_range("2020-01-01", periods=40)
    price = 10 + 0.1 * np.arange(40)
    daily = pd.DataFrame({"Date": dates, "Price": price, "Bid": price - 0.05,
                          "Ask": price + 0.05, "Turnover": 1000.0})
    prices = [PriceFile("TOY.MI", daily, 1000.0)]
    dividends = pd.DataFrame({"Ticker": ["TOY.MI"], "ExDate": [dates[25]],
                              "DivNet": [0.5], "DivGross": [0.6]})
    factors = pd.DataFrame(0.001, index=dates, columns=["MKT_RF", "SMB", "HML", "RMW", "CMA", "UMD"])
    factors["RF"] = 0.0001
    return prices, dividends, factors, dates, price


# --------------------------------------------------------------------- events
def test_compound():
    assert compound([0.1, -0.1]) == pytest.approx(1.1 * 0.9 - 1)


def test_event_quantities_match_thesis_formulas(toy):
    prices, dividends, factors, dates, price = toy
    panel = build_panel(prices, dividends)
    ev = build_event_dataset(panel, factors, trading_calendar(panel), CFG)

    assert len(ev) == 1
    e = ev.iloc[0]
    assert e["EntryDate"] == dates[10] and e["ExitDate"] == dates[24]       # T-15, T-1
    assert e["CR"] == pytest.approx(price[24] / price[10] - 1)               # eq. 4.1
    assert e["CAR"] == pytest.approx((price[24] - 0.05) / (price[10] + 0.05) - 1)  # eq. 4.2
    assert e["NetDY"] == pytest.approx(0.5 / price[10])
    assert e["CFR_MKT_RF"] == pytest.approx(1.001 ** 15 - 1)                 # eq. 4.3
    assert e["CRF"] == pytest.approx(1.0001 ** 15 - 1)
    assert e["CR_excess"] == pytest.approx(e["CR"] - e["CRF"])


def test_factor_window_uses_market_calendar(toy):
    """A factor date on which the stock market is closed must not enter the window."""
    prices, dividends, factors, dates, _ = toy
    panel = build_panel(prices, dividends)
    calendar = trading_calendar(panel).delete(20)          # market closed on day 20
    factors.loc[dates[20], "MKT_RF"] = 0.5                 # would dominate the window if used
    ev = build_event_dataset(panel, factors, calendar, CFG)
    assert ev.iloc[0]["CFR_MKT_RF"] == pytest.approx(1.001 ** 15 - 1)


def test_event_without_enough_history_is_dropped(toy):
    prices, _, factors, dates, _ = toy
    dividends = pd.DataFrame({"Ticker": ["TOY.MI"], "ExDate": [dates[5]], "DivNet": [0.5], "DivGross": [0.6]})
    panel = build_panel(prices, dividends)
    assert build_event_dataset(panel, factors, trading_calendar(panel), CFG).empty


# --------------------------------------------------------------------- returns
def test_cutoffs_are_inclusive():
    events = pd.DataFrame({"NetDY": [0.0, 0.0025, 0.01], "CR": [0.01, 0.02, 0.03],
                           "CR_excess": [0.01, 0.02, 0.03]})
    t = returns_by_cutoff(events, "CR", "CR_excess", CFG).set_index("cutoff")
    assert t.loc[0.0025, "n_events"] == 2
    assert t.loc[0.0025, "mean"] == pytest.approx(0.025)
    assert t.loc[0.0025, "mean_ann_linear"] == pytest.approx(0.025 * 252 / 15)


# --------------------------------------------------------------------- OLS
def test_ols_matches_closed_form():
    """Independent check of the regression output against the textbook formulas."""
    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame({"x1": rng.normal(size=n), "x2": rng.normal(size=n)})
    e = rng.normal(scale=0.1, size=n) * (1 + np.abs(X["x1"]))
    y = 0.02 + 0.5 * X["x1"] - 0.3 * X["x2"] + e

    Xc = np.column_stack([np.ones(n), X.to_numpy()])
    xtx_inv = np.linalg.inv(Xc.T @ Xc)
    beta = xtx_inv @ Xc.T @ y.to_numpy()
    resid = y.to_numpy() - Xc @ beta
    se_classical = np.sqrt(np.diag(resid @ resid / (n - 3) * xtx_inv))
    meat = (Xc * resid[:, None] ** 2).T @ Xc
    se_hc1 = np.sqrt(np.diag(n / (n - 3) * xtx_inv @ meat @ xtx_inv))

    res = fit_ols(y, X)
    np.testing.assert_allclose(res.params.to_numpy(), beta)
    np.testing.assert_allclose(res.bse.to_numpy(), se_classical)
    assert list(res.params.index) == ["const", "x1", "x2"]

    res_hc1 = fit_ols(y, X, cov_type="HC1")
    np.testing.assert_allclose(res_hc1.params.to_numpy(), beta)
    np.testing.assert_allclose(res_hc1.bse.to_numpy(), se_hc1)


def test_one_sided_pvalue():
    assert one_sided_pvalue(0.5, 0.04) == pytest.approx(0.02)
    assert one_sided_pvalue(-0.5, 0.04) == pytest.approx(0.98)


# --------------------------------------------------------------------- event study
def test_cumulative_profile_is_cumsum_of_averages(toy):
    prices, dividends, _, _, price = toy
    panel = build_panel(prices, dividends)
    cfg = replace(CFG, event_pre_days=5, event_post_days=5)
    windows = event_windows(panel, cfg)
    profile = average_profile(windows)
    assert len(windows) == 1
    assert profile["t"].tolist() == list(range(-5, 6))
    assert profile.loc[profile["t"] == 0, "avg_return"].item() == pytest.approx(price[25] / price[24] - 1)
    np.testing.assert_allclose(profile["cum_avg_return"], profile["avg_return"].cumsum())


# --------------------------------------------------------------------- readers
def test_lseg_and_french_readers(tmp_path):
    from make_synthetic_data import (calendar, simulate_stock, write_dividend_file,
                                     write_french_csvs, write_price_file)
    rng = np.random.default_rng(1)
    days = calendar()
    factors = write_french_csvs(days, rng, tmp_path)
    df, divs = simulate_stock(days, factors, rng)
    write_price_file(tmp_path / "ABC.MI_PREZZO.xlsx", "ABC.MI", df)
    write_dividend_file(tmp_path / "ABC.MI_DIV.xlsx", "ABC.MI", divs)

    pf = read_price_file(tmp_path / "ABC.MI_PREZZO.xlsx")
    assert pf.ticker == "ABC.MI"
    assert pf.daily["Date"].is_monotonic_increasing
    assert pf.daily[["Price", "Bid", "Ask"]].notna().all().all()
    assert pf.summary_avg_turnover > 0

    d = read_dividend_file(tmp_path / "ABC.MI_DIV.xlsx")
    expected = {pd.Timestamp(x): v for x, v in divs}
    assert dict(zip(d["ExDate"], d["DivNet"])) == pytest.approx(expected)

    f = read_french_csv(tmp_path / "Europe_5_Factors_Daily.csv")
    assert list(f.columns) == ["MKT_RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert f["MKT_RF"].abs().median() < 0.05            # converted from percent
