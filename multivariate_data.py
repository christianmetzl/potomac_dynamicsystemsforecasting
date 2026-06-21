"""
multivariate_data.py - H4 encoding-density panel for CHIMERA-QRC (Phase 3, Axis B).

The Phase-2 paper (S7, H4) commits to scaling qubit count "in lockstep with input
richness ... so added qubits encode new information rather than reprocessing the same
eight." The univariate Axis-A sweep (FINDINGS_scaling_sweep.md) measured the failure mode
this guards against: with a fixed 8-lag input, qubits beyond 8 receive RY(0) and actively
degrade the model.

This module builds an ORDERED multivariate realized-measure panel from the same public
Oxford-Man .SPX data (no new data needed), exploiting the per-day measure columns:
  rv5  - 5-min realized variance (the base; also the forecast target)
  rv10 - 10-min realized variance (coarser sampling frequency)
  bv   - bipower variation (jump-robust continuous component)
  medrv- median realized variance (jump-robust)
  rsv  - realized semivariance (downside risk)
  jump - log jump-ratio log(rv5) - log(bv)  (always finite; intraday jump intensity)

Column ordering is deliberate:
  positions 0..7  = log rv5 at lags (1,2,3,4,5,10,15,22)  == the EXACT univariate baseline,
                    so an n<=8 multivariate reservoir is identical to the univariate one
                    (a clean control: the encoders only diverge as n grows past 8);
  positions 8..   = new measures, interleaved lag-by-lag, so each ADDED qubit (n=9,10,...)
                    encodes a genuinely new information dimension (downside, jump, freq).

Target (y_logrv = log rv5) and the HAR set are unchanged from the univariate pipeline, so
the ONLY thing that changes between encoders is the reservoir's input panel.

Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import volatility_data as vd

RV5_LAGS = (1, 2, 3, 4, 5, 10, 15, 22)          # positions 0..7 == univariate LAGS
NEW_MEASURES = ("rsv", "medrv", "jump", "bv", "rv10")  # most-new-info first (lowest corr w/ rv5)
NEW_LAGS = (1, 2, 3, 5, 10, 22)


def load_spx_panel(path=vd.OXFORDMAN_CSV, symbol=".SPX"):
    """Load the .SPX multi-measure realized panel as a positive, date-sorted DataFrame."""
    df = pd.read_csv(vd._find(path), index_col=0)
    d = df[df["Symbol"] == symbol].copy()
    d.index = pd.to_datetime([str(s).split("+")[0] for s in d.index])
    d = d.sort_index()
    cols = ["rv5", "rv10", "bv", "medrv", "rsv", "close_price"]
    P = pd.DataFrame({c: pd.to_numeric(d[c], errors="coerce") for c in cols}, index=d.index)
    pos = (P[["rv5", "rv10", "bv", "medrv", "rsv", "close_price"]] > 0).all(axis=1)
    P = P[pos & P.notna().all(axis=1)]
    return P


def build_panel_supervised(horizon=1):
    """One-step-ahead supervised dataset with a multivariate input panel.

    Returns a dict mirroring volatility_data.build_supervised, plus:
      X_panel : (N, F) ordered log realized-measure features (see module docstring)
      names   : list[str] feature names in column order
    The reservoir consumes the first n columns of X_panel (n = qubit count); y_logrv, y_rv
    and X_har are the same rv5-based quantities as the univariate pipeline.
    """
    P = load_spx_panel()
    rv = P["rv5"]
    logs = {
        "rv5": np.log(P["rv5"]), "rv10": np.log(P["rv10"]),
        "bv": np.log(P["bv"]), "medrv": np.log(P["medrv"]), "rsv": np.log(P["rsv"]),
        "jump": np.log(P["rv5"]) - np.log(P["bv"]),     # log jump-ratio (always finite)
    }
    h = horizon - 1
    y_rv = rv.shift(-h)
    y_logrv = np.log(rv).shift(-h)

    feat, names = {}, []
    # Block A: rv5 lags == univariate baseline (positions 0..7)
    for L in RV5_LAGS:
        nm = f"rv5_lag{L}"; feat[nm] = logs["rv5"].shift(L + h); names.append(nm)
    # Block B: new measures, interleaved by lag then measure (positions 8..)
    for L in NEW_LAGS:
        for m in NEW_MEASURES:
            nm = f"{m}_lag{L}"; feat[nm] = logs[m].shift(L + h); names.append(nm)

    Xpanel = pd.DataFrame(feat)[names]
    har = vd.har_components(rv)
    if horizon > 1:
        har = har.shift(h)
    Xhar = np.log(har)

    allcols = pd.concat(
        [Xpanel, Xhar.add_prefix("har_"),
         y_logrv.rename("y_logrv"), y_rv.rename("y_rv"), P["close_price"].rename("close")],
        axis=1,
    ).dropna()

    return {
        "X_panel": allcols[names].values,
        "names": names,
        "X_har": allcols[["har_rv_d", "har_rv_w", "har_rv_m"]].values,
        "y_logrv": allcols["y_logrv"].values,
        "y_rv": allcols["y_rv"].values,
        "dates": allcols.index.values,
        "n_features": len(names),
    }


if __name__ == "__main__":
    d = build_panel_supervised()
    print(f"Multivariate panel: N={len(d['y_logrv'])}, F={d['n_features']} features")
    print("First 14 feature columns (qubit order):")
    for i, nm in enumerate(d["names"][:14]):
        tag = "  [univariate baseline]" if i < 8 else "  <- NEW information"
        print(f"  q{i:2d}: {nm}{tag}")
    X = d["X_panel"]
    print(f"\npanel shape {X.shape}; any NaN: {np.isnan(X).any()}; "
          f"col std range [{X.std(0).min():.3f}, {X.std(0).max():.3f}]")
