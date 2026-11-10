"""
Command-line entry point:

    python -m dmp --data-dir data --output-dir outputs
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from .config import Config
from .pipeline import run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m dmp",
        description="Replicate the Dividend Month Premium analysis on the FTSE Italia STAR segment.",
    )
    parser.add_argument("--data-dir", type=Path, default=Config.data_dir,
                        help="folder containing prices/, dividends/ and factors/ (default: data)")
    parser.add_argument("--output-dir", type=Path, default=Config.output_dir,
                        help="folder where results are written (default: outputs)")
    parser.add_argument("--factors", type=Path, default=None,
                        help="factor folder or tidy factor file (default: <data-dir>/factors)")
    parser.add_argument("--factors-in-percent", action="store_true",
                        help="the tidy factor file passed with --factors is in percent")
    parser.add_argument("--robust-se", action="store_true",
                        help="use HC1 heteroskedasticity-robust standard errors for the alphas")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug-level logging")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)-7s %(name)s: %(message)s")

    cfg = replace(Config(), data_dir=args.data_dir, output_dir=args.output_dir,
                  tidy_factors_in_percent=args.factors_in_percent,
                  regression_cov_type="HC1" if args.robust_se else "nonrobust")
    if args.factors is not None:
        cfg = replace(cfg, factors_subdir=str(args.factors.resolve()))
    run(cfg)


if __name__ == "__main__":
    main()
