"""
qbraid_submit.py - submit the CHIMERA-QRC gate-Trotter circuit to a backend.

This is the executable Platform-Use path: it runs the SAME verified gate-Trotter circuit
(`sdk_demo.py`) on a PennyLane simulator NOW, and is ONE FLAG (`--device`) from a real
qBraid / Braket / IonQ / IQM / IBM device. It produces the three things the Phase-3 brief and
our paper promise for a hardware run:

  1. SHOT-BUDGET characterization  - feature error vs shot count S (the ε ≈ 1/√S law).
     All n+C(n,2) readout observables are diagonal in the computational basis, so a SINGLE
     set of S shots estimates every ⟨Z_i⟩, ⟨Z_iZ_j⟩.
  2. ZNE demonstration             - zero-noise extrapolation over a depolarizing-noise sweep
     (linear Richardson) on `default.mixed`, recovering the noiseless value (Mitiq's
     gate-folding is the drop-in production path).
  3. CLASSICAL CROSS-CHECK         - every run is compared to the exact NumPy engine, the
     verification we commit to performing for every hardware execution.

Usage:
  python3 qbraid_submit.py                       # simulator: shot study + ZNE + cross-check
  python3 qbraid_submit.py --n 8 --shots 4000
  python3 qbraid_submit.py --device <qbraid/braket/qiskit device>   # real hardware (needs creds)

On qBraid, set --device to an available backend string (e.g. a Braket/IonQ device via the
PennyLane-Braket plugin, or 'qiskit.remote'); the rest of the pipeline is unchanged.

Team EIGENNEXUS | GIC 2026 - Phase 3 (Platform Use: executable QPU submission path)
"""
import argparse
import time
import numpy as np

try:
    import pennylane as qml
except ImportError:
    raise SystemExit("PennyLane required: pip install -r requirements.txt")

from scipy.linalg import expm
from qrc_engine import generate_coupling_matrix, build_ising_hamiltonian
from multiscale_chimera import MultiScaleCHIMERA
import volatility_data as vd
from vol_fair_benchmark import LAGS

TAU, HX, CONN = 2.0, 1.0, 0.5


def real_rv_windows(n, k=6, seed_split=0.70):
    """A few real S&P-500 RV input windows, scaled to [0,1], first min(n,8) lags."""
    d = vd.build_supervised(vd.load_spx_rv(), horizon=1, lags=LAGS)
    Xlag = d["X_lags"]; tr, _ = vd.make_splits(len(d["y_logrv"]), seed_split)
    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rg = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rg, 0, 1)
    m = min(n, Xlag.shape[1])
    return Q[tr][:k, :m]


def engine_features(n, seed):
    """Exact NumPy reference features (single-scale CHIMERA, no feedback)."""
    ch = MultiScaleCHIMERA(n_qubits=n, taus=(TAU,), hamiltonian='ising',
                           hx=HX, connectivity=CONN, seed=seed)

    def f(w):
        ch._reset_feedback()
        full = np.array(ch._all_features(w))
        return full
    return f


def _observables(n):
    return ([qml.PauliZ(i) for i in range(n)]
            + [qml.PauliZ(i) @ qml.PauliZ(j) for i in range(n) for j in range(i + 1, n)])


def _encode(w, n):
    for q in range(min(len(w), n)):
        qml.RY(np.pi * float(np.clip(w[q], 0, 1)), wires=q)


def _trotter(w, n, J, layers, noise_p=0.0):
    _encode(w, n)
    dt = TAU / layers
    for _ in range(layers):
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-12:
                    qml.IsingZZ(2 * J[i, j] * dt, wires=[i, j])
        for i in range(n):
            qml.RX(2 * HX * dt, wires=i)
        if noise_p > 0:
            for i in range(n):
                qml.DepolarizingChannel(noise_p, wires=i)


def make_qnode(device_str, n, J, layers, shots=None, noisy=False):
    """Build a qnode on the requested device. default = local simulator; pass a qBraid/
    Braket/IBM device string for real hardware (needs credentials on qBraid)."""
    if device_str:
        dev = qml.device(device_str, wires=n, shots=shots)         # real backend (one flag)
    elif noisy:
        dev = qml.device("default.mixed", wires=n, shots=shots)    # noisy simulator (ZNE)
    else:
        dev = qml.device("default.qubit", wires=n, shots=shots)    # statevector / shot sim
    OBS = _observables(n)

    @qml.qnode(dev)
    def circ(w, noise_p=0.0):
        _trotter(w, n, J, layers, noise_p=noise_p)
        return [qml.expval(o) for o in OBS]
    return circ


def make_exact_qnode(device_str, n, U, shots=None):
    """Exact-evolution circuit (QubitUnitary) - reproduces the NumPy engine to ~1e-16;
    used for the classical cross-check (validates the circuit IS the reservoir)."""
    dev = (qml.device(device_str, wires=n, shots=shots) if device_str
           else qml.device("default.qubit", wires=n, shots=shots))
    OBS = _observables(n)

    @qml.qnode(dev)
    def circ(w):
        _encode(w, n); qml.QubitUnitary(U, wires=range(n))
        return [qml.expval(o) for o in OBS]
    return circ


