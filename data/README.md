# Data

The raw data are **not included** in this repository: prices, quotes and dividends
are licensed by LSEG (formerly Refinitiv) and cannot be redistributed. This
document explains how to obtain every input and where to place it so that
`python -m dmp` runs without any further manual step.

## Expected layout

```
data/
├── star_constituents.csv          # list of the 66 RICs in the sample (included)
├── prices/                        # one LSEG Price History export per stock
│   ├── MARR.MI_PREZZO.xlsx
│   └── ...
├── dividends/                     # one LSEG Dividend History export per stock
│   ├── MARR.MI_DIV.xlsx
│   └── ...
└── factors/                       # Kenneth French daily European factors
    ├── Europe_5_Factors_Daily.csv
    └── Europe_Mom_Factor_Daily.csv
```

File names must start with the stock's RIC (e.g. `MARR.MI`) followed by
`_PREZZO.xlsx` (or `_PRICE.xlsx`) for prices and `_DIV.xlsx` (or `_DIVIDEND.xlsx`)
for dividends. The pipeline processes every file it finds, and matches prices and
dividends on the RIC.

## 1. Sample: FTSE Italia STAR constituents

`star_constituents.csv` lists the 66 stocks of the FTSE Italia STAR segment that
make up the sample (RIC codes, Borsa Italiana suffix `.MI`). Each RIC can be
pasted directly in the LSEG Workspace search bar.

## 2. Daily prices and bid/ask quotes (LSEG Workspace)

For each RIC in `star_constituents.csv`:

1. Open the instrument in LSEG Workspace and launch the **Price History** app.
2. Set **Interval** to *Daily* and the date range to **01-Jan-2020 → 31-Dec-2024**.
3. Make sure the table includes the columns **Exchange Date**, **Official Close Price**,
   **Bid**, **Ask** and **Turnover** (add them from the column selector if needed).
4. Export to Excel and save the file as `data/prices/<RIC>_PREZZO.xlsx`.

Keep the export as it is: the summary block above the table (which contains the
average turnover used in the liquidity analysis) and any title rows are handled
automatically.

> Starting the export a few weeks earlier (e.g. 01-Dec-2019) lets dividends going
> ex in the first 15 trading days of 2020 enter the sample. The thesis uses
> 01-Jan-2020, so such events are excluded there.

## 3. Dividends (LSEG Workspace)

For each RIC:

1. Open the instrument's **Dividend History** (corporate actions → dividends).
2. Select the period **01-Jan-2020 → 31-Dec-2024**.
3. The export must contain **Ex-Date**, **Gross Amt (Unadj)** and **Net Amt (Unadj)**
   (Ann. Date, Pay Date and Record Date are read if present).
4. Export to Excel and save as `data/dividends/<RIC>_DIV.xlsx`.

Stocks that paid no dividend in the period do not need a dividend file.
Text dates in the `13-Mar-2024` format and native Excel dates are both accepted.

## 4. Risk factors (Kenneth R. French Data Library)

From the [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html),
section *Developed Markets Factors and Returns*, download:

| Dataset on the website | File to extract into `data/factors/` | Columns |
|---|---|---|
| Fama/French European 5 Factors **[Daily]** | `Europe_5_Factors_Daily.csv` | Mkt-RF, SMB, HML, RMW, CMA, RF |
| European Momentum Factor (Mom) **[Daily]** | `Europe_Mom_Factor_Daily.csv` | WML |

Unzip the archives and place the CSV files in `data/factors/` without editing
them: the reader skips the description lines at the top of each file and
converts returns from percent to decimals. The momentum factor (WML in the
file) is labelled UMD in the thesis and in the outputs. Note that in the French
library the European factors are expressed in US dollars and RF is the
one-month US Treasury bill rate.

A single pre-cleaned file with a `Date` column and the columns above can be used
instead:

```bash
python -m dmp --factors path/to/factors.xlsx                       # values in decimals
python -m dmp --factors path/to/factors.xlsx --factors-in-percent  # values in percent
```

## Sanity checks

With the data described above, the log printed by `python -m dmp` should report
214 dividend events retained, with an average net dividend yield of about 2.44%
(Section 4 of the thesis). The log also lists any ex-date that does not fall on
a trading day in the price file, and any dividend file without a matching price
file.
