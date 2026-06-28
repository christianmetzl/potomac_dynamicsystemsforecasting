"""
canonical_har_baselines.py - run the NAMED canonical realized-volatility models that a
finance referee expects, addressing the critique "you invoke SHAR/HARQ but only run a
generic additive HAR-X."

Models (all forecast 1-step log-RV on the same .SPX rows/splits as axisB_rigorous):
  HAR     : ridge on [HAR_d, HAR_w, HAR_m]                                (weak bar)
  HAR-X   : ridge on [rich pool (first 10) + HAR]                         (our strong bar)
  SHAR    : ridge on [log RS+_{t-1}, log RS-_{t-1}, HAR_w, HAR_m]         (Patton-Sheppard 2015:
            signed semivariance on the daily lag; RS- = downside rsv, RS+ = rv5 - rsv)
  HAR-CJ  : ridge on [log C_{t-1}, log(1+J_{t-1}), HAR_w, HAR_m]          (Andersen-Bollerslev-
            Diebold 2007: continuous C = bipower BV, jump J = max(RV-BV,0))
  HARQ    : OLS in LEVEL space RV_t ~ RV_d + RV_d*sqrt(RQ) + RV_w + RV_m  (Bollerslev-Patton-
            Quaedvlieg 2016). RQ (realized quarticity) needs intraday returns we do not have
            for the bundled .SPX, so RQ is PROXIED by RV^2 (a documented fallback; the HARQ
            literature notes RQ scales ~RV^2). Labeled 'HARQ*' to flag the proxy.
  HEAVY   : HEAVY-RM realized-measure GARCH (Shephard-Sheppard 2010), the realized-GARCH-
            family representative, fit by QLIKE. (A full Hansen-Huang-Shek RealGARCH QMLE was
            unstable/degenerate on the pre-crisis-train split, so we use the robust HEAVY-RM.)
  CHIMERA : ridge on [quantum features(rich,n=10) + rich + HAR], 5-seed ensemble (as in paper)

We report RMSE(log-RV), QLIKE, MZ, and BOTH a MSE-loss and a QLIKE-loss Diebold-Mariano
(Newey-West HAC + HLN), Holm-adjusted. Two questions:
  Q1  Does any canonical named model beat HAR-X?  (is HAR-X a fair stand-in for them?)
  Q2  Does CHIMERA beat the BEST canonical model? (quantum vs the strongest classical)

Honest by construction; no V1 number is changed. Companion: results/canonical_baselines_findings.md
"""
import argparse
import time
import numpy as np
import pandas as pd

import feature_pool as fp
import scaling_sweep as ss
from vol_fair_benchmark import rmse, qlike, mz_r2, ridge_readout
from axisB_rigorous import dm_hac, holm

CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")
N_FOCAL = 10
SEEDS = (0, 1, 2, 3, 4)


def _qlike_vec(rv_true, var_pred):
    """Per-observation QLIKE loss (Patton 2011 robust form): s/h - log(s/h) - 1, s,h>0."""
    s = np.asarray(rv_true, float); h = np.clip(np.asarray(var_pred, float), 1e-12, None)
    r = s / h
    return r - np.log(r) - 1.0


def _ols(Xtr, ytr, Xte):
    """Plain OLS with intercept (level-space HARQ); returns test predictions."""
    A = np.hstack([np.ones((len(Xtr), 1)), Xtr])
    beta, *_ = np.linalg.lstsq(A, ytr, rcond=None)
    return np.hstack([np.ones((len(Xte), 1)), Xte]) @ beta