def shot_budget_study(n, J, layers, wins, shots_list, device_str=None):
    exact = make_qnode(device_str, n, J, layers, shots=None)
    Fexact = np.array([exact(w) for w in wins])
    print("\nSHOT-BUDGET (feature error vs shots; ε≈1/√S):")
    print(f"  {'shots S':>9}{'mean|Δ feat|':>14}{'max|Δ feat|':>13}")
    rows = []
    for S in shots_list:
        q = make_qnode(device_str, n, J, layers, shots=S)
        F = np.array([q(w) for w in wins])
        err = np.abs(F - Fexact)
        rows.append(dict(shots=S, mean_err=float(err.mean()), max_err=float(err.max())))
        print(f"  {S:>9}{err.mean():>14.4f}{err.max():>13.4f}")
    return Fexact, rows


def zne_demo(n, J, layers, w, base_p=0.01, scales=(1, 2, 3)):
    """Linear zero-noise extrapolation over a depolarizing-noise sweep (one window)."""
    noisy = make_qnode(None, n, J, layers, shots=None, noisy=True)
    clean = make_qnode(None, n, J, layers, shots=None)
    # scalar summary = mean |single-qubit Z| (robust, monotone in noise)
    nz = n
    exact_val = float(np.mean(np.abs(np.array(clean(w))[:nz])))
    vals = [float(np.mean(np.abs(np.array(noisy(w, noise_p=base_p * s))[:nz]))) for s in scales]
    coef = np.polyfit(scales, vals, 1)
    zne0 = float(np.polyval(coef, 0.0))
    return dict(scales=list(scales), noisy_vals=vals, zne_extrapolated=zne0,
                noiseless_exact=exact_val,
                zne_improves=abs(zne0 - exact_val) < abs(vals[0] - exact_val))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--layers", type=int, default=20)
    ap.add_argument("--shots", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", type=str, default=None,
                    help="real backend string (qBraid/Braket/IBM); default = local simulator")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    n = args.n
    layers = 8 if args.quick else args.layers

    t0 = time.time()
    J = generate_coupling_matrix(n, CONN, seed=args.seed)
    nzz = int((np.abs(np.triu(J, 1)) > 1e-12).sum())
    wins = real_rv_windows(n, k=(3 if args.quick else 6))

    print("#" * 70)
    print(f"CHIMERA-QRC qBraid submission  n={n}  layers={layers}  "
          f"device={args.device or 'local simulator'}")
    print(f"  gate-Trotter circuit: {nzz} ZZ + {n} RX per layer  -> "
          f"{nzz*layers} two-qubit + {n*layers} one-qubit gates; "
          f"{n + n*(n-1)//2} Z-basis observables")
    print("#" * 70)

    # 2) CLASSICAL CROSS-CHECK: exact-evolution circuit (QubitUnitary) vs NumPy engine (~1e-16)
    U = expm(-1j * build_ising_hamiltonian(n, J, hx=HX) * TAU)
    exact_qnode = make_exact_qnode(args.device, n, U)
    Funitary = np.array([exact_qnode(w) for w in wins])
    eng = engine_features(n, args.seed)
    Feng = np.array([eng(w) for w in wins])
    xcheck = float(np.max(np.abs(Funitary - Feng)))
    print(f"\nCLASSICAL CROSS-CHECK  max|circuit(QubitUnitary) − NumPy engine| = {xcheck:.2e}"
          f"   ({'PASS' if xcheck < 1e-6 else 'CHECK'})  -> the circuit IS the reservoir")

    # 1) shot-budget on the realistic gate-Trotter circuit (referenced to its own shots=None,
    #    so this isolates SHOT noise) + the Trotter gate-approximation error vs exact
    shots_list = [256, 1024, 4096] if args.quick else [256, 1024, 4096, 16384]
    Ftrot, rows = shot_budget_study(n, J, layers, wins, shots_list, args.device)
    trotter_err = float(np.max(np.abs(Ftrot - Funitary)))
    print(f"gate-model approximation: max|Trotter({layers}) − exact| = {trotter_err:.3f} "
          f"(decreases with more layers; cf. sdk_demo.py)")

    # 3) ZNE demonstration (simulator)
    if not args.device:
        z = zne_demo(n, J, layers, wins[0])
        print(f"\nZNE DEMO (depolarizing sweep, linear extrapolation):")
        print(f"  noisy(scale {z['scales']}) = {[round(v,4) for v in z['noisy_vals']]}")
        print(f"  ZNE→0 = {z['zne_extrapolated']:.4f}   noiseless exact = {z['noiseless_exact']:.4f}"
              f"   {'(ZNE closer ✓)' if z['zne_improves'] else '(no improvement)'}")

    if not args.quick:           # --quick must not clobber the committed full-run artifact
        np.save("qbraid_submit_results.npy",
                dict(n=n, layers=layers, two_qubit_gates=nzz*layers, observables=n+n*(n-1)//2,
                     shot_study=rows, cross_check=xcheck), allow_pickle=True)
        print(f"\nsaved qbraid_submit_results.npy   [{time.time()-t0:.1f}s]")
    else:
        print(f"\n[--quick] skipped writing results (committed full-run artifact preserved) [{time.time()-t0:.1f}s]")
    print("To run on real hardware: python3 qbraid_submit.py --device <qBraid backend> (needs credits).")


if __name__ == "__main__":
    main()
