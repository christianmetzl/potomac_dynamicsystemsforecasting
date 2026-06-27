"""
regime_adaptive_qrc.py - test of CHIMERA Innovation 3 (Regime-Adaptive Hamiltonian
Switching) on financial realized volatility, crisis window.

Mechanism: a quantum reservoir that swaps its Hamiltonian by market regime -
transverse-field Ising in calm regimes, Heisenberg in turbulent regimes - with the
switch driven by Bayesian Online Changepoint Detection (Adams & MacKay 2007,
Normal-Gamma model) on log-RV. Everything is causal: the regime used to forecast
RV_t is the one inferred from information up to t-1 (no look-ahead).

Controls isolate WHERE any gain comes from:
  HAR-RV            linear benchmark
  Static-Ising      quantum, Ising only      (= the best static config so far)
  Static-Heisenberg quantum, Heisenberg only  (is one Hamiltonian just better?)
  Regime-Adaptive   Ising<->Heisenberg switched by BOCPD   [Innovation 3]
If Regime-Adaptive beats BOTH statics, the *switching* adds value - not merely a
better fixed Hamiltonian.

All three reservoirs share the SAME coupling matrix per seed (only the Hamiltonian
form differs), identical [0,1]-scaled lag inputs, and the HAR-subsuming hybrid
readout. 3 seeds, ensembled.

Pre-registered hypothesis (stated before running): the adaptive model's advantage is
concentrated at regime TRANSITIONS (high changepoint probability), where the static
HAR/Ising models lag. Reported via a transition-vs-stable split of the test set.

Window: train 2000-01..2006-12, test 2007-01..2012-12 (GFC + recovery in test).
Data: Oxford-Man .SPX rv5 (gold-standard 5-min realized variance).

Team EIGENNEXUS | GIC 2026 - Phase 2 (Innovation 3, honest test)
"""
import numpy as np
import pandas as pd
from scipy import stats
import volatility_data as vd
from delay_qrc import DelayEmbeddingQRC
from vol_fair_benchmark import (
    LAGS, N_QUBITS, SEEDS, rmse, qlike, mz_r2, dm_test, model_confidence_set, ridge_readout,
)

TRAIN_END = pd.Timestamp("2007-01-01")
TEST_END = pd.Timestamp("2013-01-01")
TAU = 2.0
HAZARD_LAMBDA = 125.0   # prior expected regime length ~6 months (preset, not tuned)


def bocpd_clean(x, hazard_lambda=HAZARD_LAMBDA, kappa0=1.0, alpha0=1.0, rmax=400):
    """Causal BOCPD (Normal-Gamma). Returns cp_prob[t], MAP run-length[t]."""
    x = np.asarray(x, float); n = len(x)
    init = x[:min(250, n)]
    mu0 = float(init.mean()); beta0 = float(init.var()) + 1e-6
    H = 1.0 / hazard_lambda
    mu = np.array([mu0]); ka = np.array([float(kappa0)]); al = np.array([float(alpha0)]); be = np.array([beta0])
    R = np.array([1.0]); cp = np.zeros(n); mrl = np.zeros(n, int)
    for t in range(n):
        xt = x[t]
        scale = np.sqrt(be * (ka + 1.0) / (al * ka)); dof = 2.0 * al
        pred = stats.t.pdf((xt - mu) / scale, dof) / scale
        growth = R * pred * (1.0 - H)
        cpm = float(np.sum(R * pred * H))
        # posterior update of sufficient stats (use pre-update values)
        mu_new = (ka * mu + xt) / (ka + 1.0)
        be_new = be + 0.5 * ka * (xt - mu) ** 2 / (ka + 1.0)
        ka_new = ka + 1.0
        al_new = al + 0.5
        mu = np.concatenate([[mu0], mu_new])
        ka = np.concatenate([[kappa0], ka_new])
        al = np.concatenate([[alpha0], al_new])
        be = np.concatenate([[beta0], be_new])
        R = np.concatenate([[cpm], growth]); R /= R.sum()
        if len(R) > rmax:
            R = R[:rmax]; mu = mu[:rmax]; ka = ka[:rmax]; al = al[:rmax]; be = be[:rmax]; R /= R.sum()
        cp[t] = R[0]; mrl[t] = int(np.argmax(R))
    return cp, mrl


