"""
volatility_data.py - Track A (financial realized-volatility) data pipeline for CHIMERA-QRC.

Real data: S&P 500 daily 5-minute realized variance (rv5) from the Oxford-Man
Realized Library (terminated 2022; recovered from the `highfrequency` R-package
mirror). Series: .SPX, 2000-01-03 .. 2020-02-21, 5052 trading days, INCLUDING the
2008 Global Financial Crisis regime shift (peak realized vol 8.8%/day on 2008-10-10).
`close_price` gives close-to-close returns for GARCH-family baselines, date-aligned
to RV so every model is evaluated on the same target over the same window.

This mirrors the empirical setting of Li, Mukhopadhyay, Bayat & Habibnia (PRR 2026,
arXiv:2505.13933) - one-step-ahead forecasting of S&P 500 realized volatility - but
on PROPER daily 5-min RV rather than their coarse monthly-from-daily proxy, so the
HAR baseline is genuinely strong and a win against it is far more credible.

Design principle (carried over from the Denver fair-benchmark methodology):
all reservoir models (ESN, CHIMERA) receive IDENTICAL inputs; the only difference
is the quantum vs classical reservoir. The linear HAR information set is made
available to the reservoir readout so that any reservoir gain is genuine
nonlinearity, not missing linear structure.
"""
import numpy as np
import pandas as pd
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
def _find(fname):
    """Resolve a data file from cwd, ./data/, or alongside this module."""
    for c in (fname, os.path.join(_HERE, "data", os.path.basename(fname)),
              os.path.join(_HERE, os.path.basename(fname))):
        if os.path.exists(c):
            return c
    return fname

OXFORDMAN_CSV = "oxfordman_spx_full.csv"
TRADING_YEAR = 252
# multi-horizon lag set spanning daily -> monthly (the long-memory structure).
# 7 lags -> 7 input qubits, matching the anchor paper's n1=7 input / n2=3 hidden split.
DEFAULT_LAGS = (1, 2, 3, 5, 10, 15, 22)


def load_spx_rv(path=OXFORDMAN_CSV, symbol=".SPX", measure="rv5"):
    """Load real Oxford-Man realized-variance series for one index.
    Returns a DataFrame indexed by date with columns: rv (daily realized variance),
    logrv, close (price), ret (close-to-close % return)."""
    df = pd.read_csv(_find(path), index_col=0)
    d = df[df["Symbol"] == symbol].copy()
    d.index = pd.to_datetime([str(s).split("+")[0] for s in d.index])
    d = d.sort_index()
    rv = pd.to_numeric(d[measure], errors="coerce")
    cp = pd.to_numeric(d["close_price"], errors="coerce")
    m = rv.notna() & cp.notna() & (rv > 0) & (cp > 0)
    rv, cp = rv[m], cp[m]
    ret = 100.0 * np.log(cp).diff()  # percentage log returns (GARCH convention)
    out = pd.DataFrame(
        {"rv": rv.values, "logrv": np.log(rv.values), "close": cp.values, "ret": ret.values},
        index=rv.index,
    )
    return out.dropna()


def har_components(rv):
    """Corsi (2009) HAR realized-volatility components in VARIANCE units, each
    using information available at t-1 to predict RV_t:
      rv_d = RV_{t-1};  rv_w = mean(RV_{t-1..t-5});  rv_m = mean(RV_{t-1..t-22}).
    Returns a DataFrame aligned to rv's index (first 22 rows are NaN)."""
    rv = pd.Series(rv)
    rv_d = rv.shift(1)
    rv_w = rv.rolling(5).mean().shift(1)
    rv_m = rv.rolling(22).mean().shift(1)
    return pd.DataFrame({"rv_d": rv_d, "rv_w": rv_w, "rv_m": rv_m})


