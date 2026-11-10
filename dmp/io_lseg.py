"""
Readers for the LSEG Workspace (formerly Refinitiv Eikon) Excel exports.

Two kinds of files are used, one pair per stock, named after the stock's RIC:

* ``<RIC>_PREZZO.xlsx``  - "Price History" export: a summary block at the top
  (which contains the average daily turnover) followed by the daily table with
  columns such as ``Exchange Date``, ``Official Close Price``, ``Bid``, ``Ask``.
* ``<RIC>_DIV.xlsx``     - "Dividend History" export with columns such as
  ``Ex-Date``, ``Gross Amt (Unadj)``, ``Net Amt (Unadj)``.

LSEG exports place a variable number of title rows above the actual table, so
each reader locates the header row by searching for the expected column names.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

PRICE_FILE_SUFFIXES = ("_PREZZO.xlsx", "_PRICE.xlsx")
DIVIDEND_FILE_SUFFIXES = ("_DIVIDEND.xlsx", "_DIV.xlsx")

# Column names in the LSEG exports (matched case-insensitively) -> internal names
PRICE_COLUMNS = {
    "exchange date": "Date",
    "official close price": "Price",
    "bid": "Bid",
    "ask": "Ask",
    "turnover": "Turnover",
}
DIVIDEND_COLUMNS = {
    "ann. date": "AnnDate",
    "ex-date": "ExDate",
    "pay date": "PayDate",
    "record date": "RecordDate",
    "gross amt (unadj)": "DivGross",
    "net amt (unadj)": "DivNet",
}
DIVIDEND_DATE_FORMAT = "%d-%b-%Y"  # e.g. "13-Mar-2024"


@dataclass
class PriceFile:
    ticker: str
    daily: pd.DataFrame             # Date, Price, Bid, Ask, Turnover
    summary_avg_turnover: float     # "Turnover -> Avg" in the summary block (NaN if absent)


# --------------------------------------------------------------------------- helpers
def ticker_from_filename(path: Path, suffixes: tuple[str, ...]) -> str:
    """Return the RIC encoded in a file name, e.g. 'MARR.MI_PREZZO.xlsx' -> 'MARR.MI'."""
    name = path.name
    for suffix in suffixes:
        if name.upper().endswith(suffix.upper()):
            return name[: -len(suffix)]
    return path.stem


def list_excel_files(directory: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """List the LSEG exports in `directory` (temporary '~$' Excel files are skipped)."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")
    files = [
        p for p in sorted(directory.iterdir())
        if p.suffix.lower() == ".xlsx"
        and not p.name.startswith("~$")
        and any(p.name.upper().endswith(s.upper()) for s in suffixes)
    ]
    if not files:
        raise FileNotFoundError(f"No files ending in {suffixes} found in {directory}")
    return files


def _normalise(value) -> str:
    return str(value).strip().lower() if pd.notna(value) else ""


def _find_header_row(raw: pd.DataFrame, required: set[str], max_rows: int = 200) -> int | None:
    """Index of the first row that contains all `required` labels (case-insensitive)."""
    for i in range(min(max_rows, len(raw))):
        labels = {_normalise(v) for v in raw.iloc[i].tolist()}
        if required.issubset(labels):
            return i
    return None


def _extract_table(raw: pd.DataFrame, header_row: int, column_map: dict[str, str]) -> pd.DataFrame:
    """Slice the table below `header_row` and keep/rename the columns in `column_map`."""
    header = [_normalise(v) for v in raw.iloc[header_row].tolist()]
    positions = {}
    for j, label in enumerate(header):
        if label in column_map and column_map[label] not in positions:
            positions[column_map[label]] = j
    table = raw.iloc[header_row + 1:, list(positions.values())].copy()
    table.columns = list(positions.keys())
    return table.dropna(how="all").reset_index(drop=True)