def build_canonical(dates):
    """Build canonical regressors aligned to the supervised target dates `dates`.
    All regressors use info at t-1; targets RV_t / log RV_t come from build_rich."""
    raw = fp._load_raw_spx()                       # rv, close, rsv, bv, medrv on canonical index
    rv = raw["rv"]
    rsv = raw["rsv"].clip(lower=1e-12)             # downside semivariance
    bv = raw["bv"].clip(lower=1e-12)               # bipower (continuous)
    rsp = (rv - rsv).clip(lower=1e-12)             # upside semivariance RS+ = RV - RS-
    jump = (rv - bv).clip(lower=0.0)               # jump variation
    logrv = np.log(rv)
    har = np.log(fp.vd.har_components(rv))         # HAR_d/w/m (log), same as everywhere

    feats = pd.DataFrame(index=rv.index)
    feats["logRSp_l1"] = np.log(rsp).shift(1)
    feats["logRSm_l1"] = np.log(rsv).shift(1)
    feats["logC_l1"] = np.log(bv).shift(1)
    feats["logJ_l1"] = np.log1p(jump).shift(1)
    feats["RV_l1"] = rv.shift(1)                   # level (HARQ)
    feats["RQ_l1"] = (rv ** 2).shift(1)            # RQ PROXY = RV^2 (intraday RQ unavailable)
    feats["RV_w"] = rv.rolling(5).mean().shift(1)
    feats["RV_m"] = rv.rolling(22).mean().shift(1)
    feats["har_d"] = har["rv_d"]; feats["har_w"] = har["rv_w"]; feats["har_m"] = har["rv_m"]
    feats["ret"] = (100.0 * np.log(raw["close"])).diff()
    feats = feats.reindex(pd.to_datetime(dates))   # align to supervised target dates
    return feats


def heavy_rm(rv_all, ntr, te_idx):
    """HEAVY-RM realized-measure GARCH (Shephard & Sheppard 2010) — the realized-GARCH-family
    representative; robust where a full Hansen-Huang-Shek RealGARCH QMLE is unstable on a
    pre-crisis-train / crisis-test split. Conditional mean of the realized measure follows a
    GARCH(1,1) recursion driven by the realized measure itself:
        mu_t = w + a*RV_{t-1} + b*mu_{t-1}   (level space; w>0, a,b>=0, a+b<1)
    fit by QLIKE on the TRAIN prefix [0,ntr); 1-step forecasts roll through test using realized
    RV_{t-1} (observed). Returns RV-level forecasts on te_idx (or None on failure)."""
    from scipy.optimize import minimize
    x = np.clip(np.asarray(rv_all, float), 1e-12, None)
    n = len(x); mx = float(x[:ntr].mean())

    def loss(p):
        w, a, b = p
        if w <= 0 or a < 0 or b < 0 or a + b >= 0.999:
            return 1e10
        mu = mx; L = 0.0
        for t in range(1, ntr):                      # QLIKE on train prefix only
            mu = w + a * x[t - 1] + b * mu
            if mu <= 0:
                return 1e10
            L += x[t] / mu + np.log(mu)
        return L / ntr if np.isfinite(L) else 1e10

    try:
        res = minimize(loss, np.array([mx * 0.05, 0.4, 0.55]), method="Nelder-Mead",
                       options=dict(maxiter=3000, xatol=1e-12, fatol=1e-8))
        w, a, b = res.x
        if w <= 0 or a < 0 or b < 0 or a + b >= 0.999:
            return None
        mu = np.empty(n); mu[0] = mx
        for t in range(1, n):
            mu[t] = w + a * x[t - 1] + b * mu[t - 1]
        out = mu[te_idx]
        return out if np.all(np.isfinite(out)) and np.all(out > 0) else None
    except Exception:
        return None