def build_supervised(df=None, horizon=1, lags=DEFAULT_LAGS, path=OXFORDMAN_CSV,
                     symbol=".SPX", measure="rv5"):
    """Build a one-step-ahead supervised dataset for realized-volatility forecasting.

    Returns a dict with (all numpy arrays, row-aligned, NaNs dropped):
      X_lags : (N, len(lags))  lagged log-RV values  -> reservoir input encoding
      X_har  : (N, 3)          log HAR components [log rv_d, log rv_w, log rv_m]
      y_logrv: (N,)            target log-RV at t+horizon-1 (the modeled quantity)
      y_rv   : (N,)            target realized variance (level) for QLIKE
      ret    : (N,)            same-day return (for GARCH alignment / diagnostics)
      dates  : (N,) datetimes  target dates
    """
    if df is None:
        df = load_spx_rv(path, symbol, measure)
    rv = df["rv"]
    logrv = df["logrv"]

    # target: RV at t (predicted from info up to t-1). For horizon h, shift target up.
    y_rv = rv.shift(-(horizon - 1))
    y_logrv = logrv.shift(-(horizon - 1))

    # lagged log-RV features (information at t-1, t-2, ...)
    lag_cols = {f"lag{L}": logrv.shift(L + (horizon - 1)) for L in lags}
    Xlag = pd.DataFrame(lag_cols)

    # HAR components (variance units) -> log
    har = har_components(rv)
    if horizon > 1:
        har = har.shift(horizon - 1)
    Xhar = np.log(har)

    allcols = pd.concat(
        [Xlag, Xhar.add_prefix("har_"),
         y_logrv.rename("y_logrv"), y_rv.rename("y_rv"), df["ret"].rename("ret")],
        axis=1,
    ).dropna()

    return {
        "X_lags": allcols[[f"lag{L}" for L in lags]].values,
        "X_har": allcols[["har_rv_d", "har_rv_w", "har_rv_m"]].values,
        "y_logrv": allcols["y_logrv"].values,
        "y_rv": allcols["y_rv"].values,
        "ret": allcols["ret"].values,
        "dates": allcols.index.values,
        "lags": list(lags),
    }


def make_splits(n, train_frac=0.70):
    """Chronological (no-shuffle) train/test split indices."""
    n_tr = int(round(n * train_frac))
    return np.arange(n_tr), np.arange(n_tr, n)


def scale_to_phase(X_train, X_all, lo=-np.pi, hi=np.pi):
    """Min-max scale features into [lo, hi] for RY phase encoding, using TRAIN-ONLY
    statistics (no look-ahead leakage). Returns scaled X_all."""
    mn = X_train.min(axis=0)
    mx = X_train.max(axis=0)
    rng = np.where((mx - mn) == 0, 1.0, mx - mn)
    z = (X_all - mn) / rng                      # ~[0,1] on train support
    return lo + (hi - lo) * np.clip(z, -0.5, 1.5)  # allow mild test overshoot


if __name__ == "__main__":
    df = load_spx_rv()
    print(f"Loaded .SPX realized variance: {len(df)} days, "
          f"{df.index.min().date()} -> {df.index.max().date()}")
    print(f"  annualized vol = {np.sqrt(TRADING_YEAR*df['rv'].mean())*100:.1f}%  "
          f"(daily vol {np.sqrt(df['rv']).mean()*100:.2f}%, "
          f"max {np.sqrt(df['rv']).max()*100:.2f}% on {df['rv'].idxmax().date()})")
    data = build_supervised(df, horizon=1)
    tr, te = make_splits(len(data["y_logrv"]))
    print(f"Supervised set: N={len(data['y_logrv'])}, "
          f"input lags={data['lags']} ({data['X_lags'].shape[1]} qubits), "
          f"HAR feats={data['X_har'].shape[1]}")
    print(f"  train={len(tr)} ({pd.Timestamp(data['dates'][tr[0]]).date()}.."
          f"{pd.Timestamp(data['dates'][tr[-1]]).date()}), "
          f"test={len(te)} ({pd.Timestamp(data['dates'][te[0]]).date()}.."
          f"{pd.Timestamp(data['dates'][te[-1]]).date()})")
