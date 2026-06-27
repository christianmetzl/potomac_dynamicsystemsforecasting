"""
gk_validation.py - independent, current-era validation of the CHIMERA-QRC finding.

Data: SPY daily OHLCV 2022-2026, pulled by us directly from Massive.com via our own
read-only n8n workflow (massive_spy_daily.csv). No third-party RV library, no
pre-filtered tables - a fully self-controlled, current series.

Vol target: Garman-Klass daily variance proxy (uses OHLC, ~7x more efficient than
close-to-close):  sigma2 = 0.5*(ln(H/L))^2 - (2 ln2 - 1)*(ln(C/O))^2

We run the SAME models, inputs, readout discipline and metrics as the Oxford-Man
benchmark. Absolute errors are NOT comparable across datasets (different estimator);
only the RELATIVE model ranking transfers. This asks one question: does
"CHIMERA beats the matched/larger classical reservoir and reaches the HAR/best tier"
replicate on an independent, current dataset with a different vol estimator?

Split: train 2022-01..2024-12, test 2025-01..2026-05 (truly recent, post-Oxford-Man).

Team EIGENNEXUS | GIC 2026 - Phase 2 (independent current-era robustness check)
"""
import numpy as np
import pandas as pd
from volatility_data import _find
from vol_fair_benchmark import (
    LAGS, N_QUBITS, SEEDS, rmse, qlike, mz_r2, dm_test, model_confidence_set,
    ridge_readout, esn_features, chimera_features,
)

TEST_START = pd.Timestamp("2025-01-01")


def garman_klass(o, h, l, c):
    lhl = np.log(h / l) ** 2
    lco = np.log(c / o) ** 2
    gk = 0.5 * lhl - (2 * np.log(2) - 1) * lco
    return np.clip(gk, 1e-10, None)


def build_supervised_gk(dates, var, lags=LAGS, horizon=1):
    logv = np.log(var)
    maxlag = max(lags)
    idx = np.arange(maxlag, len(logv) - horizon)
    X_lags = np.column_stack([logv[idx - L] for L in lags])
    # HAR components from the variance level (daily / weekly / monthly), logged
    daily = var[idx - 1]
    weekly = np.array([var[i - 5:i].mean() for i in idx])
    monthly = np.array([var[i - 22:i].mean() for i in idx])
    X_har = np.log(np.column_stack([daily, weekly, monthly]))
    y_logrv = logv[idx + horizon]
    y_rv = var[idx + horizon]
    return dict(X_lags=X_lags, X_har=X_har, y_logrv=y_logrv, y_rv=y_rv,
                dates=dates[idx + horizon])


def main():
    df = pd.read_csv(_find("massive_spy_daily.csv"), parse_dates=["date"]).sort_values("date")
    o, h, l, c = (df[k].to_numpy(float) for k in ["open", "high", "low", "close"])
    gk = garman_klass(o, h, l, c)
    dts = df["date"].to_numpy()
    ann = np.sqrt(gk.mean() * 252) * 100
    print("=" * 84)
    print("INDEPENDENT current-era validation - SPY Garman-Klass vol (self-pulled Massive bars)")
    print(f"bars {pd.Timestamp(dts[0]).date()}..{pd.Timestamp(dts[-1]).date()} (n={len(gk)}), "
          f"mean GK ann.vol = {ann:.1f}%")
    print("=" * 84)

    data = build_supervised_gk(dts, gk, lags=LAGS, horizon=1)
    Xlag, Xhar = data["X_lags"], data["X_har"]
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    d = pd.to_datetime(data["dates"])
    tr = np.where(d < TEST_START)[0]
    te = np.where(d >= TEST_START)[0]

    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rng, 0.0, 1.0)
    LIN = np.hstack([Xlag, Xhar])
    print(f"train {d[tr[0]].date()}..{d[tr[-1]].date()} (n={len(tr)}) | "
          f"test {d[te[0]].date()}..{d[te[-1]].date()} (n={len(te)})\n")

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
    print(f"{'Model':<16}{'RMSE(logGK)':>13}{'±seed':>8}{'QLIKE':>10}{'MZ R2':>8}{'DMvsHAR':>9}{'p':>7}")
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
