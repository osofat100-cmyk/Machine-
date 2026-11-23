# Sealed test result: 2016-01-04 to 2026-11-20 (2738 trading days)

Settings were locked on the development years (2006-2015) and committed before this test.
N = 36 combinations tried. PBO (development) over all 36: 0.60.

| Strategy | $1,000 became | 95% range | Sharpe above cash | IR vs SPY | DSR | Worst drop | Trades | Coin-flip p | Beats SPY? |
|---|---|---|---|---|---|---|---|---|---|
| ridge_h1 | $1,638.28 | $705-$3,456 | 0.23 | -0.54 | 0.00 | -36% | 473 | 0.018 | no |
| ridge_h5 | $1,413.84 | $241-$6,238 | 0.16 | -0.51 | 0.00 | -60% | 575 | 0.699 | no |
| ridge_h21 | $1,982.74 | $351-$8,630 | 0.29 | -0.30 | 0.00 | -56% | 175 | 0.784 | no |
| gbm_h1 | $1,460.03 | $700-$3,061 | 0.16 | -0.62 | 0.00 | -27% | 599 | 0.071 | no |
| gbm_h5 | $1,251.59 | $259-$4,401 | 0.09 | -0.63 | 0.00 | -51% | 421 | 0.748 | no |
| gbm_h21 | $1,378.12 | $284-$5,789 | 0.14 | -0.53 | 0.00 | -49% | 163 | 0.948 | no |
| mlp_h1 | $808.76 | $342-$1,650 | -0.21 | -0.95 | 0.00 | -42% | 551 | 0.807 | no |
| mlp_h5 | $3,703.70 | $1,303-$9,967 | 0.62 | -0.05 | 0.01 | -31% | 383 | 0.015 | no |
| mlp_h21 | $3,717.64 | $1,831-$7,593 | 0.84 | -0.10 | 0.01 | -15% | 117 | 0.038 | no |
| hold_spy | $4,089.21 | $1,482-$10,525 | 0.69 | 0.00 | nan | -34% | 1 | nan | - |
| equal_weight | $3,796.98 | $1,401-$9,140 | 0.67 | -0.20 | 0.00 | -36% | 1703 | nan | - |
| momentum | $2,240.45 | $748-$7,070 | 0.35 | -0.30 | 0.00 | -31% | 75 | nan | - |

Forecast quality (strategies only):

| Strategy | R2_OS timing | R2_OS selection | Direction hit rate | PT p | Timing skill | Selection skill | Invested |
|---|---|---|---|---|---|---|---|
| ridge_h1 | -0.0012 | -0.0006 | 50.5% | 0.816 | +0.0010 | +0.0007 | 12% |
| ridge_h5 | -0.0098 | -0.0023 | 52.1% | 0.993 | -0.0026 | +0.0006 | 70% |
| ridge_h21 | -0.0558 | -0.0051 | 66.2% | 0.148 | +0.0021 | -0.0014 | 86% |
| gbm_h1 | -0.0777 | -0.0195 | 49.0% | 0.981 | +0.0008 | +0.0002 | 14% |
| gbm_h5 | -0.1235 | -0.0118 | 46.3% | 0.996 | +0.0005 | -0.0006 | 49% |
| gbm_h21 | -0.3241 | -0.0062 | 60.8% | 0.655 | -0.0273 | -0.0007 | 82% |
| mlp_h1 | -0.0234 | -0.0027 | 48.5% | 0.912 | -0.0003 | -0.0002 | 15% |
| mlp_h5 | -0.0954 | -0.0768 | 48.1% | 0.890 | +0.0028 | +0.0022 | 45% |
| mlp_h21 | -0.2255 | -0.0397 | 56.9% | 0.135 | +0.0101 | +0.0045 | 50% |

## Independent review (after the run)

No look-ahead and no accounting error found; the dollars above are not too high or too low. Unit tests pass.
Minor notes, none changing the verdict (every Deflated Sharpe is 0.01 or less, far below the 0.95 needed):
- The coin flips draw each decision independently, so they switch more often than the strategies and pay more
  costs. That makes the coin-flip p-values for the daily and weekly strategies look somewhat better than they
  deserve (ridge_h1 0.018 and mlp_h5 0.015 are borderline). This follows PLAN.md as written; not changed afterwards.
- The Diebold-Mariano tests use h-1 lags although the monthly/weekly forecast errors do not overlap; this only
  makes those tests more cautious.
