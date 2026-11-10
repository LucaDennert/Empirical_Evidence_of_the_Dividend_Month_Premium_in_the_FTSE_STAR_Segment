"""
Reader for the daily European factors from the Kenneth R. French Data Library.

Two files are required (download links in the README):

* ``Europe_5_Factors_Daily.csv``   - Mkt-RF, SMB, HML, RMW, CMA, RF
* ``Europe_Mom_Factor_Daily.csv``  - WML (momentum, labelled UMD in the thesis)

Both are distributed as CSV files with a few lines of text above the data and
returns expressed in percent. They are parsed directly, so no manual cleaning
is needed. Alternatively, a single tidy file (CSV or XLSX) with a ``Date``
column and the factor columns can be supplied.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

import pandas as pd

from .config import FACTOR_COLUMNS

log = logging.getLogger(__name__)

RENAME = {"MKT-RF": "MKT_RF", "MKT_RF": "MKT_RF", "WML": "UMD", "MOM": "UMD", "UMD": "UMD",
          "SMB": "SMB", "HML": "HML", "RMW": "RMW", "CMA": "CMA", "RF": "RF"}
_DATE_LINE = re.compile(r"^\s*\d{8}\s*,")


def read_french_csv(path: Path) -> pd.DataFrame:
    """
    Parse a daily file from the French Data Library.

    The data block starts at the first line beginning with a YYYYMMDD date; the
    line just above it holds the column names. Values are converted from
    percent to decimals.
    """
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    first = next((i for i, line in enumerate(lines) if _DATE_LINE.match(line)), None)
    if first is None or first == 0:
        raise ValueError(f"{path.name}: no daily data block found")
    last = first
    while last < len(lines) and _DATE_LINE.match(lines[last]):
        last += 1

    block = "\n".join([lines[first - 1]] + lines[first:last])
    df = pd.read_csv(io.StringIO(block), skipinitialspace=True)
    df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"].astype(str).str.strip(), format="%Y%m%d")
    df = df.set_index("Date")
    df.columns = [RENAME.get(c.strip().upper(), c.strip()) for c in df.columns]
    return df.apply(pd.to_numeric, errors="coerce") / 100.0


def read_tidy_factor_file(path: Path, in_percent: bool) -> pd.DataFrame:
    """Read a single file with a Date column and factor columns."""
    df = pd.read_excel(path) if path.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")
    df.columns = [RENAME.get(str(c).strip().upper(), str(c).strip()) for c in df.columns]
    df = df.apply(pd.to_numeric, errors="coerce")
    return df / 100.0 if in_percent else df


def load_factors(path: Path, tidy_in_percent: bool = False) -> pd.DataFrame:
    """
    Load the daily factors as decimals, indexed by date, with columns
    MKT_RF, SMB, HML, RMW, CMA, UMD, RF.

    `path` is either a directory with the two French CSV files or a tidy file.
    """
    path = Path(path)
    if path.is_dir():
        csvs = sorted(path.glob("*.csv")) + sorted(path.glob("*.CSV"))
        five = [p for p in csvs if "5_factors" in p.name.lower() and "daily" in p.name.lower()]
        mom = [p for p in csvs if "mom" in p.name.lower() and "daily" in p.name.lower()]
        if not five or not mom:
            raise FileNotFoundError(
                f"{path}: expected 'Europe_5_Factors_Daily.csv' and 'Europe_Mom_Factor_Daily.csv'"
            )
        factors = read_french_csv(five[0]).join(read_french_csv(mom[0]), how="inner")
    else:
        factors = read_tidy_factor_file(path, tidy_in_percent)

    missing = [c for c in FACTOR_COLUMNS if c not in factors.columns]
    if missing:
        raise ValueError(f"Factor data is missing columns {missing}")

    factors = factors[FACTOR_COLUMNS].dropna().sort_index()
    if factors["MKT_RF"].abs().median() > 0.05:
        log.warning("Median |MKT_RF| > 5%%: factors look like percentages, not decimals")
    log.info("Factors: %d daily observations, %s to %s",
             len(factors), factors.index.min().date(), factors.index.max().date())
    return factors
