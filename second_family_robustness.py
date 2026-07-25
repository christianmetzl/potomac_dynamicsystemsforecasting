"""
second_family_robustness.py — is the no-advantage negative specific to the
transverse-field *Ising* reservoir, or does it hold for a different Hamiltonian
family?

We swap the reservoir Hamiltonian to **Heisenberg (XXZ)** — a genuinely different
entangling dynamics (H = Σ J_ij (X_iX_j + Y_iY_j + Δ Z_iZ_j) + h Σ Z_i) — and re-run,
on the SAME Oxford-Man S&P 500 RV data and the SAME nested HAR-X readout as the headline:
  (1) the decisive forecasting test  — does the Heisenberg reservoir beat HAR-X?
  (2) the kernel-distinctness diagnostic (Huang et al. 2021 geometric difference g).
Everything else is identical to `vol_fair_benchmark` / `kernel_analysis`.

Result is reported as measured. Reproduce: `python3 second_family_robustness.py`
"""
import time
import numpy as np
from numpy.linalg import eigh, inv, norm

import volatility_data as vd
from vol_fair_benchmark import esn_features, ridge_readout, rmse, LAGS, N_QUBITS
from multiscale_chimera import MultiScaleCHIMERA

SEEDS = list(range(8))          # match the headline decisive test's seed count


def chimera_features_family(Q, taus, seed, family):
    ch = MultiScaleCHIMERA(n_qubits=N_QUBITS, taus=taus, hamiltonian=family,
                           hx=1.0, connectivity=0.5, seed=seed)
    ch._reset_feedback()
    return np.array([ch._all_features(w) for w in Q])


def standardize(F):
    mu, sd = F.mean(0), F.std(0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    return (F - mu) / sd


def lin_kernel(F):
    F = standardize(F)
    K = F @ F.T
    return K * (K.shape[0] / np.trace(K))


def kta(K, yv):
    n = K.shape[0]
    H = np.eye(n) - np.ones((n, n)) / n
    Kc = H @ K @ H
    Y = np.outer(yv, yv)
    return float((Kc * Y).sum() / (norm(Kc) * norm(Y) + 1e-12))


def geom_diff(KA, KB, reg=1e-3):
    n = KA.shape[0]
    wB, VB = eigh(KB)
    wB = np.clip(wB, 0, None)
    KBh = (VB * np.sqrt(wB)) @ VB.T
    M = KBh @ inv(KA + reg * np.eye(n)) @ KBh
    return float(np.sqrt(np.clip(eigh(M)[0], 0, None).max()))


def main():
    t0 = time.time()
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    Xlag, Xhar = data["X_lags"], data["X_har"]
    y = data["y_logrv"]
    tr, te = vd.make_splits(len(y), train_frac=0.70)
    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0)
    rngd = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rngd, 0.0, 1.0)
    LIN = np.hstack([Xlag, Xhar])          # the HAR-X block (lags + HAR components)

    # ---- baselines (linear) ----
    p_harx, _ = ridge_readout(LIN[tr], y[tr], LIN[te]); r_harx = rmse(y[te], p_harx)
    p_har, _ = ridge_readout(Xhar[tr], y[tr], Xhar[te]); r_har = rmse(y[te], p_har)

    print("=" * 78)
    print("Second reservoir family — is the no-advantage negative Ising-specific?")
    print("  Oxford-Man S&P500 RV | nested HAR-X readout | 8 seeds | identical pipeline")
    print("=" * 78)
    print(f"  HAR (linear, HAR only)        RMSE(logRV) = {r_har:.4f}")
    print(f"  HAR-X (linear, lags+HAR)      RMSE(logRV) = {r_harx:.4f}   <- the control to beat")

    # ---- reservoir forecasting, both families, nested readout ----
    fam_rmse = {}
    for family in ["ising", "heisenberg"]:
        rs = []
        for sd in SEEDS:
            F = chimera_features_family(Q, (2.0,), sd, family)
            D = np.hstack([F, LIN])
            pr, _ = ridge_readout(D[tr], y[tr], D[te])
            rs.append(rmse(y[te], pr))
        fam_rmse[family] = (float(np.mean(rs)), float(np.std(rs)))
        m, s = fam_rmse[family]
        verdict = "beats HAR-X" if m < r_harx else "does NOT beat HAR-X"
        print(f"  CHIMERA-{family:<10} (nested)  RMSE(logRV) = {m:.4f} +/- {s:.4f}   "
              f"(Δ vs HAR-X {m - r_harx:+.4f}) -> {verdict}")

    # ---- kernel distinctness, both families (subsample 800) ----
    N = 800
    idx = np.linspace(0, len(tr) - 1, N).astype(int)
    trk = np.array(tr)[idx]
    ytr = y[trk]; yc = ytr - ytr.mean()
    F108 = esn_features(Q[trk], 108, 0); K108 = lin_kernel(F108)
    F108b = esn_features(Q[trk], 108, 1); K108b = lin_kernel(F108b)
    g_ctrl = geom_diff(K108, K108b)
    print("\n  kernel geometric difference g(ESN-108 || CHIMERA-family)  "
          f"[classical-vs-classical control = {g_ctrl:.2f}]")
    fam_g = {}
    for family in ["ising", "heisenberg"]:
        FQ = chimera_features_family(Q[trk], (2.0,), 0, family)
        KQ = lin_kernel(FQ)
        g = geom_diff(K108, KQ)
        kpf = kta(KQ, yc) / FQ.shape[1] * 1000
        kpf108 = kta(K108, yc) / 108 * 1000
        fam_g[family] = (g, kpf, kpf108)
        print(f"    CHIMERA-{family:<10}  g = {g:7.2f}   "
              f"KTA/feature = {kpf:.3f} vs ESN-108 {kpf108:.3f} (x1e-3)")

    print("\n  VERDICT:")
    both_lose = all(fam_rmse[f][0] >= r_harx for f in fam_rmse)
    both_distinct = all(fam_g[f][0] > 5 * g_ctrl for f in fam_g)
    print(f"    both families kernel-distinct (g >> control): {both_distinct}")
    print(f"    neither family beats HAR-X on RMSE:           {both_lose}")
    print("    => the no-advantage negative is NOT specific to the Ising reservoir."
          if (both_lose and both_distinct) else
          "    => see numbers above (mixed result — report as measured).")
    print(f"[done in {time.time() - t0:.1f}s]")
    return dict(r_har=r_har, r_harx=r_harx, fam_rmse=fam_rmse, fam_g=fam_g, g_ctrl=g_ctrl)


if __name__ == "__main__":
    main()
