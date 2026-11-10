# Empirical Evidence of the Dividend Month Premium in the FTSE STAR Segment

**A Multi-Factor Asset Pricing Approach: replication package**

[![tests](https://github.com/LucaDennert/Empirical_Evidence_of_the_Dividend_Month_Premium_in_the_FTSE_STAR_Segment/actions/workflows/tests.yml/badge.svg)](https://github.com/LucaDennert/Empirical_Evidence_of_the_Dividend_Month_Premium_in_the_FTSE_STAR_Segment/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Luca Dennert**, BSc thesis in Economics and Finance, Università Bocconi.
Advisor: Prof. Carlo Ambrogio Favero.

The thesis is available in this repository:
[`Empirical_Evidence_of_the_Dividend_Month_Premium_in_the_FTSE_STAR_Segment.pdf`](Empirical_Evidence_of_the_Dividend_Month_Premium_in_the_FTSE_STAR_Segment.pdf).

---

## Overview

The thesis tests for a Dividend Month Premium (Hartzmark and Solomon, 2013) in
the FTSE Italia STAR segment of Borsa Italiana from January 2020 to December
2024. The premium has also been documented outside the United States
(Ainsworth and Nicholson, 2015; Chae and Koo, 2020; Chai, Do and Strydom, 2025).

For each of the 214 dividends paid in the period, the analysis computes the
return of buying at the close 15 trading days before the ex-date and selling
at the close of the day before the ex-date. Average window returns are positive and
significant, and they increase with the dividend yield. Regressing the window
returns on cumulative European factors gives positive and significant alphas
under the CAPM, the Fama–French three- and five-factor models and the Carhart
four-factor model. After bid-ask spreads, the strategy remains profitable only
for high-yield events (net dividend yield between 3% and 5%). An event study
shows a run-up until t = −1, a drop at the ex-date in line with the net
dividend, and a partial reversal afterwards. The evidence is consistent with
price pressure from dividend-seeking investors (Graham and Kumar, 2006;
Hartzmark and Solomon, 2013) and with catering explanations (Baker and
Wurgler, 2004) in a relatively illiquid segment.

This package reproduces every table and figure of Chapter 5 from the raw data
exports, with a single command:

```bash
python -m dmp --data-dir data --output-dir outputs
```

## Data availability and provenance

### Statement about rights

The author had legitimate access to all data used in the thesis. The LSEG
(formerly Refinitiv) data are proprietary: they are not included in this
repository and may not be redistributed. The Kenneth R. French factors are
publicly available. Any researcher with an LSEG Workspace licence can obtain
identical inputs by following [`data/README.md`](data/README.md).

### Data sources

| Data | Source | Access | Frequency | Period |
|---|---|---|---|---|
| Official closing prices, bid and ask quotes, turnover | LSEG Workspace, *Price History* | Licence required | Daily | 2020–2024 |
| Ex-dates and net/gross dividend amounts | LSEG Workspace, *Dividend History* | Licence required | Per event | 2020–2024 |
| Mkt−RF, SMB, HML, RMW, CMA, RF and WML (momentum), European | Kenneth R. French Data Library | Public | Daily | 2020–2024 |

The sample consists of the 66 FTSE Italia STAR stocks listed in
[`data/star_constituents.csv`](data/star_constituents.csv). The download steps,
file names and folder layout are in [`data/README.md`](data/README.md).

### Data citations

- LSEG Data & Analytics. *LSEG Workspace: Price History and Dividend History*, FTSE Italia STAR constituents, 2020–2024. Accessed through LSEG Workspace.
- French, K. R. *Data Library: Fama/French European 5 Factors [Daily]; European Momentum Factor (Mom) [Daily]*. https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

## Computational requirements

- **Software:** Python ≥ 3.10 with `numpy`, `pandas`, `scipy`, `statsmodels`,
  `matplotlib` and `openpyxl` (see [`requirements.txt`](requirements.txt)).
  The test suite runs on Python 3.10 and 3.13 through GitHub Actions on every
  commit.
- **Hardware:** any standard laptop. A full run on the synthetic dataset
  (25 stocks, 2020–2024) takes about 5 seconds.
- **Storage:** less than 50 MB for inputs and outputs.

## Instructions to replicators

1. Clone the repository and install the dependencies:

   ```bash
   git clone https://github.com/LucaDennert/Empirical_Evidence_of_the_Dividend_Month_Premium_in_the_FTSE_STAR_Segment.git
   cd Empirical_Evidence_of_the_Dividend_Month_Premium_in_the_FTSE_STAR_Segment
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Download the data as described in [`data/README.md`](data/README.md) and place it in `data/`.
3. Run the analysis:

   ```bash
   python -m dmp --data-dir data --output-dir outputs
   ```

4. The tables are written to `outputs/tables/`, also collected in a single
   workbook, `thesis_tables.xlsx`. The figures are in `outputs/figures/`.

Options: `--robust-se` uses HC1 standard errors in the factor regressions, and
`--factors FILE [--factors-in-percent]` uses a single pre-cleaned factor file.
All other parameters (window length, cutoffs, sample period, event-study
threshold) are set in [`dmp/config.py`](dmp/config.py).

**Without an LSEG licence.** A generator writes synthetic files with exactly the
same layout as the LSEG and Kenneth French files, so the whole pipeline can be
run and inspected. The resulting numbers have no economic meaning.

```bash
python scripts/make_synthetic_data.py --out example_data
python -m dmp --data-dir example_data --output-dir example_outputs
pytest                                   # unit tests of the core formulas
```

## List of tables and figures

| Thesis | Content | Module | Output (`outputs/`) |
|---|---|---|---|
| Eq. 4.1–4.3 | Window returns, bid-ask returns, cumulative factors | `events.py` | `data/events.csv` |
| Table 5.1 | Strategy returns by dividend-yield cutoff, 15-day window | `strategy_returns.py` | `tables/table_5_1.csv` |
| Table 5.2 | Same, annualised | `strategy_returns.py` | `tables/table_5_2.csv` |
| Section 5.1 | Median and mean quoted spread, average daily turnover | `liquidity.py` | `tables/liquidity.csv` |
| Table 5.5 | Strategy returns net of bid-ask spreads, 15-day window | `strategy_returns.py` | `tables/table_5_5.csv` |
| Table 5.6 | Same, annualised | `strategy_returns.py` | `tables/table_5_6.csv` |
| Table 5.7 | CAPM, FF3, C4F and FF5 alphas by cutoff (eq. 4.9) | `alphas.py` | `tables/table_5_7.csv` |
| Table 5.8 | Same, annualised | `alphas.py` | `tables/table_5_8.csv` |
| Figures 5.9, 5.10 | Average and cumulative daily returns around the ex-date | `event_study.py` | `figures/figure_5_9_*.png`, `figures/figure_5_10_*.png` |
| Figures 5.11, 5.12 | Same, events with net dividend yield ≥ 3.75% | `event_study.py` | `figures/figure_5_11_*.png`, `figures/figure_5_12_*.png` |

`outputs/results/` contains the unrounded results with standard errors,
t-statistics, p-values, R² and factor loadings. It also contains the alphas of
the returns net of bid-ask spreads, an additional robustness check not reported
in the thesis.

## Description of the code

```
dmp/                         Python package (dmp = Dividend Month Premium)
├── config.py                every parameter of the analysis, in one place
├── io_lseg.py               readers for the LSEG Excel exports
├── io_factors.py            reader for the Kenneth French CSV files
├── panel.py                 daily stock panel: prices, quotes, dividends
├── events.py                event-level dataset (eq. 4.1–4.3)
├── strategy_returns.py      returns by dividend-yield cutoff (Tables 5.1, 5.2, 5.5, 5.6)
├── inference.py             OLS (statsmodels) and one-sided tests
├── alphas.py                factor-model alphas (eq. 4.9, Tables 5.7, 5.8)
├── event_study.py           event-time returns (Figures 5.9–5.12)
├── liquidity.py             quoted spreads and turnover (Section 5.1)
└── pipeline.py              runs all steps in order
scripts/make_synthetic_data.py   synthetic data with the original file layout
tests/                           unit tests of the core formulas
data/                            data guide and list of sample constituents
```

## Methodology

Let T be the ex-date of a dividend paid by stock i, and let t denote trading
days, with t = 0 at the ex-date.

**Strategy window.** Buy at the close of T−15 and sell at the close of T−1.
Closing before the ex-date excludes the dividend and the mechanical price drop.

$$CR_{i,T} = \frac{P_{i,T-1}}{P_{i,T-15}} - 1 \quad (4.1) \qquad\qquad CAR_{i,T} = \frac{Bid_{i,T-1}}{Ask_{i,T-15}} - 1 \quad (4.2)$$

**Dividend yield.** Measured at entry, so the signal is known ex ante and is
not inflated by the run-up:

$$DY_{i,T} = \frac{D^{net}_{i,T}}{P_{i,T-15}}$$

Cutoffs go from 0% to 5.5% in steps of 0.25%, and cutoff c selects the events
with DY ≥ c.

**Factors.** Regional (European) factors are used rather than global ones,
since country and regional models price local stocks better than global
models (Griffin, 2002; Fama and French, 2012, 2017). Daily factors are
compounded over the 15 trading days preceding the ex-date, on the Italian
trading calendar. The risk-free rate is
compounded in the same way to obtain CRF<sub>T</sub>:

$$CFR_{k,T} = \prod_{t=T-15}^{T-1} (1 + F_{k,t}) - 1 \quad (4.3)$$

**Alphas.** Jensen (1968) alphas are estimated, for each cutoff and model,
with a cross-sectional regression across events:

$$CR_{i,T} - CRF_{T} = \alpha + \sum_k \beta_k CFR_{k,T} + \varepsilon_{i,T} \quad (4.9)$$

with factors {MKT} for the CAPM (Sharpe, 1964), {MKT, SMB, HML} for FF3 (Fama
and French, 1993), {MKT, SMB, HML, UMD} for C4F (Carhart, 1997) and
{MKT, SMB, HML, RMW, CMA} for FF5 (Fama and French, 2015). Significance refers to the one-sided test
H₁: α > 0, with classical OLS standard errors.

**Annualisation.** A = 252/15 = 16.8 windows per year. Means are annualised
linearly (A·r) and with compounding ((1 + r)^A − 1); volatility and the
Sharpe ratio are scaled by √A; annualised alphas are A·α. These figures assume
independent, non-overlapping windows and serve only for comparison.

**Event study.** Daily simple price returns are averaged across events for
each t ∈ [−15, +15]. The cumulative profile is the running sum of the averages.
Only events with a complete window are used, so each point is averaged over the
same events. The ex-date drop is compared with the net dividend, as in Elton
and Gruber (1970).

## References

The complete bibliography is in the thesis.

- Ainsworth, A., & Nicholson, M. (2015). Can dividend schedules predict abnormal returns? International evidence. *Financial Markets & Corporate Governance Conference*.
- Baker, M., & Wurgler, J. (2004). A catering theory of dividends. *Journal of Finance*, 59(3), 1125–1165. https://doi.org/10.1111/j.1540-6261.2004.00658.x
- Carhart, M. M. (1997). On persistence in mutual fund performance. *Journal of Finance*, 52(1), 57–82. https://doi.org/10.1111/j.1540-6261.1997.tb03808.x
- Chae, Y. K., & Koo, H.-K. (2020). Dividend-month premium in the Korean stock market. *Journal of Derivatives and Quantitative Studies*, 28(3), 193–213. https://doi.org/10.1108/JDQS-04-2020-0006
- Chai, D., Do, V., & Strydom, M. (2025). *The dividend month premium uncovered*. Working paper, Monash University.
- Elton, E. J., & Gruber, M. J. (1970). Marginal stockholder tax rates and the clientele effect. *Review of Economics and Statistics*, 52(1), 68–74. https://doi.org/10.2307/1927599
- Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds. *Journal of Financial Economics*, 33(1), 3–56. https://doi.org/10.1016/0304-405X(93)90023-5
- Fama, E. F., & French, K. R. (2012). Size, value, and momentum in international stock returns. *Journal of Financial Economics*, 105(3), 457–472. https://doi.org/10.1016/j.jfineco.2012.05.011
- Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model. *Journal of Financial Economics*, 116(1), 1–22. https://doi.org/10.1016/j.jfineco.2014.10.010
- Fama, E. F., & French, K. R. (2017). International tests of a five-factor asset pricing model. *Journal of Financial Economics*, 123(3), 441–463. https://doi.org/10.1016/j.jfineco.2016.11.004
- Graham, J. R., & Kumar, A. (2006). Do dividend clienteles exist? Evidence on dividend preferences of retail investors. *Journal of Finance*, 61(3), 1305–1336. https://doi.org/10.1111/j.1540-6261.2006.00873.x
- Griffin, J. M. (2002). Are the Fama and French factors global or country specific? *Review of Financial Studies*, 15(3), 783–803. https://doi.org/10.1093/rfs/15.3.783
- Hartzmark, S. M., & Solomon, D. H. (2013). The dividend month premium. *Journal of Financial Economics*, 109(3), 640–660. https://doi.org/10.1016/j.jfineco.2013.03.005
- Jensen, M. C. (1968). The performance of mutual funds in the period 1945–1964. *Journal of Finance*, 23(2), 389–416. https://doi.org/10.1111/j.1540-6261.1968.tb00815.x
- Sharpe, W. F. (1964). Capital asset prices: A theory of market equilibrium under conditions of risk. *Journal of Finance*, 19(3), 425–442. https://doi.org/10.1111/j.1540-6261.1964.tb02865.x

## Citation

> Dennert, L. *Empirical Evidence of the Dividend Month Premium in the FTSE STAR
> Segment: A Multi-Factor Asset Pricing Approach.* BSc thesis, Università Bocconi.

See [`CITATION.cff`](CITATION.cff).

## License

The code is released under the [MIT License](LICENSE). The data remain subject
to the terms of their providers.
