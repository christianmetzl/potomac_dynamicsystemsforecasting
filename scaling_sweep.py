"""
scaling_sweep.py - CHIMERA-QRC Phase-3 scaling study (the decisive H0 test).

WHAT THIS PRODUCES
------------------
For a sweep over qubit count n, on the REAL Oxford-Man S&P 500 realized-variance
data, this script emits the curves the Phase-2 paper (Section 7) pre-registered as
the falsifiable test of H0, plus the noise characterization the Phase-3 brief asks
for (depolarizing + amplitude damping):

  1. g(n)        - geometric difference g(ESN(n) || CHIMERA(n)) [Huang et al. 2021]
                   (how badly the matched classical reservoir fails to reproduce the
                    quantum kernel) vs the classical-classical control g(ESN||ESN').
  2. MZ-gap(n)   - Mincer-Zarnowitz R^2 (CHIMERA) - R^2 (HAR) on the crisis window
                   (GFC 2008 in the test set), with a Diebold-Mariano p-value.
  3. rank(n)     - effective dimension D_eff and numerical rank of the quantum kernel
                   (the H4 encoding-density signal).
  4. noise sweep - RMSE/QLIKE/MZ under depolarizing and amplitude-damping channels
                   at matched n (the brief's "realistic noise models").

Outcomes are adjudicated against thresholds fixed in `preregistration.py` BEFORE
running, and the script reports honestly - including the input-bottleneck caveat:
with a fixed 8-lag univariate encoder, qubits beyond ~8 carry NO new input, so
g(n)/MZ-gap are expected to saturate until the multivariate / data-re-uploading
encoder (Axis B) lands. A flat curve here is the *motivation* for Axis B, not a
refutation of H0 at richer encodings.

The pure-NumPy statevector engine forms the dense propagator U = exp(-iH tau)
(2^n x 2^n), which is memory-feasible up to ~12 qubits; n>=13-20 (the brief's upper
range) requires sparse / Trotter evolution and is a logged follow-up (see
MAX_DENSE_N). Nothing is silently capped: the frontier reached is printed.

Usage:
  python3 scaling_sweep.py                # default sweep
  python3 scaling_sweep.py --quick        # fast smoke (small n, 1 seed, no noise)
  python3 scaling_sweep.py --no-noise     # skip the noise sweep
  python3 scaling_sweep.py --ns 5 8 10 12 # custom qubit counts

Team EIGENNEXUS | GIC 2026 - Phase 3 (Track A)
"""
import argparse
import time
import numpy as np
from numpy.linalg import eigh, inv, norm

import volatility_data as vd
from vol_fair_benchmark import (
    LAGS, SEEDS, rmse, qlike, mz_r2, dm_test, ridge_readout, esn_features,
)
from multiscale_chimera import MultiScaleCHIMERA
import preregistration as prereg

import pandas as pd

# Dense U = exp(-iH tau) is 2^n x 2^n complex128; ~12 qubits is the practical
# statevector frontier for this pure-NumPy engine on a single node.
MAX_DENSE_N = 12
# Density-matrix noise simulation is 2^n x 2^n per channel application; keep the
# exact noisy sweep to small n (exact rho is 4^n in memory).
MAX_NOISE_N = 10

CRISIS_TRAIN_END = pd.Timestamp("2007-01-01")
CRISIS_TEST_END = pd.Timestamp("2013-01-01")
KERNEL_SUBSAMPLE = 800   # matches kernel_analysis.py for comparable g values


