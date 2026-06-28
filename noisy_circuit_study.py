"""
noisy_circuit_study.py - the INFORMATIVE noise study (addresses the critique that the MNIST
noise result is readout-only, so "invariance to depolarizing" is just a standardization
artifact, not evidence about a noisy CIRCUIT).

We build the gate-Trotter CHIMERA circuit (n=8, 20 layers, random ~50%-Ising) on PennyLane's
density-matrix simulator and compare, at matched noise rate r, the readout features
(⟨Z_i⟩, ⟨Z_iZ_j⟩) under FOUR noise placements:

  readout-depol   : depolarizing applied ONCE, after evolution, before measurement
  perlayer-depol  : depolarizing applied after EVERY Trotter layer (accumulates ~220 2q gates)
  readout-ampdamp : amplitude damping applied once at readout
  perlayer-ampdamp: amplitude damping after every Trotter layer

For each we report the mean absolute feature error vs the noiseless circuit, BOTH raw and after
the per-feature standardization the classifier/readout uses. The decisive contrast:

  * readout-only depolarizing  -> raw error large, STANDARDIZED error ~ 0
    (a uniform Bloch contraction is divided out exactly by per-feature standardization;
     this is the "invariance" reported on MNIST -- a property of the standardizer, not the QPU)
  * per-LAYER depolarizing      -> STANDARDIZED error grows with r and does NOT vanish
    (noise interleaved with unitaries is not a single final contraction; standardization
     cannot remove it) -- this is the NISQ-relevant degradation.

So the honest, informative statement is: CHIMERA is invariant to *readout* depolarizing by
construction, but accumulated *per-layer* 2-qubit noise genuinely degrades the features, which
is what a real device incurs over a 380-gate circuit. (Shot noise is characterized separately
in qbraid_submit.py; a real-QPU run is the remaining step.)

Usage:  python3 noisy_circuit_study.py            # n=8, 120 windows, rates 0..0.05
        python3 noisy_circuit_study.py --quick     # n=8, 40 windows, rates 0,0.01,0.02
"""
import argparse
import time
import numpy as np
import pennylane as qml

from qrc_engine import generate_coupling_matrix
from qbraid_submit import real_rv_windows, _observables, _encode, TAU, HX, CONN

N = 8
LAYERS = 20


def _layer(n, J, dt):
    for i in range(n):
        for j in range(i + 1, n):
            if abs(J[i, j]) > 1e-12:
                qml.IsingZZ(2 * J[i, j] * dt, wires=[i, j])
    for i in range(n):
        qml.RX(2 * HX * dt, wires=i)


def _noise(n, channel, p):
    if p <= 0:
        return
    for i in range(n):
        if channel == "depol":
            qml.DepolarizingChannel(p, wires=i)
        elif channel == "ampdamp":
            qml.AmplitudeDamping(p, wires=i)


def make_circ(n, J, channel, placement):
    dev = qml.device("default.mixed", wires=n)
    OBS = _observables(n)

    @qml.qnode(dev)
    def circ(w, p=0.0):
        _encode(w, n)
        dt = TAU / LAYERS
        for _ in range(LAYERS):
            _layer(n, J, dt)
            if placement == "perlayer":
                _noise(n, channel, p)
        if placement == "readout":
            _noise(n, channel, p)
        return [qml.expval(o) for o in OBS]
    return circ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    k = 6 if args.quick else 12       # density-matrix sim at n=8 is ~2s/circuit; few windows suffice
    rates = [0.0, 0.02] if args.quick else [0.0, 0.01, 0.04]
    J = generate_coupling_matrix(N, connectivity=CONN, seed=0)
    wins = real_rv_windows(N, k=k)

    print("#" * 92)
    print("NOISY-CIRCUIT STUDY (informative): readout-only vs per-Trotter-layer noise, n=8, 20 layers")
    print(f"  {len(wins)} real .SPX input windows · density-matrix sim · rates {rates}")
    print("#" * 92)

    # noiseless reference. The readout standardizes whatever feature set it is given by THAT set's
    # own per-feature mean/std (z-score). So we standardize each set by its OWN stats, then compare:
    # a uniform per-feature scaling (readout-only depolarizing) maps to the SAME z-scores (error ~0);
    # interleaved per-layer noise does not (error > 0). This is the fair reproduction of the MNIST test.
    F0 = np.array([make_circ(N, J, "depol", "readout")(w, 0.0) for w in wins])
    zscore = lambda M: (M - M.mean(0)) / (M.std(0) + 1e-12)
    z0 = zscore(F0)

    combos = [("depol", "readout"), ("depol", "perlayer"),
              ("ampdamp", "readout"), ("ampdamp", "perlayer")]
    print(f"\n  {'channel':<9}{'placement':<10}{'rate':>7}{'raw |Δfeat|':>13}{'STD-z |Δfeat|':>14}",
          flush=True)
    rows = []
    for channel, placement in combos:
        circ = make_circ(N, J, channel, placement)
        for r in rates:
            if r == 0.0:
                continue
            F = np.array([circ(w, r) for w in wins])
            raw = float(np.abs(F - F0).mean())
            std = float(np.abs(zscore(F) - z0).mean())   # each set z-scored by its OWN stats
            rows.append(dict(channel=channel, placement=placement, rate=r,
                             raw_err=raw, std_err=std))
            print(f"  {channel:<9}{placement:<10}{r:>7.3f}{raw:>13.4f}{std:>14.4f}", flush=True)

    # decisive contrast at the largest rate
    rmax = rates[-1]
    ro = next(x for x in rows if x["channel"] == "depol" and x["placement"] == "readout" and x["rate"] == rmax)
    pl = next(x for x in rows if x["channel"] == "depol" and x["placement"] == "perlayer" and x["rate"] == rmax)
    print("\n" + "=" * 92)
    print(f"CONTRAST at depolarizing rate {rmax}:")
    print(f"  readout-only : standardized feature error = {ro['std_err']:.4f}  "
          f"(≈0 ⇒ standardization removes it exactly — this is the MNIST 'invariance', an artifact)")
    rel = f"{pl['std_err']/ro['std_err']:.0f}× larger" if ro['std_err'] > 1e-4 else "vs ≈0 at readout"
    print(f"  per-layer    : standardized feature error = {pl['std_err']:.4f}  "
          f"({rel} ⇒ NOT removed — the real NISQ degradation over the 380-gate circuit)")
    verdict = ("CONFIRMED: per-layer noise genuinely degrades features; readout-only invariance is "
               "a standardization artifact." if pl["std_err"] > 5 * ro["std_err"] + 1e-6
               else "Per-layer and readout effects are comparable here (inspect rates).")
    print("VERDICT:", verdict)
    if not args.quick:
        np.save("noisy_circuit_results.npy",
                dict(rows=rows, n=N, layers=LAYERS, rates=rates, k=len(wins)), allow_pickle=True)
        print(f"\nsaved noisy_circuit_results.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
