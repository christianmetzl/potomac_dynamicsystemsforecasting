"""
vol_timing_backtest.py - the ECONOMIC-significance layer (addresses the critique that a
statistical RMSE result says nothing a desk can trade). We convert each model's one-step RV
forecast into a textbook VOLATILITY-TIMING strategy (Fleming-Kirby-Ostdiek 2001): scale
S&P-500 exposure inversely to forecast variance to hold risk at a constant target, then measure
realized Sharpe, max drawdown, turnover, and the net-of-cost Sharpe.

  position on day t:  w_t = (target_daily_vol) / sqrt(RV_forecast_t),  clipped to [0, w_max]
  strategy return  :  w_t * r_t  -  cost * |w_t - w_{t-1}|         (r_t = day-t % return /100)

The forecast of RV_t is made from t-1 information (leakage-free), so sizing day-t exposure with
it is causal. We compare buy&hold vs timing on HAR, HAR-X and CHIMERA forecasts, and report the
annual management fee (Δ certainty-equivalent) a mean-variance investor would pay to switch from
the HAR-timed to the CHIMERA-timed strategy.

HONEST EXPECTATION (consistent with the rest of the study): because CHIMERA ≈ HAR-X in forecast
accuracy, their economic outcomes should be ~equal — i.e. no economic quantum advantage. The
deployable takeaway is the OTHER comparison: informed realized-measure features (HAR-X) vs plain
HAR. We report whatever it shows.

Usage:  python3 vol_timing_backtest.py            # calm + crisis windows
        python3 vol_timing_backtest.py --quick    # calm window only, 3 CHIMERA seeds
"""
import argparse
import time
import numpy as np
import pandas as pd

import feature_pool as fp
import scaling_sweep as ss
from vol_fair_benchmark import ridge_readout

CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")
N_FOCAL = 10
TARGET_ANN_VOL = 0.10           # 10% annualized target
W_MAX = 3.0                     # leverage cap
COST = 0.0001                   # 1 bp per unit turnover (round-trip-ish, conservative)
RF = 0.0                        # excess-return Sharpe


def _returns_aligned(dates):
    raw = fp._load_raw_spx()
    ret = (100.0 * np.log(raw["close"])).diff()    # % daily log return, same-day as RV_t
    return ret.reindex(pd.to_datetime(dates)).values / 100.0   # to fraction


def _stats(strat, w):
    """Annualized return, vol, Sharpe, max drawdown, turnover, net Sharpe (after tx cost)."""
    dwt = np.abs(np.diff(np.concatenate([[0.0], w])))
    net = strat - COST * dwt
    ann_ret = float(np.mean(net) * 252); ann_vol = float(np.std(net) * np.sqrt(252) + 1e-12)
    sharpe = (ann_ret - RF) / ann_vol
    eq = np.cumprod(1 + net); dd = float((eq / np.maximum.accumulate(eq) - 1).min())
    turn = float(np.mean(dwt) * 252)
    gross_sharpe = float(np.mean(strat) * 252 / (np.std(strat) * np.sqrt(252) + 1e-12))
    return dict(ann_ret=ann_ret, ann_vol=ann_vol, sharpe=sharpe, gross_sharpe=gross_sharpe,
                maxdd=dd, turnover=turn)


def _timed(rv_forecast, ret):
    tgt = TARGET_ANN_VOL / np.sqrt(252)            # daily target vol
    w = np.clip(tgt / np.sqrt(np.clip(rv_forecast, 1e-10, None)), 0, W_MAX)
    return w * ret, w


def ce_fee(net_a, net_b, gamma=2.0):
    """Annual management fee (certainty-equiv. gain) a mean-variance investor with risk aversion
    gamma would pay to switch from strategy A to B. >0 => B preferred. (Fleming-Kirby-Ostdiek)."""
    def ce(x):
        return np.mean(x) - 0.5 * gamma * np.var(x)
    return float((ce(net_b) - ce(net_a)) * 252)


