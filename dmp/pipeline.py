"""
End-to-end replication pipeline.

    raw LSEG + French data
        -> daily panel                 (panel.py)
        -> event-level dataset         (events.py,            eq. 4.1-4.3)
        -> strategy returns by cutoff  (strategy_returns.py,  Tables 5.1, 5.2, 5.5, 5.6)
        -> factor-model alphas         (alphas.py,            eq. 4.9, Tables 5.7, 5.8)
        -> event study                 (event_study.py,       Figures 5.9-5.12)
        -> liquidity                   (liquidity.py,         Section 5.1)

All outputs are written to `cfg.output_dir`:

    data/      intermediate datasets (daily panel, event-level dataset)
    results/   full numeric results (unrounded, with t-statistics and p-values)
    tables/    tables formatted as in the thesis, plus thesis_tables.xlsx
    figures/   event-study figures
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import alphas, event_study, liquidity, strategy_returns
from .config import Config
from .events import build_event_dataset
from .io_factors import load_factors
from .io_lseg import load_dividends, load_prices
from .panel import build_panel, trading_calendar

log = logging.getLogger(__name__)


def _dirs(cfg: Config) -> dict[str, Path]:
    out = {name: Path(cfg.output_dir) / name for name in ("data", "results", "tables", "figures")}
    for path in out.values():
        path.mkdir(parents=True, exist_ok=True)
    return out


def run(cfg: Config) -> dict[str, pd.DataFrame]:
    out = _dirs(cfg)

    # 1. Data --------------------------------------------------------------
    prices = load_prices(cfg.prices_dir)
    dividends = load_dividends(cfg.dividends_dir)
    factors = load_factors(cfg.factors_path, cfg.tidy_factors_in_percent)
    panel = build_panel(prices, dividends)
    panel.to_csv(out["data"] / "daily_panel.csv", index=False)

    # 2. Event-level dataset (eq. 4.1-4.3) --------------------------------
    events = build_event_dataset(panel, factors, trading_calendar(panel), cfg)
    if events.empty:
        raise RuntimeError("No events could be constructed: check the input data and sample period")
    events.to_csv(out["data"] / "events.csv", index=False)

    tables: dict[str, pd.DataFrame] = {}

    # 3. Strategy returns (Tables 5.1, 5.2, 5.5, 5.6) ----------------------
    for label, ret, exc, t_win, t_ann in [
        ("price", "CR", "CR_excess", "Table 5.1", "Table 5.2"),
        ("bidask", "CAR", "CAR_excess", "Table 5.5", "Table 5.6"),
    ]:
        res = strategy_returns.returns_by_cutoff(events, ret, exc, cfg)
        res.to_csv(out["results"] / f"returns_by_cutoff_{label}.csv", index=False)
        tables[t_win] = strategy_returns.format_window_table(res)
        tables[t_ann] = strategy_returns.format_annualized_table(res)

    # 4. Factor-model alphas (Tables 5.7, 5.8) -----------------------------
    alpha_price = alphas.alphas_by_cutoff(events, "CR_excess", cfg)
    alpha_price.to_csv(out["results"] / "alphas_by_cutoff_price.csv", index=False)
    tables["Table 5.7"] = alphas.format_alpha_table(alpha_price)
    tables["Table 5.8"] = alphas.format_annualized_alpha_table(alpha_price, "linear")

    # Robustness, not reported in the thesis: alphas of the bid-ask returns.
    alpha_ba = alphas.alphas_by_cutoff(events, "CAR_excess", cfg)
    alpha_ba.to_csv(out["results"] / "alphas_by_cutoff_bidask.csv", index=False)
    tables["Alphas bid-ask (robustness)"] = alphas.format_alpha_table(alpha_ba)

    # 5. Event study (Figures 5.9-5.12) ------------------------------------
    for label, min_yield, title, figs in [
        ("all", None, "All events", ("5_9", "5_10")),
        ("high_yield", cfg.event_yield_threshold,
         f"Net DY ≥ {100 * cfg.event_yield_threshold:.2f}%", ("5_11", "5_12")),
    ]:
        windows = event_study.event_windows(panel, cfg, min_yield)
        profile = event_study.average_profile(windows)
        windows.to_csv(out["results"] / f"event_study_windows_{label}.csv")
        profile.to_csv(out["results"] / f"event_study_profile_{label}.csv", index=False)
        log.info("Event study (%s): %d events", label, len(windows))
        if len(windows):
            event_study.plot_profile(profile, title,
                                     out["figures"] / f"figure_{figs[0]}_daily_returns_{label}.png",
                                     out["figures"] / f"figure_{figs[1]}_cumulative_returns_{label}.png")

    # 6. Liquidity ---------------------------------------------------------
    spreads = liquidity.daily_spreads(panel, cfg)
    by_stock = liquidity.liquidity_by_stock(spreads, prices, panel, cfg)
    by_stock.to_csv(out["results"] / "liquidity_by_stock.csv", index=False)
    tables["Liquidity"] = liquidity.liquidity_summary(spreads, by_stock)

    # 7. Export ------------------------------------------------------------
    with pd.ExcelWriter(out["tables"] / "thesis_tables.xlsx", engine="openpyxl") as xw:
        for name, table in tables.items():
            table.to_excel(xw, sheet_name=name[:31], index=False)
    for name, table in tables.items():
        slug = name.lower().replace(" ", "_").replace(".", "_").replace("(", "").replace(")", "")
        table.to_csv(out["tables"] / f"{slug}.csv", index=False)

    log.info("Done. Results written to %s", Path(cfg.output_dir).resolve())
    return {"panel": panel, "events": events, **tables}