def main():
    df = vd.load_spx_rv()
    logrv = df["logrv"].values
    cp, mrl = bocpd_clean(logrv)
    seg = np.array([logrv[max(0, s - max(1, mrl[s]) + 1):s + 1].mean() for s in range(len(logrv))])
    theta = float(np.median(logrv[df.index < TRAIN_END]))
    g = (seg > theta).astype(int)
    g_s = pd.Series(g, index=df.index); cp_s = pd.Series(cp, index=df.index)

    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    dates = pd.to_datetime(data["dates"])
    # regime / changepoint known at t-1 (causal for predicting RV_t)
    regime = g_s.shift(1).reindex(dates).fillna(0).to_numpy().astype(int)
    cpv = cp_s.shift(1).reindex(dates).fillna(cp_s.median()).to_numpy()

    Xlag, Xhar = data["X_lags"], data["X_har"]
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    tr = np.where(dates < TRAIN_END)[0]; te = np.where((dates >= TRAIN_END) & (dates < TEST_END))[0]

    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rng, 0.0, 1.0)
    LIN = np.hstack([Xlag, Xhar])

    print("=" * 86)
    print("CHIMERA Innovation 3 - Regime-Adaptive Hamiltonian Switching (Ising<->Heisenberg, BOCPD)")
    print(f"train {dates[tr[0]].date()}..{dates[tr[-1]].date()} (n={len(tr)}) | "
          f"test {dates[te[0]].date()}..{dates[te[-1]].date()} (n={len(te)})")
    hi_frac_tr = regime[tr].mean(); hi_frac_te = regime[te].mean()
    cpmax_date = dates[int(np.argmax(cpv))].date()
    print(f"BOCPD: high-vol regime share train={hi_frac_tr:.0%} test={hi_frac_te:.0%}; "
          f"max changepoint prob near {cpmax_date}")
    print("=" * 86)

    # static + adaptive feature maps, ensembled over seeds
    preds, perseed = {}, {}
    p, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te]); preds["HAR-RV"] = p

    sp = {k: [] for k in ["Static-Ising", "Static-Heisenberg", "Regime-Adaptive"]}
    sr = {k: [] for k in sp}
    for sd in SEEDS:
        qi = DelayEmbeddingQRC(n_qubits=N_QUBITS, tau=TAU, hamiltonian="ising",
                               hx=1.0, connectivity=0.5, seed=sd)
        qh = DelayEmbeddingQRC(n_qubits=N_QUBITS, tau=TAU, hamiltonian="heisenberg",
                               hx=1.0, delta=0.8, connectivity=0.5, seed=sd)
        FI = np.array([qi._step_features(w) for w in Q])
        FH = np.array([qh._step_features(w) for w in Q])
        sel = np.where(regime[:, None] == 1, FH, FI)   # regime-adaptive selection
        for name, F in [("Static-Ising", FI), ("Static-Heisenberg", FH), ("Regime-Adaptive", sel)]:
            D = np.hstack([F, LIN])
            pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
            sp[name].append(pr); sr[name].append(rmse(y_logrv[te], pr))
    for name in sp:
        preds[name] = np.mean(sp[name], axis=0); perseed[name] = sr[name]

    yT_log, yT_rv = y_logrv[te], y_rv[te]
    har_loss = (preds["HAR-RV"] - yT_log) ** 2
    isi_loss = (preds["Static-Ising"] - yT_log) ** 2
    print(f"\n{'Model':<19}{'RMSE(logRV)':>13}{'±seed':>8}{'QLIKE':>10}{'MZ R2':>8}{'DMvsHAR':>9}{'p':>7}")
    print("-" * 86)
    loss_dict = {}
    for name in ["HAR-RV", "Static-Ising", "Static-Heisenberg", "Regime-Adaptive"]:
        pp = preds[name]; var = np.exp(pp)
        r = rmse(yT_log, pp); q = qlike(yT_rv, var); mz = mz_r2(yT_rv, var)
        sdv = np.std(perseed[name]) if name in perseed else 0.0
        loss = (pp - yT_log) ** 2; loss_dict[name] = loss
        ds, dp = (0.0, 1.0) if name == "HAR-RV" else dm_test(loss, har_loss)
        star = "" if (np.isnan(dp) or dp >= 0.05 or ds > 0) else "  *beats HAR"
        print(f"{name:<19}{r:>13.4f}{sdv:>8.4f}{q:>10.4f}{mz:>8.3f}{ds:>9.2f}{dp:>7.3f}{star}")
    print("-" * 86)

    ad = (preds["Regime-Adaptive"] - yT_log) ** 2
    s, p1 = dm_test(ad, isi_loss)
    print(f"Regime-Adaptive vs Static-Ising (does switching help?): DM={s:.2f} p={p1:.3f}"
          f"  {'-> switching helps' if (not np.isnan(p1) and s<0 and p1<0.05) else '-> n.s.'}")
    s, p2 = dm_test(ad, (preds['Static-Heisenberg'] - yT_log) ** 2)
    print(f"Regime-Adaptive vs Static-Heisenberg: DM={s:.2f} p={p2:.3f}")

    # ---- pre-registered transition-conditional test ----
    cpt = cpv[te]
    thr = np.quantile(cpt, 2 / 3)
    trans = cpt >= thr; stab = ~trans
    print("\nTransition-conditional (test split by BOCPD changepoint prob, top tercile = transition):")
    for lbl, m in [("TRANSITION", trans), ("stable", stab)]:
        ri = rmse(yT_log[m], preds["Static-Ising"][m])
        ra = rmse(yT_log[m], preds["Regime-Adaptive"][m])
        rh = rmse(yT_log[m], preds["HAR-RV"][m])
        print(f"  {lbl:<11} n={m.sum():<4} HAR={rh:.4f}  Static-Ising={ri:.4f}  "
              f"Regime-Adaptive={ra:.4f}  (Adaptive-Ising={ra-ri:+.4f})")

    surv, mp = model_confidence_set(loss_dict)
    print(f"\nModel Confidence Set (95%): {{{', '.join(surv)}}}")
    print("  MCS p: " + ", ".join(f"{k}={v:.3f}" for k, v in mp.items()))


if __name__ == "__main__":
    main()