def run_window(label, tr, te, pool, X_har, y_logrv, y_rv, dates, seeds):
    ret = _returns_aligned(dates)[te]
    rich = pool[:, :N_FOCAL]; rich_s = fp.scale_pool(pool, tr)[:, :N_FOCAL]
    LINX = np.hstack([rich, X_har])
    fc = {}
    fc["HAR"] = np.exp(ridge_readout(X_har[tr], y_logrv[tr], X_har[te])[0])
    fc["HAR-X"] = np.exp(ridge_readout(LINX[tr], y_logrv[tr], LINX[te])[0])
    ens = []
    for sd in seeds:
        D = np.hstack([ss.chimera_features_n(rich_s, N_FOCAL, (2.0,), sd), LINX])
        ens.append(ridge_readout(D[tr], y_logrv[tr], D[te])[0])
    fc["CHIMERA"] = np.exp(np.mean(ens, axis=0))

    print(f"\n=== {label}  (test {len(te)} days; target {TARGET_ANN_VOL:.0%} vol, "
          f"cost {COST*1e4:.0f}bp/turn, cap {W_MAX:g}x) ===")
    print(f"  {'strategy':<14}{'AnnRet':>8}{'AnnVol':>8}{'Sharpe':>8}{'netShrp':>8}"
          f"{'maxDD':>8}{'turn':>7}")
    nets = {}
    # buy & hold
    bh = ret.copy(); bh_stats = _stats(bh, np.ones_like(ret))
    nets["BuyHold"] = bh
    print(f"  {'BuyHold':<14}{bh_stats['ann_ret']:>8.3f}{bh_stats['ann_vol']:>8.3f}"
          f"{bh_stats['gross_sharpe']:>8.2f}{bh_stats['sharpe']:>8.2f}{bh_stats['maxdd']:>8.2f}{0.0:>7.1f}")
    rows = [dict(window=label, strategy="BuyHold", **bh_stats)]
    for name in ("HAR", "HAR-X", "CHIMERA"):
        strat, w = _timed(fc[name], ret)
        dwt = np.abs(np.diff(np.concatenate([[0.0], w])))
        nets[name] = strat - COST * dwt
        s = _stats(strat, w)
        rows.append(dict(window=label, strategy=name, **s))
        print(f"  {name+'-timed':<14}{s['ann_ret']:>8.3f}{s['ann_vol']:>8.3f}"
              f"{s['gross_sharpe']:>8.2f}{s['sharpe']:>8.2f}{s['maxdd']:>8.2f}{s['turnover']:>7.1f}")
    fee_hx = ce_fee(nets["HAR"], nets["HAR-X"])
    fee_ch = ce_fee(nets["HAR-X"], nets["CHIMERA"])
    print(f"  -> CE fee to switch HAR->HAR-X: {fee_hx*1e4:+.0f} bp/yr   "
          f"HAR-X->CHIMERA: {fee_ch*1e4:+.0f} bp/yr")
    return rows, fee_hx, fee_ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    seeds = (0, 1, 2) if args.quick else (0, 1, 2, 3, 4)
    t0 = time.time()
    d = fp.build_rich()
    pool, X_har = d["pool"], d["X_har"]
    y_logrv, y_rv = d["y_logrv"], d["y_rv"]
    dts = pd.to_datetime(d["dates"])

    print("#" * 84)
    print("VOLATILITY-TIMING BACKTEST (economic significance) — S&P-500, forecast-scaled exposure")
    print("#" * 84)

    allrows, fees = [], {}
    ntr = int(0.70 * len(y_logrv))
    r, fhx, fch = run_window("calm 2014-2020", np.arange(ntr), np.arange(ntr, len(y_logrv)),
                             pool, X_har, y_logrv, y_rv, d["dates"], seeds)
    allrows += r; fees["calm"] = (fhx, fch)
    if not args.quick:
        tr = np.where(dts < CRISIS_TR)[0]; te = np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0]
        r2, fhx2, fch2 = run_window("crisis 2007-2012 (GFC in test)", tr, te,
                                    pool, X_har, y_logrv, y_rv, d["dates"], seeds)
        allrows += r2; fees["crisis"] = (fhx2, fch2)

    print("\n" + "=" * 84)
    print("VERDICT (economic):")
    print("  - Informed realized-measure features (HAR-X) vs plain HAR: see CE fee (HAR->HAR-X).")
    print("  - Quantum vs its linear span (CHIMERA vs HAR-X): CE fee (HAR-X->CHIMERA).")
    print("    Honest expectation/finding: ~0 bp ⇒ no ECONOMIC quantum advantage, consistent with")
    print("    the statistical negative; the deployable lever is the realized-measure features.")
    if not args.quick:
        np.save("vol_timing_results.npy", dict(rows=allrows, fees=fees,
                target_vol=TARGET_ANN_VOL, cost=COST, w_max=W_MAX), allow_pickle=True)
        print(f"\nsaved vol_timing_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
