"""
feature_pool.py - Axis-B encoding-density feature pool for CHIMERA-QRC.

The Phase-3 H0 test refuted "more qubits help" with the FIXED univariate 8-lag
encoder, because qubits beyond the input dimension sit idle and only dilute the
reservoir (see results/scaling_sweep_findings.md). Axis B fixes that bottleneck:
it scales INPUT RICHNESS with qubit count so each added qubit encodes genuinely
NEW information.

All features come from the realized measures already bundled in
data/oxfordman_spx_full.csv (Oxford-Man .SPX) - no external data is required:

  rv5      realized variance (5-min)          -> the 8 core log-RV lags
  rsv      realized SEMIVARIANCE (downside)    -> leverage / downside asymmetry
  bv       bipower variation (jump-robust)     -> continuous component
  medrv    median RV (jump-robust)             -> jump-robust level
  rk_parzen realized kernel                     -> alternative estimator
  open_to_close  open-to-close return          -> overnight vs intraday
  close_price -> daily log return              -> leverage (signed) + ARCH term

Jump component:  J_t = max(rv5_t - bv_t, 0)   (Barndorff-Nielsen & Shephard).

Everything is LEAKAGE-FREE: every feature uses information available at t-1 (or
earlier) to predict RV_t, and the supervised rows are aligned to exactly the same
target as volatility_data.build_supervised (single dropna over all columns).

The pool columns are returned in PRIORITY order (most orthogonal-to-RV info
first, after the 8 core lags), so taking the first n columns gives the richest
n-feature encoding for an n-qubit reservoir.

Team EIGENNEXUS | GIC 2026 - Phase 3 (Axis B)
"""
import numpy as np
import pandas as pd
import os

import volatility_data as vd

LAGS = (1, 2, 3, 4, 5, 10, 15, 22)   # the 8 core log-RV lags (paper baseline)


def _load_raw_spx():
    """Load the .SPX realized-measure columns, ALIGNED to the canonical supervised
    panel (volatility_data.load_spx_rv) so Axis-B shares the exact same rows/dates as
    every other experiment (eliminates the prior 1-row offset)."""
    base = vd.load_spx_rv()                      # canonical rv/close/ret; index == build_supervised
    path = vd._find(vd.OXFORDMAN_CSV)
    df = pd.read_csv(path, index_col=0)
    d = df[df["Symbol"] == ".SPX"].copy()
    d.index = pd.to_datetime([str(s).split("+")[0] for s in d.index])
    d = d.sort_index()
    d = d[~d.index.duplicated()]
    num = lambda c: (pd.to_numeric(d[c], errors="coerce") if c in d.columns
                     else pd.Series(np.nan, index=d.index))
    extra = pd.DataFrame({"rsv": num("rsv"), "bv": num("bv"), "medrv": num("medrv"),
                          "rk": num("rk_parzen"), "o2c": num("open_to_close")})
    extra = extra.reindex(base.index)            # align extras to the canonical rows
    out = pd.DataFrame(index=base.index)
    out["rv"] = base["rv"].values
    out["close"] = base["close"].values
    for c in ("rsv", "bv", "medrv", "rk", "o2c"):
        out[c] = extra[c].values
    return out


