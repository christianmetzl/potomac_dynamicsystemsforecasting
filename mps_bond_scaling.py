"""
mps_bond_scaling.py - how far can the MPS backend push CHIMERA-QRC, and at what cost?
====================================================================================
Phase-3 Axis-A (scale) diagnostic. The dense engine walls at n=12 (2^n memory). The MPS
backend (mps_engine.py, validated to ~1e-3 vs dense with 2nd-order Trotter) represents the
reservoir state with a bounded bond dimension chi. Whether that *helps* depends entirely on
how much entanglement the reservoir builds - and the Phase-2 Hamiltonian is a transverse-
field Ising model with a RANDOM (long-range) coupling graph, the hard case for MPS.

This script measures, on a representative crisis input row of the multivariate panel:
  (1) FIDELITY  - capped-chi MPS vs exact dense features at n in {8,10,12} (validates that a
                  modest chi reproduces the reservoir where we can still check).
  (2) ENTANGLEMENT - the bond dimension actually reached (with the discarded weight at a
                  generous chi), vs the 2^{n/2} maximal-entanglement line, as n grows.
  (3) TRUNCATION COST - max discarded weight vs chi at each n (does a fixed chi stay accurate
                  as n grows, or does the long-range coupling force chi up exponentially?).
  (4) WALL-TIME - per-input cost vs n (the practical reach of the pure-NumPy backend).

Emits mps_bond_scaling.json + figures/fig_mps_bond_scaling.png. The verdict this feeds: if
truncation error at a fixed chi blows up with n, the CHIMERA reservoir needs genuinely
exponential resources (an H0-relevant negative); if it stays controlled, MPS extends the
decisive sweep past the dense wall.

Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
from __future__ import annotations
import argparse, json, time
import numpy as np

import multivariate_data as mvd
from qrc_engine import (build_ising_hamiltonian, generate_coupling_matrix,
                        apply_single_qubit_gate, Ry, measure_full_features)
from mps_engine import reservoir_features_mps
from scipy.linalg import expm


def dense_features(emb, n, J, tau):
    H = build_ising_hamiltonian(n, J, hx=1.0)
    U = expm(-1j * H * tau)
    psi = np.zeros(2 ** n, dtype=complex); psi[0] = 1.0
    for q in range(min(len(emb), n)):
        psi = apply_single_qubit_gate(psi, Ry(np.pi * np.clip(emb[q], 0, 1)), q, n)
    return measure_full_features(U @ psi, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=[8, 10, 12, 14])
    ap.add_argument("--tau", type=float, default=2.0, help="evolution time (g-anchor scale)")
    ap.add_argument("--chis", type=int, nargs="+", default=[8, 16, 32, 64])
    ap.add_argument("--chi-ref", type=int, default=128, help="generous chi for true-bond probe")
    ap.add_argument("--dense-max", type=int, default=12, help="largest n to cross-check vs dense")
    ap.add_argument("--out", default="mps_bond_scaling.json")
    args = ap.parse_args()

    # representative crisis input (max total realized vol -> richest entanglement)
    data = mvd.build_panel_supervised(horizon=1)
    Xraw = data["X_panel"]
    lo, hi = Xraw.min(0), Xraw.max(0); rng = np.where(hi - lo == 0, 1, hi - lo)
    Q = np.clip((Xraw - lo) / rng, 0.0, 1.0)
    crisis_row = Q[int(np.argmax(Xraw[:, 0]))]            # peak rv5 day (GFC-like)

    print("=" * 88)
    print(f"MPS BOND-DIMENSION SCALING  tau={args.tau}  input=peak-RV crisis row "
          f"({data['n_features']}-feat panel)")
    print(f"  chi caps {args.chis} ; true-bond probe chi={args.chi_ref} ; dense check n<={args.dense_max}")
    print("=" * 88)

    rows = []
    for n in args.ns:
        emb = crisis_row[:n]
        J = generate_coupling_matrix(n, 0.5, seed=0)     # g(n)-anchor coupling (seed 0)
        rec = {"n": n, "max_bond_full": int(2 ** (n // 2))}

        fdense = dense_features(emb, n, J, args.tau) if n <= args.dense_max else None

        # true-bond probe at a generous chi
        t0 = time.time()
        f_ref, bond_ref, te_ref = reservoir_features_mps(emb, n, J, args.tau, chi=args.chi_ref)
        rec["t_ref_s"] = round(time.time() - t0, 2)
        rec["bond_reached"] = int(bond_ref)
        rec["trunc_at_chiref"] = float(te_ref)
        # saturated == hit the cap AND still discarding real weight => true bond exceeds chi_ref
        rec["bond_saturated"] = bool(bond_ref >= args.chi_ref and te_ref > 1e-10)
        if fdense is not None:
            rec["err_ref_vs_dense"] = float(np.max(np.abs(f_ref - fdense)))

        # truncation cost + fidelity at each chi cap
        rec["chi"], rec["trunc"], rec["err_vs_dense"], rec["t_s"] = [], [], [], []
        for chi in args.chis:
            t0 = time.time()
            f, bond, te = reservoir_features_mps(emb, n, J, args.tau, chi=chi)
            dt = time.time() - t0
            rec["chi"].append(chi); rec["trunc"].append(float(te)); rec["t_s"].append(round(dt, 2))
            rec["err_vs_dense"].append(float(np.max(np.abs(f - fdense))) if fdense is not None else None)

        msg = (f"[n={n:2d}] bond@chi{args.chi_ref}={bond_ref:3d}"
               f"{'(SAT)' if rec['bond_saturated'] else '     '} "
               f"trunc@chi{args.chi_ref}={te_ref:.1e}  2^(n/2)={2**(n//2):4d}  t_ref={rec['t_ref_s']:5.1f}s")
        if fdense is not None:
            msg += f"  | err(chi={args.chis[-1]} vs dense)={rec['err_vs_dense'][-1]:.1e}"
        print(msg)
        for chi, te, ev in zip(rec["chi"], rec["trunc"], rec["err_vs_dense"]):
            ev_s = f" err_vs_dense={ev:.1e}" if ev is not None else ""
            print(f"        chi={chi:3d}  trunc={te:.2e}{ev_s}")
        rows.append(rec)
        json.dump({"tau": args.tau, "rows": rows}, open(args.out, "w"), indent=2)   # incremental

    print(f"\nsaved {args.out}")
    try:
        _plot(rows, args.tau)
    except Exception as e:
        print(f"(plot skipped: {e})")


def _plot(rows, tau):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ns = [r["n"] for r in rows]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.3))

    ax[0].plot(ns, [r["bond_reached"] for r in rows], "o-", color="C0", lw=2, label="bond reached")
    ax[0].plot(ns, [2 ** (n // 2) for n in ns], "k--", alpha=.6, label=r"$2^{n/2}$ (max entanglement)")
    sat = [r["n"] for r in rows if r["bond_saturated"]]
    if sat:
        ax[0].scatter(sat, [next(r["bond_reached"] for r in rows if r["n"] == s) for s in sat],
                      color="C3", zorder=5, label="chi-cap saturated")
    ax[0].set_yscale("log"); ax[0].set_xlabel("qubit count n"); ax[0].set_ylabel("bond dimension")
    ax[0].set_title(f"Entanglement growth (tau={tau})\nrandom-graph Ising builds bond dim fast")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.3, which="both")

    for r in rows:
        ax[1].plot(r["chi"], r["trunc"], "o-", lw=1.5, label=f"n={r['n']}")
    ax[1].set_yscale("log"); ax[1].set_xlabel("bond-dim cap chi"); ax[1].set_ylabel("max discarded weight")
    ax[1].set_title("Truncation cost vs chi\n(does a fixed chi stay accurate as n grows?)")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3, which="both")

    ax[2].plot(ns, [r["t_ref_s"] for r in rows], "o-", color="C2", lw=2)
    ax[2].set_yscale("log"); ax[2].set_xlabel("qubit count n"); ax[2].set_ylabel(f"wall-time / input (s)")
    ax[2].set_title("Backend cost vs n\n(practical reach of pure-NumPy MPS)")
    ax[2].grid(alpha=.3, which="both")

    fig.suptitle("CHIMERA-QRC Phase-3: MPS backend reach for the random-graph Ising reservoir "
                 "(entanglement, truncation cost, wall-time)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    import os; os.makedirs("figures", exist_ok=True)
    fig.savefig("figures/fig_mps_bond_scaling.png", dpi=130)
    print("saved figures/fig_mps_bond_scaling.png")


if __name__ == "__main__":
    main()