def run_window(label, feats, pool, X_har, y_logrv, y_rv, tr, te):
    yT_log, yT_rv = y_logrv[te], y_rv[te]
    rich = pool[:, :N_FOCAL]
    rich_s = fp.scale_pool(pool, tr)[:, :N_FOCAL]
    LINX = np.hstack([rich, X_har])

    def met(pred_log):
        v = np.exp(pred_log)
        return dict(rmse=rmse(yT_log, pred_log), qlike=qlike(yT_rv, v), mz=mz_r2(yT_rv, v),
                    pred=pred_log)

    preds = {}
    # HAR / HAR-X (log-space ridge)
    preds["HAR"] = met(ridge_readout(X_har[tr], y_logrv[tr], X_har[te])[0])
    preds["HAR-X"] = met(ridge_readout(LINX[tr], y_logrv[tr], LINX[te])[0])
    # SHAR
    Xsh = feats[["logRSp_l1", "logRSm_l1", "har_w", "har_m"]].values
    preds["SHAR"] = met(ridge_readout(Xsh[tr], y_logrv[tr], Xsh[te])[0])
    # HAR-CJ
    Xcj = feats[["logC_l1", "logJ_l1", "har_w", "har_m"]].values
    preds["HAR-CJ"] = met(ridge_readout(Xcj[tr], y_logrv[tr], Xcj[te])[0])
    # HARQ* (level-space OLS, RQ proxied by RV^2; predict level -> log)
    Xhq = feats[["RV_l1", "RV_w", "RV_m"]].values.copy()
    rq_int = (feats["RV_l1"].values * np.sqrt(np.clip(feats["RQ_l1"].values, 0, None)))
    Xhq = np.column_stack([feats["RV_l1"].values, rq_int, feats["RV_w"].values, feats["RV_m"].values])
    lvl = _ols(Xhq[tr], y_rv[tr], Xhq[te])
    # BPQ (2016) insanity filter: replace negative or above-in-sample-max forecasts with the
    # estimation-sample mean. HARQ in levels is known to extrapolate badly without it.
    tr_mean, tr_max = float(y_rv[tr].mean()), float(y_rv[tr].max())
    lvl = np.where((lvl <= 0) | (lvl > tr_max), tr_mean, lvl)
    preds["HARQ*"] = met(np.log(np.clip(lvl, 1e-12, None)))
    # HEAVY-RM (realized-measure GARCH; chronological recursion, train is the prefix [0,ntr))
    ntr = int(tr.max()) + 1 if len(tr) else 0
    rg = heavy_rm(y_rv, ntr, te)
    if rg is not None:
        preds["HEAVY"] = met(np.log(np.clip(rg, 1e-12, None)))
    # CHIMERA (5-seed ensemble, nests HAR-X)
    ens = []
    for sd in SEEDS:
        F = ss.chimera_features_n(rich_s, N_FOCAL, (2.0,), sd)
        D = np.hstack([F, LINX])
        ens.append(ridge_readout(D[tr], y_logrv[tr], D[te])[0])
    preds["CHIMERA"] = met(np.mean(ens, axis=0))
    return preds, yT_log, yT_rv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    d = fp.build_rich()
    pool, X_har = d["pool"], d["X_har"]
    y_logrv, y_rv = d["y_logrv"], d["y_rv"]
    dts = pd.to_datetime(d["dates"])
    feats = build_canonical(d["dates"])

    print("#" * 96)
    print("CANONICAL REALIZED-VOL BASELINES vs HAR-X and CHIMERA (n=10) — MSE-loss & QLIKE-loss DM")
    print("  SHAR (Patton-Sheppard) · HAR-CJ (ABD) · HARQ* (BPQ; RQ=RV^2 proxy) · HEAVY-RM (Shephard-Sheppard)")
    print("#" * 96)

    windows = [("crisis 2007-2012 (GFC in test)",
                np.where(dts < CRISIS_TR)[0],
                np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0])]
    if not args.quick:
        ntr = int(0.70 * len(y_logrv))
        windows.append(("calm 2014-2020 (robustness)", np.arange(ntr), np.arange(ntr, len(y_logrv))))

    fam_mse, fam_ql, rows = {}, {}, []
    order = ["HAR", "SHAR", "HAR-CJ", "HARQ*", "HEAVY", "HAR-X", "CHIMERA"]
    for label, tr, te in windows:
        preds, yT_log, yT_rv = run_window(label, feats, pool, X_har, y_logrv, y_rv, tr, te)
        harx = preds["HAR-X"]; chim = preds["CHIMERA"]
        harx_mse = (harx["pred"] - yT_log) ** 2
        harx_ql = _qlike_vec(yT_rv, np.exp(harx["pred"]))
        chim_mse = (chim["pred"] - yT_log) ** 2
        chim_ql = _qlike_vec(yT_rv, np.exp(chim["pred"]))
        print(f"\n=== {label} ===")
        print(f"  {'model':<10}{'RMSE':>9}{'QLIKE':>12}{'MZ_R2':>8}"
              f"{'DMvsHARX(MSE)':>15}{'p':>7}{'DMvsHARX(QL)':>14}{'p':>7}")
        for name in order:
            if name not in preds:
                print(f"  {name:<10}     n/a (RealGARCH optimizer did not converge)"); continue
            m = preds[name]; v = np.exp(m["pred"])
            mse_l = (m["pred"] - yT_log) ** 2; ql_l = _qlike_vec(yT_rv, v)
            if name == "HAR-X":
                ds=dp=qs=qp=np.nan
            else:
                ds, dp = dm_hac(mse_l, harx_mse)       # <0 => model better than HAR-X (MSE)
                qs, qp = dm_hac(ql_l, harx_ql)         # <0 => model better than HAR-X (QLIKE)
            rows.append(dict(window=label, model=name, rmse=m["rmse"], qlike=m["qlike"],
                             mz=m["mz"], dm_mse=ds, p_mse=dp, dm_ql=qs, p_ql=qp))
            ms = "" if name == "HAR-X" else f"{ds:>+15.2f}{dp:>7.3f}{qs:>+14.2f}{qp:>7.3f}"
            print(f"  {name:<10}{m['rmse']:>9.4f}{m['qlike']:>12.4f}{m['mz']:>8.3f}{ms}")
        # CHIMERA vs the BEST canonical (lowest RMSE among canonical classical models)
        canon = {k: preds[k] for k in ("HAR", "SHAR", "HAR-CJ", "HARQ*", "HEAVY") if k in preds}
        best = min(canon, key=lambda k: canon[k]["rmse"])
        bmse = (canon[best]["pred"] - yT_log) ** 2; bql = _qlike_vec(yT_rv, np.exp(canon[best]["pred"]))
        cs, cp = dm_hac(chim_mse, bmse); cqs, cqp = dm_hac(chim_ql, bql)
        fam_mse[f"{label}:CHIMERAvsBEST({best})"] = cp
        fam_ql[f"{label}:CHIMERAvsBEST({best})_QL"] = cqp
        print(f"  -> best canonical = {best} (RMSE {canon[best]['rmse']:.4f}); "
              f"CHIMERA vs it: DM(MSE)={cs:+.2f} p={cp:.3f} | DM(QLIKE)={cqs:+.2f} p={cqp:.3f}")

    adj = holm({**fam_mse, **fam_ql})
    # Q1: did any named canonical model significantly beat HAR-X (DM<0 & raw p<0.05) on either loss?
    CANON = {"HAR", "SHAR", "HAR-CJ", "HARQ*", "HEAVY"}
    q1 = [(r["window"], r["model"]) for r in rows if r["model"] in CANON
          and ((r.get("dm_mse") is not None and r["dm_mse"] < 0 and r["p_mse"] < 0.05)
               or (r.get("dm_ql") is not None and r["dm_ql"] < 0 and r["p_ql"] < 0.05))]
    print("\n" + "=" * 96)
    print("VERDICT (Holm-adjusted across windows):")
    print(f"  Q1 — canonical models that significantly beat HAR-X (raw p<0.05, either loss): "
          f"{q1 if q1 else 'NONE — HAR-X is a fair, strong stand-in for the named models'}")
    print("  Q2 — CHIMERA vs the BEST canonical model (Holm-adjusted):")
    for k in sorted({**fam_mse, **fam_ql}):
        print(f"      {k:<48} Holm p={adj[k]:.3f}")
    print("  (CHIMERA 'beats' a model only if DM<0 AND Holm p<0.05; see per-window lines for signs.)")
    if not args.quick:
        np.save("canonical_baselines_results.npy",
                dict(rows=rows, family_mse=fam_mse, family_ql=fam_ql, holm=adj), allow_pickle=True)
        print(f"\nsaved canonical_baselines_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] not written (preserve committed artifact)  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