def _to_datetime(series: pd.Series, fmt: str | None = None) -> pd.Series:
    """Parse dates stored either as Excel dates or as text (optionally with `fmt`)."""
    parsed = pd.to_datetime(series, format=fmt, errors="coerce") if fmt else pd.Series(pd.NaT, index=series.index)
    remaining = parsed.isna() & series.notna()
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(series[remaining], errors="coerce")
    return parsed.dt.normalize()


def _summary_value(raw: pd.DataFrame, block_label: str, stat_label: str, max_rows: int = 200) -> float:
    """
    Read a statistic from the summary block of a Price History export.

    The block has the form   | Turnover |        |
                             | ...      | ...    |
                             | Avg      | 1.2e6  |
    i.e. the statistic label sits in the same column as the block label and its
    value in the column to the right.
    """
    for i in range(min(max_rows, len(raw))):
        for j in range(raw.shape[1]):
            if _normalise(raw.iat[i, j]) == block_label:
                for r in range(i + 1, min(i + 12, len(raw))):
                    if _normalise(raw.iat[r, j]) == stat_label and j + 1 < raw.shape[1]:
                        return pd.to_numeric(raw.iat[r, j + 1], errors="coerce")
                return np.nan
    return np.nan


# --------------------------------------------------------------------------- readers
def read_price_file(path: Path) -> PriceFile:
    """Read one LSEG Price History export."""
    ticker = ticker_from_filename(path, PRICE_FILE_SUFFIXES)
    raw = pd.read_excel(path, header=None)

    header_row = _find_header_row(raw, {"exchange date", "official close price"})
    if header_row is None:
        raise ValueError(f"{path.name}: header with 'Exchange Date' and 'Official Close Price' not found")

    daily = _extract_table(raw, header_row, PRICE_COLUMNS)
    daily["Date"] = _to_datetime(daily["Date"])
    for col in ("Price", "Bid", "Ask", "Turnover"):
        daily[col] = pd.to_numeric(daily[col], errors="coerce") if col in daily else np.nan

    daily = daily.dropna(subset=["Date", "Price"]).sort_values("Date")
    n_dup = daily["Date"].duplicated().sum()
    if n_dup:
        log.warning("%s: %d duplicated dates dropped (last observation kept)", ticker, n_dup)
        daily = daily.drop_duplicates("Date", keep="last")

    return PriceFile(
        ticker=ticker,
        daily=daily[["Date", "Price", "Bid", "Ask", "Turnover"]].reset_index(drop=True),
        summary_avg_turnover=_summary_value(raw, "turnover", "avg"),
    )


def read_dividend_file(path: Path) -> pd.DataFrame:
    """Read one LSEG Dividend History export (one row per dividend)."""
    ticker = ticker_from_filename(path, DIVIDEND_FILE_SUFFIXES)
    raw = pd.read_excel(path, header=None)

    header_row = _find_header_row(raw, {"ex-date", "gross amt (unadj)"})
    if header_row is None:
        raise ValueError(f"{path.name}: header with 'Ex-Date' and 'Gross Amt (Unadj)' not found")

    divs = _extract_table(raw, header_row, DIVIDEND_COLUMNS)
    for col in ("AnnDate", "ExDate", "PayDate", "RecordDate"):
        if col in divs:
            divs[col] = _to_datetime(divs[col], DIVIDEND_DATE_FORMAT)
    for col in ("DivGross", "DivNet"):
        divs[col] = pd.to_numeric(divs[col], errors="coerce") if col in divs else np.nan

    divs = divs.dropna(subset=["ExDate"])
    divs.insert(0, "Ticker", ticker)
    return divs.reset_index(drop=True)


def load_prices(directory: Path) -> list[PriceFile]:
    files = list_excel_files(directory, PRICE_FILE_SUFFIXES)
    log.info("Reading %d price files from %s", len(files), directory)
    return [read_price_file(p) for p in files]


def load_dividends(directory: Path) -> pd.DataFrame:
    files = list_excel_files(directory, DIVIDEND_FILE_SUFFIXES)
    log.info("Reading %d dividend files from %s", len(files), directory)
    frames = [read_dividend_file(p) for p in files]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
