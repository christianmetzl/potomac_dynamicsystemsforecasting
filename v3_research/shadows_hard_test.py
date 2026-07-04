"""
shadows_hard_test.py  [V3 — the PROPER quantum-data test: QRC vs CLASSICAL SHADOWS, matched budget]

Our crossover study was honest that its budget-matched classical baseline was a random-Pauli
subset, NOT the SOTA — classical shadows (Huang-Kueng-Preskill 2020). This experiment runs the
real thing: RANDOM-PAULI CLASSICAL SHADOWS vs the quantum-native QRC estimator, at a MATCHED
per-state measurement budget (N single-copy measurements per state for shadows; N shots through
the reservoir for the QRC), on two functionals of random k-qubit mixed states:

  Tr(rho^2)  - degree-2, the shadows sweet spot (pair U-statistic). Expected: shadows win.
  Tr(rho^3)  - degree-3, shadows-HARD: needs a TRIPLE U-statistic whose variance explodes at
               small N. The one place a learned quantum-native estimator could honestly win.

Honest framing (stated up front): the QRC estimator is LEARNED — it needs a training set of
states with known labels (cost amortized over uses); shadows are training-free. The question
tested is narrow and fair: at matched per-state budget, which delivers lower estimation error on
NEW states?

Usage:  python3 shadows_hard_test.py            # k=3, budgets 60/240/960, ~8 min
        python3 shadows_hard_test.py --quick
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from qrc_quantum_data_crossover import rand_state, QStateReservoir
from axisB_rigorous import rff_features, rbf_gamma
from vol_fair_benchmark import ridge_readout

HERE = os.path.dirname(os.path.abspath(__file__))

H = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
SDG = np.diag([1, -1j])
ROT = {0: H, 1: H @ SDG, 2: np.eye(2)}          # X-, Y-, Z-basis rotations
E0 = np.array([[1, 0], [0, 0]]); E1 = np.array([[0, 0], [0, 1]])


def shadows_snapshots(rho, k, N, rng):
    """N random-Pauli single-copy snapshots; returns per-qubit 2x2 inverse factors."""
    snaps = np.empty((N, k, 2, 2), complex)
    for s in range(N):
        bases = rng.randint(0, 3, size=k)
        U = np.array([[1.0]])
        for q in range(k):
            U = np.kron(U, ROT[bases[q]])
        p = np.clip(np.real(np.diag(U @ rho @ U.conj().T)), 0, None)
        p = p / p.sum()
        out = rng.choice(2 ** k, p=p)
        for q in range(k):
            o = (out >> (k - 1 - q)) & 1
            Uq = ROT[bases[q]]
            proj = Uq.conj().T @ (E0 if o == 0 else E1) @ Uq
            snaps[s, q] = 3 * proj - np.eye(2)
        # (each factor is the single-qubit shadow inverse; tensor product over qubits)
    return snaps


def shadow_purity(snaps, n_pairs, rng):
    """U-statistic over distinct pairs: Tr(rho^2) ~ E[prod_q Tr(s_a,q s_b,q)]."""
    N = len(snaps)
    a = rng.randint(0, N, n_pairs); b = rng.randint(0, N, n_pairs)
    ok = a != b; a, b = a[ok], b[ok]
    prod = np.einsum('pqij,pqji->pq', snaps[a], snaps[b])   # per-qubit traces
    return float(np.real(np.mean(np.prod(prod, axis=1))))


def shadow_tr3(snaps, n_tri, rng):
    """U-statistic over distinct triples: Tr(rho^3) ~ E[prod_q Tr(s_a s_b s_c)]."""
    N = len(snaps)
    a = rng.randint(0, N, n_tri); b = rng.randint(0, N, n_tri); c = rng.randint(0, N, n_tri)
    ok = (a != b) & (b != c) & (a != c); a, b, c = a[ok], b[ok], c[ok]
    prod = np.einsum('pqij,pqjk,pqki->pq', snaps[a], snaps[b], snaps[c])
    return float(np.real(np.mean(np.prod(prod, axis=1))))


def qrc_features_shots(qr, rho, K, N, rng):
    """Reservoir features from SHOT-SAMPLED counts (N total copies, split across K blocks)."""
    per = max(N // K, 1)
    din, dmem, n = qr.din, qr.dmem, qr.n
    rho_full = np.kron(rho, np.eye(dmem) / dmem)
    feats = []
    for _ in range(K):
        rho_full = qr.U @ rho_full @ qr.Ud
        p = np.clip(np.real(np.diag(rho_full)), 0, None); p = p / p.sum()
        cnt = rng.multinomial(per, p)
        ph = cnt / per
        zi = ph @ qr.Z
        zz = [float(ph @ (qr.Z[:, i] * qr.Z[:, j])) for (i, j) in qr.pairs]
        feats.extend(list(zi) + zz)
        R = rho_full.reshape(din, dmem, din, dmem)
        rho_full = np.kron(rho, np.einsum('ikil->kl', R))
    return np.array(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    k, m, K = 3, 3, 3
    n_train, n_test = (120, 40) if args.quick else (300, 100)
    budgets = [240] if args.quick else [60, 240, 960]
    seeds = (0,) if args.quick else (0, 1)
    t0 = time.time()

    rng = np.random.RandomState(7)
    states = [rand_state(k, rng) for _ in range(n_train + n_test)]
    y2 = np.array([float(np.real(np.trace(r @ r))) for r in states])
    y3 = np.array([float(np.real(np.trace(r @ r @ r))) for r in states])
    tr = np.arange(n_train); te = np.arange(n_train, n_train + n_test)

    print("#" * 88)
    print("V3 SHADOWS-HARD TEST — QRC(learned) vs CLASSICAL SHADOWS at matched per-state budget")
    print(f"  k={k} qubit states; reservoir n={k+m} (K={K} injections); train={n_train} "
          f"test={n_test}; budgets={budgets} copies/state; seeds={seeds}")
    print("  (honest: QRC amortizes a labeled training set; shadows are training-free)")
    print("#" * 88)

    # trivial ensemble-prior baseline (predict the training mean) — any claimed "win"
    # must beat THIS meaningfully, else it is a prior artifact, not information
    triv2 = float(np.sqrt(np.mean((y2[tr].mean() - y2[te]) ** 2)))
    triv3 = float(np.sqrt(np.mean((y3[tr].mean() - y3[te]) ** 2)))
    print(f"\n  trivial (train-mean) baseline:  Tr(rho^2) RMSE={triv2:.4f}   "
          f"Tr(rho^3) RMSE={triv3:.4f}")

    results = []
    for N in budgets:
        # --- classical shadows on TEST states ---
        sh2, sh3 = [], []
        srng = np.random.RandomState(100 + N)
        for i in te:
            snaps = shadows_snapshots(states[i], k, N, srng)
            sh2.append(shadow_purity(snaps, 20000, srng))
            sh3.append(shadow_tr3(snaps, 30000, srng))
        rmse_sh2 = float(np.sqrt(np.mean((np.array(sh2) - y2[te]) ** 2)))
        rmse_sh3 = float(np.sqrt(np.mean((np.array(sh3) - y3[te]) ** 2)))

        # --- QRC learned estimator, same budget (seed-averaged) ---
        q2s, q3s = [], []
        for sd in seeds:
            qr = QStateReservoir(k, m, sd)
            frng = np.random.RandomState(200 + N + sd)
            F = np.array([qrc_features_shots(qr, r, K, N, frng) for r in states])
            Fs = (F - F.min(0)) / (np.ptp(F, 0) + 1e-9)
            g = rbf_gamma(Fs[tr])
            FR = rff_features(Fs, 60, sd, g)
            p2, _ = ridge_readout(FR[tr], y2[tr], FR[te])
            p3, _ = ridge_readout(FR[tr], y3[tr], FR[te])
            q2s.append(p2); q3s.append(p3)
        rmse_q2 = float(np.sqrt(np.mean((np.mean(q2s, 0) - y2[te]) ** 2)))
        rmse_q3 = float(np.sqrt(np.mean((np.mean(q3s, 0) - y3[te]) ** 2)))

        results.append(dict(N=N, shadows_tr2=rmse_sh2, qrc_tr2=rmse_q2,
                            shadows_tr3=rmse_sh3, qrc_tr3=rmse_q3))
        print(f"\n  budget N={N:>4}:  Tr(rho^2) RMSE  shadows={rmse_sh2:.4f}  QRC={rmse_q2:.4f}"
              f"   {'QRC wins' if rmse_q2 < rmse_sh2 else 'shadows win'}")
        print(f"                 Tr(rho^3) RMSE  shadows={rmse_sh3:.4f}  QRC={rmse_q3:.4f}"
              f"   {'QRC WINS' if rmse_q3 < rmse_sh3 else 'shadows win'}", flush=True)

    print("\n" + "=" * 88)
    # a genuine win must beat BOTH shadows AND the trivial prior by a clear margin
    def real_win(q, s, triv):
        return q < s and q < 0.9 * triv
    w3 = [r for r in results if real_win(r["qrc_tr3"], r["shadows_tr3"], triv3)]
    w2 = [r for r in results if real_win(r["qrc_tr2"], r["shadows_tr2"], triv2)]
    prior_only = [r for r in results
                  if r["qrc_tr3"] < r["shadows_tr3"] and not real_win(r["qrc_tr3"], r["shadows_tr3"], triv3)]
    if w3 or w2:
        print(f"VERDICT: the learned quantum-native estimator GENUINELY beats classical shadows "
              f"(and the ensemble prior) at budgets tr2={[r['N'] for r in w2]} "
              f"tr3={[r['N'] for r in w3]} — verify carefully before claiming.")
    else:
        print("VERDICT: NO genuine QRC edge over classical shadows. Wherever the QRC nominally "
              "beats shadows (tiny budgets), its accuracy equals the trivial ensemble-prior — a "
              "variance statement about shadows at small N, not extracted quantum information. "
              "Wherever real information is extracted, shadows win. The proper SOTA baseline "
              "confirms the honest negative on quantum data at simulable scale.")
        if prior_only:
            print(f"  (prior-artifact 'wins' correctly discarded at budgets "
                  f"{[r['N'] for r in prior_only]})")
    if not args.quick:
        np.save(os.path.join(HERE, "shadows_hard_results.npy"),
                dict(results=results, k=k, m=m, K=K, n_train=n_train, n_test=n_test,
                     trivial_tr2=triv2, trivial_tr3=triv3),
                allow_pickle=True)
        print(f"saved shadows_hard_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
