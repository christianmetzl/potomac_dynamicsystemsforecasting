"""
vol_crisis_benchmark.py - crisis-inclusive companion to vol_fair_benchmark.

Same models, inputs, readout discipline, and metrics, but a regime-stressed split:
  train 2000-01 .. 2006-12  (calm/pre-crisis, ~1750 days)
  test  2007-01 .. 2012-12  (GFC 2008 + recovery + 2011 Euro crisis IN THE TEST SET)

Pre-registered question (stated before seeing calm-window results): do the quantum
edge and the multi-scale bank show more value where HAR's linear form is most
stressed and genuine multi-timescale / regime structure is present?
"""
import numpy as np
import pandas as pd
import volatility_data as vd
from vol_fair_benchmark import (
    LAGS, N_QUBITS, SEEDS, rmse, qlike, mz_r2, dm_test, model_confidence_set,
    ridge_readout, esn_features, chimera_features,
)

TRAIN_END = pd.Timestamp("2007-01-01")
TEST_END = pd.Timestamp("2013-01-01")


def main():
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    Xlag, Xhar = data["X_lags"], data["X_har"]
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    dts = pd.to_datetime(data["dates"])

    tr = np.where(dts < TRAIN_END)[0]
    te = np.where((dts >= TRAIN_END) & (dts < TEST_END))[0]

    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rng, 0.0, 1.0)
    LIN = np.hstack([Xlag, Xhar])

    print("=" * 84)
    print("CHIMERA-QRC Track A - CRISIS-INCLUSIVE split (GFC 2008 in test)")
    print(f"train {dts[tr[0]].date()}..{dts[tr[-1]].date()} (n={len(tr)}) | "
          f"test {dts[te[0]].date()}..{dts[te[-1]].date()} (n={len(te)}, peak vol day 2008-10-10)")
    print("=" * 84)

    preds, perseed = {}, {}
    p, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te]); preds["HAR-RV"] = p
    for name, kind, arg in [("ESN-108", "esn", 108), ("ESN-400", "esn", 400),
                            ("CHIMERA-1scale", "chim", (2.0,)),
                            ("CHIMERA-3scale", "chim", (1.0, 2.0, 4.0))]:
        sp, sr = [], []
        for sd in SEEDS:
            F = esn_features(Q, arg, sd) if kind == "esn" else chimera_features(Q, arg, sd)
            D = np.hstack([F, LIN])
            pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
            sp.append(pr); sr.append(rmse(y_logrv[te], pr))
        preds[name] = np.mean(sp, axis=0); perseed[name] = sr

    yT_log, yT_rv = y_logrv[te], y_rv[te]
    har_loss = (preds["HAR-RV"] - yT_log) ** 2
    print(f"\n{'Model':<16}{'RMSE(logRV)':>13}{'±seed':>8}{'QLIKE':>10}{'MZ R2':>8}{'DMvsHAR':>9}{'p':>7}")
    print("-" * 84)
    loss_dict = {}
    for name in ["HAR-RV", "ESN-108", "ESN-400", "CHIMERA-1scale", "CHIMERA-3scale"]:
        pp = preds[name]; var = np.exp(pp)
        r = rmse(yT_log, pp); q = qlike(yT_rv, var); mz = mz_r2(yT_rv, var)
        sdv = np.std(perseed[name]) if name in perseed else 0.0
        loss = (pp - yT_log) ** 2; loss_dict[name] = loss
        ds, dp = (0.0, 1.0) if name == "HAR-RV" else dm_test(loss, har_loss)
        star = "" if (np.isnan(dp) or dp >= 0.05 or ds > 0) else "  *beats HAR"
        print(f"{name:<16}{r:>13.4f}{sdv:>8.4f}{q:>10.4f}{mz:>8.3f}{ds:>9.2f}{dp:>7.3f}{star}")
    print("-" * 84)

    c3 = (preds["CHIMERA-3scale"] - yT_log) ** 2
    c1 = (preds["CHIMERA-1scale"] - yT_log) ** 2
    e1 = (preds["ESN-108"] - yT_log) ** 2
    s, p1 = dm_test(c3, e1); print(f"CHIMERA-3scale vs ESN-108 (matched): DM={s:.2f} p={p1:.3f}")
    s, p2 = dm_test(c3, c1); print(f"CHIMERA-3scale vs CHIMERA-1scale (multi vs single): DM={s:.2f} p={p2:.3f}")
    surv, mp = model_confidence_set(loss_dict)
    print(f"\nModel Confidence Set (95%): {{{', '.join(surv)}}}")
    print("  MCS p: " + ", ".join(f"{k}={v:.3f}" for k, v in mp.items()))


if __name__ == "__main__":
    main()