# ---------------------------------------------------------------------------
# Kernel-geometry helpers (copied from kernel_analysis.py so we do NOT import
# that module, which executes its full analysis at import time).
# ---------------------------------------------------------------------------
def standardize(F):
    mu, sd = F.mean(0), F.std(0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    return (F - mu) / sd


def lin_kernel(F):
    F = standardize(F)
    K = F @ F.T
    return K * (K.shape[0] / np.trace(K))   # trace-normalize to N


def eff_dim(K):
    w = np.clip(eigh(K)[0], 0, None)
    return (w.sum() ** 2) / ((w ** 2).sum() + 1e-12)


def num_rank(K, tol=1e-6):
    w = np.clip(eigh(K)[0], 0, None)
    return int((w > tol * w.max()).sum())


def kta(K, yv):
    n = K.shape[0]
    H = np.eye(n) - np.ones((n, n)) / n
    Kc = H @ K @ H
    Y = np.outer(yv, yv)
    return float((Kc * Y).sum() / (norm(Kc) * norm(Y) + 1e-12))


def geom_diff(KA, KB, reg=1e-3):
    """g(KA || KB): large => kernel A cannot reproduce kernel B's geometry."""
    n = KA.shape[0]
    wB, VB = eigh(KB)
    wB = np.clip(wB, 0, None)
    KBh = (VB * np.sqrt(wB)) @ VB.T
    M = KBh @ inv(KA + reg * np.eye(n)) @ KBh
    return float(np.sqrt(np.clip(eigh(M)[0], 0, None).max()))


# ---------------------------------------------------------------------------
# CHIMERA feature map parametrized by qubit count n
# ---------------------------------------------------------------------------
def feat_dim(n):
    """Single-scale reservoir feature dimension: n singles + n(n-1)/2 pairs."""
    return n + n * (n - 1) // 2


def chimera_features_n(Qn, n, taus, seed, noise=None, noise_rate=0.0):
    """Single-/multi-scale CHIMERA features at n qubits on encoded inputs Qn.

    Qn rows are the scaled lag values to angle-encode (one per qubit, up to n).
    Reuses the validated MultiScaleCHIMERA / DelayEmbeddingQRC engine.
    """
    ch = MultiScaleCHIMERA(n_qubits=n, taus=taus, hamiltonian='ising',
                           hx=1.0, connectivity=0.5, seed=seed,
                           noise=noise, noise_rate=noise_rate)
    ch._reset_feedback()
    return np.array([ch._all_features(w) for w in Qn])


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_calm_kernel_data():
    """Full series, 70/30 chronological split, scaled lags - for kernel geometry."""
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    Xlag, y = data["X_lags"], data["y_logrv"]
    tr, te = vd.make_splits(len(y), train_frac=0.70)
    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0)
    rng = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rng, 0.0, 1.0)
    return Q, y, tr


def load_crisis_data():
    """Crisis-inclusive split (GFC 2008 in test) - for forecasting metrics."""
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    Xlag, Xhar = data["X_lags"], data["X_har"]
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    dts = pd.to_datetime(data["dates"])
    tr = np.where(dts < CRISIS_TRAIN_END)[0]
    te = np.where((dts >= CRISIS_TRAIN_END) & (dts < CRISIS_TEST_END))[0]
    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0)
    rng = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rng, 0.0, 1.0)
    LIN = np.hstack([Xlag, Xhar])   # full linear info for both models (paper discipline)
    return Q, LIN, Xhar, y_logrv, y_rv, tr, te, dts


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------
def run_kernel_sweep(ns, seed=0, subsample=KERNEL_SUBSAMPLE):
    Q, y, tr = load_calm_kernel_data()
    idx = np.linspace(0, len(tr) - 1, min(subsample, len(tr))).astype(int)
    trk = np.array(tr)[idx]
    yc = y[trk] - y[trk].mean()
    n_lags = Q.shape[1]

    rows = []
    print("\n" + "=" * 78)
    print("KERNEL GEOMETRY SWEEP  (calm 70%% train, N_sub=%d, seed=%d)" % (len(trk), seed))
    print("=" * 78)
    print(f"{'n':>3}{'#feat':>7}{'#lags_enc':>10}{'g(ESN||CHIM)':>14}"
          f"{'g_control':>11}{'D_eff':>8}{'rank':>6}{'KTA':>9}{'sec':>7}")
    for n in ns:
        if n > MAX_DENSE_N:
            print(f"{n:>3}  -- skipped (dense statevector frontier is n={MAX_DENSE_N}; "
                  f"n>={MAX_DENSE_N+1} needs sparse/Trotter evolution - logged follow-up)")
            continue
        t0 = time.time()
        n_enc = min(n, n_lags)
        Qn = Q[:, :n_enc]
        FQ = chimera_features_n(Qn[trk], n, (2.0,), seed)
        nr = feat_dim(n)
        Fe = esn_features(Qn[trk], nr, seed)
        Feb = esn_features(Qn[trk], nr, seed + 1)
        KQ, Ke, Keb = lin_kernel(FQ), lin_kernel(Fe), lin_kernel(Feb)
        g_q = geom_diff(Ke, KQ)
        g_c = geom_diff(Ke, Keb)
        de = eff_dim(KQ); rk = num_rank(KQ); kt = kta(KQ, yc)
        dt = time.time() - t0
        rows.append(dict(n=n, n_feat=FQ.shape[1], n_enc=n_enc, g_quantum=g_q,
                         g_control=g_c, d_eff=de, rank=rk, kta=kt, sec=dt))
        print(f"{n:>3}{FQ.shape[1]:>7}{n_enc:>10}{g_q:>14.2f}{g_c:>11.2f}"
              f"{de:>8.2f}{rk:>6}{kt:>9.4f}{dt:>7.1f}")
    return rows