def build_rich(horizon=1):
    """Build the Axis-B feature pool aligned to the standard supervised target.

    Returns dict:
      pool    : (N, P) raw feature matrix, columns in priority order
      names   : list[str] of length P
      X_lags  : (N, 8) the core log-RV lags (for the hybrid linear readout)
      X_har   : (N, 3) HAR components (log)
      y_logrv : (N,)  target log-RV
      y_rv    : (N,)  target RV (level, for QLIKE/MZ)
      dates   : (N,)  target dates
    """
    raw = _load_raw_spx()
    rv = raw["rv"]
    logrv = np.log(rv)
    ret = 100.0 * np.log(raw["close"]).diff()          # % log return (leverage)
    rsv = raw["rsv"]
    bv = raw["bv"]
    medrv = raw["medrv"]
    rk = raw["rk"]
    o2c = raw["o2c"]

    # derived, all in info-at-t terms (we shift below to make them t-1 features)
    jump = (rv - bv).clip(lower=0.0)                    # jump variation
    jump_share = (jump / rv).clip(0, 1)                # fraction of variance from jumps
    down_share = (rsv / rv).clip(0, 1)                 # downside share (asymmetry)

    cols = {}
    # --- 8 core log-RV lags (baseline; qubits 1..8) ---
    for L in LAGS:
        cols[f"logrv_l{L}"] = logrv.shift(L)
    # --- richness adds (priority: most orthogonal-to-symmetric-RV first) ---
    cols["ret_l1"] = ret.shift(1)                       # signed return (leverage dir)
    cols["downshare_l1"] = down_share.shift(1)          # downside/leverage asymmetry
    cols["jumpshare_l1"] = jump_share.shift(1)          # jump intensity
    cols["o2c2_l1"] = (o2c ** 2).shift(1)               # overnight/intraday energy
    cols["ret2_l1"] = (ret ** 2).shift(1)               # ARCH term
    cols["logrsv_l1"] = np.log(rsv.clip(lower=1e-12)).shift(1)   # downside level
    cols["logbv_l1"] = np.log(bv.clip(lower=1e-12)).shift(1)     # continuous comp.
    cols["logmedrv_l1"] = np.log(medrv.clip(lower=1e-12)).shift(1)  # jump-robust lvl
    cols["downshare_w"] = down_share.rolling(5).mean().shift(1)  # weekly asymmetry
    cols["jumpshare_w"] = jump_share.rolling(5).mean().shift(1)  # weekly jump
    cols["logrk_l1"] = np.log(rk.clip(lower=1e-12)).shift(1)     # alt estimator

    # priority order: core lags first, then the richness adds in the order above
    pool_names = [f"logrv_l{L}" for L in LAGS] + [
        "ret_l1", "downshare_l1", "jumpshare_l1", "o2c2_l1", "ret2_l1",
        "logrsv_l1", "logbv_l1", "logmedrv_l1", "downshare_w", "jumpshare_w",
        "logrk_l1",
    ]

    # HAR components (variance units -> log), same as volatility_data
    har = vd.har_components(rv)
    har = np.log(har)

    # target
    y_rv = rv.shift(-(horizon - 1))
    y_logrv = logrv.shift(-(horizon - 1))

    allcols = pd.concat(
        [pd.DataFrame(cols),
         har.add_prefix("har_"),
         y_logrv.rename("y_logrv"), y_rv.rename("y_rv")],
        axis=1,
    ).dropna()

    pool = allcols[pool_names].values
    X_lags = allcols[[f"logrv_l{L}" for L in LAGS]].values
    X_har = allcols[["har_rv_d", "har_rv_w", "har_rv_m"]].values
    return {
        "pool": pool,
        "names": pool_names,
        "X_lags": X_lags,
        "X_har": X_har,
        "y_logrv": allcols["y_logrv"].values,
        "y_rv": allcols["y_rv"].values,
        "dates": allcols.index.values,
    }


def scale_pool(pool, tr):
    """Min-max scale each pool column to [0,1] on TRAIN rows only (no leakage)."""
    lo, hi = pool[tr].min(0), pool[tr].max(0)
    rng = np.where((hi - lo) == 0, 1.0, hi - lo)
    return np.clip((pool - lo) / rng, 0.0, 1.0)


def encode(pool_scaled, n, scheme="rich"):
    """Build the n-qubit encoded input from the scaled pool.

    scheme='rich'     : first min(n, P) pool columns; extra qubits idle (no fill).
    scheme='reupload' : same first columns, but if n > P, re-upload earlier columns
                        cyclically (data re-uploading) so every qubit is informed.
    """
    P = pool_scaled.shape[1]
    if n <= P or scheme != "reupload":
        return pool_scaled[:, :min(n, P)]
    idx = [q % P for q in range(n)]          # cycle through pool columns
    return pool_scaled[:, idx]


if __name__ == "__main__":
    d = build_rich()
    print(f"rich pool: N={len(d['y_logrv'])} rows, P={d['pool'].shape[1]} features")
    print("priority columns:", d["names"])
    print("first-row sample:", np.round(d["pool"][0], 4))
