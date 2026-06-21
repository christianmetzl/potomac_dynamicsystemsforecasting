"""
entanglement_distinctness.py - is the CHIMERA reservoir's kernel distinctness CAUSED by its
entanglement?  (Phase-3 Axis-A, spec-independent.)
====================================================================================
The MPS study showed the Phase-2 reservoir is near-maximally (volume-law) entangled, which is
why no classical method reaches the ~30-qubit frontier cheaply. This script asks the causal
question directly: if we DIAL DOWN the entanglement, does the kernel distinctness g (the
geometric difference of the quantum kernel from the matched ESN kernel - the H0 "curve 1"
signal) survive, or collapse?

Single clean knob: a global coupling-strength scale alpha on the Ising J. At fixed n, tau:
    alpha = 0  -> J=0 -> H = hx*sum X_i -> evolution is a PRODUCT of single-qubit rotations
                 -> ZERO entanglement (separable reservoir).
    alpha = 1  -> the exact Phase-2 reservoir (near-maximal entanglement).
    alpha > 1  -> even more entanglement.
Everything else (encoding, readout, the matched ESN, the inputs) is held fixed, so g and the
entanglement entropy S move ONLY through alpha.

Two decisive outcomes:
  * g tracks S (rises with entanglement, ~classical at alpha->0): the quantum signal IS the
    entanglement -> a clean "entanglement is the resource" claim, and confirms low-chi MPS
    cannot reproduce the high-g reservoir.
  * g survives at low S: the distinctness is NOT entanglement-bound -> a low-entanglement
    reservoir variant could be MPS-simulated to the real scale frontier (unblocks Axis-A
    classically).

Emits entanglement_distinctness.json + figures/fig_entanglement_distinctness_n{n}.png.

Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
from __future__ import annotations
import argparse, json
import numpy as np

import multivariate_data as mvd
import volatility_data as vd
from vol_fair_benchmark import esn_features
from qrc_engine import (build_ising_hamiltonian, generate_coupling_matrix,
                        apply_single_qubit_gate, Ry, measure_full_features)
from scaling_sweep import lin_kernel, geom_diff, eff_dim, KERNEL_N


def _reservoir(Q, n, jseed, tau, alpha):
    """Phase-2 reservoir with coupling scaled by alpha. Returns (features, mean bipartite
    entanglement entropy S over the inputs in bits, at the central cut)."""
    J = alpha * generate_coupling_matrix(n, 0.5, seed=jseed)     # alpha=1 == Phase-2 coupling
    H = build_ising_hamiltonian(n, J, hx=1.0)
    w, V = np.linalg.eigh(H)
    U = (V * np.exp(-1j * w * tau)) @ V.conj().T
    fdim = n + n * (n - 1) // 2
    F = np.empty((len(Q), fdim))
    k = n // 2                                                    # central bipartition
    S = np.empty(len(Q))
    for i, emb in enumerate(Q):
        psi = np.zeros(2 ** n, dtype=complex); psi[0] = 1.0
        for q in range(min(len(emb), n)):
            psi = apply_single_qubit_gate(psi, Ry(np.pi * np.clip(emb[q], 0, 1)), q, n)
        psi = U @ psi
        F[i] = measure_full_features(psi, n)
        sv = np.linalg.svd(psi.reshape(2 ** k, 2 ** (n - k)), compute_uv=False)
        p = sv ** 2; p = p[p > 1e-14]
        S[i] = float(-(p * np.log2(p)).sum())                    # von Neumann entropy (bits)
    return F, float(S.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tau", type=float, default=2.0)            # g-anchor scale
    ap.add_argument("--seed", type=int, default=0)              # reservoir coupling seed
    ap.add_argument("--alphas", type=float, nargs="+",
                    default=[0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
    ap.add_argument("--out", default="entanglement_distinctness.json")
    args = ap.parse_args()
    n = args.n

    # same inputs / split as scaling_sweep.compute_g (multivariate headline split)
    data = mvd.build_panel_supervised(horizon=1)
    Xraw = data["X_panel"]
    lo, hi = Xraw.min(0), Xraw.max(0); rng = np.where(hi - lo == 0, 1, hi - lo)
    Q = np.clip((Xraw - lo) / rng, 0.0, 1.0)
    tr, _ = vd.make_splits(len(Xraw), train_frac=0.70)
    idx = np.linspace(0, len(tr) - 1, min(KERNEL_N, len(tr))).astype(int)
    Qn = Q[np.array(tr)[idx]][:, :n]

    # matched classical maps (alpha-independent): ESN kernel + classical-classical control
    F108, F108b = esn_features(Qn, 108, 0), esn_features(Qn, 108, 1)
    K108, K108b = lin_kernel(F108), lin_kernel(F108b)
    g_control = geom_diff(K108, K108b)
    S_max = n / 2.0                                              # maximal entanglement (bits)

    print("=" * 84)
    print(f"ENTANGLEMENT -> DISTINCTNESS  n={n}  tau={args.tau}  (alpha scales the Ising coupling)")
    print(f"  matched ESN-108 control g(classical->classical) = {g_control:.2f} ;  S_max = {S_max} bits")
    print("=" * 84)
    print(f"  {'alpha':>6} {'S(bits)':>9} {'S/Smax':>7} {'g':>9} {'g/control':>10} {'D_eff(Q)':>9}")

    rows = []
    for a in args.alphas:
        FQ, S = _reservoir(Qn, n, args.seed, args.tau, a)
        KQ = lin_kernel(FQ)
        g = geom_diff(K108, KQ)
        rec = {"alpha": a, "S_bits": S, "S_frac": S / S_max, "g": g,
               "g_over_control": g / g_control, "deff": eff_dim(KQ)}
        rows.append(rec)
        print(f"  {a:6.2f} {S:9.3f} {S/S_max:7.2f} {g:9.2f} {g/g_control:10.2f} {rec['deff']:9.2f}")
        json.dump({"n": n, "tau": args.tau, "g_control": g_control, "S_max": S_max, "rows": rows},
                  open(args.out, "w"), indent=2)

    # correlation between g and S across the dial
    Sv = np.array([r["S_bits"] for r in rows]); gv = np.array([r["g"] for r in rows])
    corr = float(np.corrcoef(Sv, gv)[0, 1])
    a0 = rows[0]; a1 = next(r for r in rows if abs(r["alpha"] - 1.0) < 1e-9)
    print(f"\n  corr(g, S) across the dial = {corr:+.3f}")
    print(f"  product-state (alpha=0): S={a0['S_bits']:.2f} bits, g={a0['g']:.1f} "
          f"({a0['g_over_control']:.1f}x control)")
    print(f"  Phase-2 (alpha=1):       S={a1['S_bits']:.2f} bits, g={a1['g']:.1f} "
          f"({a1['g_over_control']:.1f}x control)")
    verdict = ("g TRACKS entanglement -> the quantum signal IS the entanglement"
               if corr > 0.8 and a0["g_over_control"] < 0.3 * a1["g_over_control"]
               else "g PARTLY survives at low entanglement -> not fully entanglement-bound"
               if a0["g_over_control"] > 0.5 * a1["g_over_control"]
               else "mixed: g rises with entanglement but retains a floor at alpha=0")
    print(f"  >>> {verdict}")
    json.dump({"n": n, "tau": args.tau, "g_control": g_control, "S_max": S_max,
               "corr_g_S": corr, "verdict": verdict, "rows": rows}, open(args.out, "w"), indent=2)
    print(f"saved {args.out}")
    try:
        _plot(rows, g_control, S_max, corr, n)
    except Exception as e:
        print(f"(plot skipped: {e})")


def _plot(rows, g_control, S_max, corr, n):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a = [r["alpha"] for r in rows]; S = [r["S_bits"] for r in rows]; g = [r["g"] for r in rows]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))

    ax0 = ax[0]; ax0b = ax0.twinx()
    l1 = ax0.plot(a, g, "o-", color="C0", lw=2, label="distinctness g")[0]
    l2 = ax0.axhline(g_control, ls="--", color="gray", alpha=.7, label="classical control")
    l3 = ax0b.plot(a, S, "s-", color="C3", lw=2, label="entanglement S")[0]
    ax0b.axhline(S_max, ls=":", color="C3", alpha=.5)
    ax0.axvline(1.0, color="k", alpha=.3, lw=1); ax0.text(1.02, ax0.get_ylim()[1]*0.9, "Phase-2", fontsize=8)
    ax0.set_xlabel(r"coupling scale $\alpha$  (0 = product state)"); ax0.set_ylabel("geometric difference g", color="C0")
    ax0b.set_ylabel("entanglement entropy S (bits)", color="C3")
    ax0.set_title(f"Dialing entanglement (n={n})\ndoes g rise with S?")
    ax0.legend(handles=[l1, l2, l3], fontsize=8, loc="center right")

    sc = ax[1].scatter(S, g, c=a, cmap="viridis", s=60, zorder=3)
    ax[1].axhline(g_control, ls="--", color="gray", alpha=.7, label="classical control")
    ax[1].set_xlabel("entanglement entropy S (bits)"); ax[1].set_ylabel("geometric difference g")
    ax[1].set_title(f"g vs entanglement  (corr = {corr:+.2f})")
    plt.colorbar(sc, ax=ax[1], label=r"$\alpha$"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

    fig.suptitle("CHIMERA-QRC Phase-3: is the kernel distinctness g caused by reservoir entanglement?",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    import os; os.makedirs("figures", exist_ok=True)
    out = f"figures/fig_entanglement_distinctness_n{n}.png"   # n-specific: never clobber another n
    fig.savefig(out, dpi=130)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