def run_forecast_sweep(ns, taus=(2.0,), seeds=SEEDS):
    Q, LIN, Xhar, y_logrv, y_rv, tr, te, dts = load_crisis_data()
    n_lags = Q.shape[1]
    yT_log, yT_rv = y_logrv[te], y_rv[te]

    # HAR baseline (computed once)
    har_pred, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te])
    mz_har = mz_r2(yT_rv, np.exp(har_pred))
    rmse_har = rmse(yT_log, har_pred)
    qlike_har = qlike(yT_rv, np.exp(har_pred))
    har_loss = (har_pred - yT_log) ** 2

    rows = []
    print("\n" + "=" * 78)
    print("FORECAST SWEEP  (crisis split: train ..2006, test 2007-2012, GFC in test)")
    print(f"HAR baseline:  RMSE(logRV)={rmse_har:.4f}  QLIKE={qlike_har:.4f}  MZ_R2={mz_har:.3f}")
    print("=" * 78)
    print(f"{'n':>3}{'#feat':>7}{'#lags_enc':>10}{'RMSE':>9}{'dRMSE':>9}"
          f"{'QLIKE':>9}{'MZ_R2':>8}{'MZ-gap':>8}{'DM_p':>7}{'sec':>7}")
    for n in ns:
        if n > MAX_DENSE_N:
            print(f"{n:>3}  -- skipped (dense frontier n={MAX_DENSE_N}; sparse/Trotter follow-up)")
            continue
        t0 = time.time()
        n_enc = min(n, n_lags)
        Qn = Q[:, :n_enc]
        seed_preds = []
        for sd in seeds:
            F = chimera_features_n(Qn, n, taus, sd)
            D = np.hstack([F, LIN])
            pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
            seed_preds.append(pr)
        ens = np.mean(seed_preds, axis=0)
        var = np.exp(ens)
        r = rmse(yT_log, ens); q = qlike(yT_rv, var); mz = mz_r2(yT_rv, var)
        ch_loss = (ens - yT_log) ** 2
        dm_s, dm_p = dm_test(ch_loss, har_loss)   # <0 & sig => CHIMERA beats HAR
        dt = time.time() - t0
        rows.append(dict(n=n, n_feat=F.shape[1], n_enc=n_enc, rmse=r,
                         rmse_gap=r - rmse_har, qlike=q, mz=mz, mz_gap=mz - mz_har,
                         dm_s=dm_s, dm_p=dm_p, sec=dt))
        print(f"{n:>3}{F.shape[1]:>7}{n_enc:>10}{r:>9.4f}{r-rmse_har:>+9.4f}"
              f"{q:>9.4f}{mz:>8.3f}{mz-mz_har:>+8.3f}{dm_p:>7.3f}{dt:>7.1f}")
    return rows, dict(mz_har=mz_har, rmse_har=rmse_har, qlike_har=qlike_har)


def run_noise_sweep(ns, settings, seeds=(0, 1), taus=(2.0,)):
    """RMSE/QLIKE/MZ under noise channels on the crisis split (exact density matrix)."""
    Q, LIN, Xhar, y_logrv, y_rv, tr, te, dts = load_crisis_data()
    n_lags = Q.shape[1]
    yT_log, yT_rv = y_logrv[te], y_rv[te]
    har_pred, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te])
    mz_har = mz_r2(yT_rv, np.exp(har_pred))

    rows = []
    print("\n" + "=" * 78)
    print("NOISE SWEEP  (crisis split; exact density-matrix channels)")
    print(f"(HAR MZ_R2={mz_har:.3f}; noise n capped at {MAX_NOISE_N} - exact rho is 4^n)")
    print("=" * 78)
    print(f"{'n':>3}  {'channel':>18}{'rate':>7}{'RMSE':>9}{'QLIKE':>9}{'MZ_R2':>8}{'MZ-gap':>8}{'sec':>7}")
    for n in ns:
        if n > MAX_NOISE_N:
            print(f"{n:>3}  -- skipped (exact-noise frontier n={MAX_NOISE_N})")
            continue
        n_enc = min(n, n_lags)
        Qn = Q[:, :n_enc]
        for (noise, rate) in settings:
            t0 = time.time()
            seed_preds = []
            for sd in seeds:
                F = chimera_features_n(Qn, n, taus, sd, noise=noise, noise_rate=rate)
                D = np.hstack([F, LIN])
                pr, _ = ridge_readout(D[tr], y_logrv[tr], D[te])
                seed_preds.append(pr)
            ens = np.mean(seed_preds, axis=0)
            var = np.exp(ens)
            r = rmse(yT_log, ens); q = qlike(yT_rv, var); mz = mz_r2(yT_rv, var)
            dt = time.time() - t0
            label = noise if noise else "noiseless"
            rows.append(dict(n=n, channel=label, rate=rate, rmse=r, qlike=q,
                             mz=mz, mz_gap=mz - mz_har, sec=dt))
            print(f"{n:>3}  {label:>18}{rate:>7.3f}{r:>9.4f}{q:>9.4f}{mz:>8.3f}"
                  f"{mz - mz_har:>+8.3f}{dt:>7.1f}")
    return rows


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def make_figure(kernel_rows, fc_rows, path="figures/fig_scaling_sweep.png"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(figure skipped: matplotlib unavailable - {e})")
        return
    if not kernel_rows and not fc_rows:
        return
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))

    if kernel_rows:
        ns = [r["n"] for r in kernel_rows]
        ax[0].plot(ns, [r["g_quantum"] for r in kernel_rows], "o-", label="g(ESN||CHIMERA)")
        ax[0].plot(ns, [r["g_control"] for r in kernel_rows], "s--", color="gray",
                   label="g control (ESN||ESN')")
        ax[0].set_title("H0: kernel distinctness g(n)")
        ax[0].set_xlabel("qubits n"); ax[0].set_ylabel("geometric difference g")
        ax[0].legend(fontsize=8)

        ax[2].plot(ns, [r["d_eff"] for r in kernel_rows], "o-", color="C2")
        ax[2].set_title("H4: effective dim D_eff(n)")
        ax[2].set_xlabel("qubits n"); ax[2].set_ylabel("D_eff (quantum kernel)")

    if fc_rows:
        ns = [r["n"] for r in fc_rows]
        ax[1].axhline(0, color="k", lw=0.8)
        ax[1].plot(ns, [r["mz_gap"] for r in fc_rows], "o-", color="C3")
        ax[1].set_title("H0: MZ R^2 gap over HAR (crisis)")
        ax[1].set_xlabel("qubits n"); ax[1].set_ylabel("MZ_R2(CHIMERA) - MZ_R2(HAR)")

    fig.suptitle("CHIMERA-QRC scaling sweep (fixed 8-lag encoder - input bottleneck for n>8)",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"\nsaved figure -> {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-noise", action="store_true")
    args = ap.parse_args()

    if args.quick:
        ns = args.ns or [8, 10, 12]   # >=3 fixed-input points so the H0/H4 verdict matches the full run
        seeds = (0,)
        do_noise = False
        kern_sub = 300
    else:
        ns = args.ns or [5, 6, 7, 8, 10, 12]
        seeds = SEEDS
        do_noise = not args.no_noise
        kern_sub = KERNEL_SUBSAMPLE

    t_all = time.time()
    print("#" * 78)
    print("CHIMERA-QRC PHASE-3 SCALING SWEEP")
    print(f"qubit counts: {ns}   seeds: {seeds}   dense frontier: n<={MAX_DENSE_N}")
    print("Pre-registered thresholds loaded from preregistration.py (committed first).")
    print("#" * 78)

    kernel_rows = run_kernel_sweep(ns, seed=0, subsample=kern_sub)
    fc_rows, har = run_forecast_sweep(ns, seeds=seeds)

    noise_rows = []
    if do_noise:
        noise_ns = [n for n in ns if n <= MAX_NOISE_N][:3] or [5]
        settings = [(None, 0.0), ("depolarizing", 0.02), ("amplitude_damping", 0.02)]
        noise_rows = run_noise_sweep(noise_ns, settings, seeds=seeds[:2])

    # ---- adjudicate against pre-registration ----
    # align kernel & forecast rows on the common n set actually computed
    kn = {r["n"]: r for r in kernel_rows}
    fn = {r["n"]: r for r in fc_rows}
    common = sorted(set(kn) & set(fn))
    n_lags = len(LAGS)
    # The CLEAN pure-qubit-scaling test holds the encoded input fixed. With a
    # univariate lag encoder that means n >= n_lags (all lags encoded; extra
    # qubits idle). Points with n < n_lags vary INPUT RICHNESS too, so they are
    # reported but excluded from the pure-scaling H0/H4 verdict.
    fixed_input = [n for n in common if n >= n_lags]
    print("\n" + "=" * 78)
    print("PRE-REGISTERED ADJUDICATION")
    print("=" * 78)
    print(f"All computed n: {common}")
    print(f"Fixed-input (pure qubit-scaling) regime used for H0/H4 verdict: {fixed_input}")
    print(f"  (n < {n_lags} also varies #encoded lags -> reported but not used for the "
          f"pure-scaling claim)")
    ns_c = fixed_input if len(fixed_input) >= 2 else common
    if len(ns_c) >= 2:
        g_q = [kn[n]["g_quantum"] for n in ns_c]
        mzg = [fn[n]["mz_gap"] for n in ns_c]
        dmp = [fn[n]["dm_p"] for n in ns_c]
        deff = [kn[n]["d_eff"] for n in ns_c]
        rgap = [fn[n]["rmse_gap"] for n in ns_c]
        control_g = float(np.median([kn[n]["g_control"] for n in ns_c]))

        v0 = prereg.evaluate_H0(ns_c, g_q, mzg, dmp, control_g)
        v1 = prereg.evaluate_H1(ns_c, rgap)
        v4 = prereg.evaluate_H4(ns_c, deff)
        for v in (v0, v1, v4):
            print(f"\n[{v['hypothesis']}] verdict = {v['verdict']}")
            for k, val in v.items():
                if k in ("hypothesis", "verdict"):
                    continue
                print(f"    {k}: {val}")
    else:
        print("(need >=2 common n values for adjudication; widen --ns)")

    if not args.quick:           # --quick must not clobber committed full-run artifacts
        make_figure(kernel_rows, fc_rows)
        out = dict(ns=ns, kernel=kernel_rows, forecast=fc_rows, noise=noise_rows,
                   har=har, prereg=dict(DM_ALPHA=prereg.DM_ALPHA))
        np.save("scaling_sweep_results.npy", out, allow_pickle=True)
        print(f"\nsaved scaling_sweep_results.npy")
    else:
        print("\n[--quick] skipped writing figure/results (committed full-run artifacts preserved)")
    print(f"[total wall-clock {time.time() - t_all:.1f}s]")


if __name__ == "__main__":
    main()
