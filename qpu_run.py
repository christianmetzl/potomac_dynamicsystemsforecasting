"""
qpu_run.py - the EXECUTE-READY hardware harness for the CHIMERA-QRC validation run.

`qbraid_submit.py` characterizes the plan (shot budget, Trotter error, simulator ZNE).
THIS file is the credit-day runner: the exact code path a real QPU needs, implemented
hardware-grade and rehearsed end-to-end offline, so that when qBraid credits land the
ONLY change is `--mode hw --device <id>`:

  counts-based readout   - one Z-basis shot set yields ALL n+C(n,2) observables
                           (every <Z_i>, <Z_iZ_j> computed from the same bitstring counts).
  readout mitigation     - tensor-product confusion-matrix inversion calibrated from two
                           circuits (|0...0> and |1...1>); exact under the uncorrelated
                           readout model (mthree-style; direct 2^n inversion is cheap at n=8).
  ZNE, hardware-grade    - GLOBAL GATE FOLDING (U -> U(U†U)^k, noise scales 1/3/5) with
                           linear + Richardson extrapolation per observable. (This replaces
                           the simulator noise-dial in qbraid_submit.py, which a real QPU
                           cannot do.)
  classical cross-check  - every run is scored against the exact NumPy engine features.
  self-contained QASM2   - the circuit is emitted as {ry, rx, cx, rz} only (IsingZZ
                           decomposed as CX-RZ-CX), accepted by every gate-model backend;
                           no plugin-specific decomposition surprises.

Backends:
  --mode rehearsal (default)  full-dress offline rehearsal on a local noisy simulator
                              (per-gate depolarizing + readout bit-flip stand-in QPU):
                              runs the IDENTICAL pipeline - calibration, folding, ZNE,
                              mitigation, cross-check - and verifies the mitigation chain
                              actually recovers accuracy. Proves execute-readiness TODAY.
  --mode hw --device <id>     real hardware via the qBraid runtime SDK (QbraidProvider):
                              submits QASM2 jobs, logs job IDs, polls to completion.
  --mode pl --device <str>    alternative: any PennyLane plugin device string.
  --list-devices              enumerate qBraid devices visible to your API key.

Usage:
  python3 qpu_run.py                                  # rehearsal (no credits needed)
  python3 qpu_run.py --list-devices                   # credit-day step 1
  python3 qpu_run.py --mode hw --device qbraid_qir_simulator   # free cloud dry-run
  python3 qpu_run.py --mode hw --device <ionq/ibm/... id> --shots 4000   # THE run

Team EIGENNEXUS | GIC 2026 Phase 3 (hardware validation path; see QPU_RUNBOOK.md)
"""
import argparse
import json
import time
import numpy as np

from scipy.linalg import expm
from qrc_engine import generate_coupling_matrix, build_ising_hamiltonian
from qbraid_submit import engine_features, real_rv_windows

TAU, HX, CONN = 2.0, 1.0, 0.5


# ---------------------------------------------------------------------------
# Circuit as a plain op list  ->  QASM2 / PennyLane / folded variants
# ---------------------------------------------------------------------------
def base_ops(w, n, J, layers):
    """CHIMERA gate-Trotter circuit as (gate, wires, angle) tuples.
    IsingZZ(phi)=exp(-i phi/2 ZZ) decomposed as CX(i,j) RZ(phi)(j) CX(i,j)."""
    ops = [("ry", (q,), np.pi * float(np.clip(w[q % len(w)], 0, 1))) for q in range(n)]
    dt = TAU / layers
    for _ in range(layers):
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-12:
                    ops += [("cx", (i, j), None),
                            ("rz", (j,), 2 * J[i, j] * dt),
                            ("cx", (i, j), None)]
        for i in range(n):
            ops.append(("rx", (i,), 2 * HX * dt))
    return ops


def inverse_ops(ops):
    inv = []
    for g, wires, a in reversed(ops):
        inv.append((g, wires, None if a is None else -a))
    return inv


def folded_ops(ops, scale):
    """Global folding U -> U (U^dag U)^k, k=(scale-1)/2; scale must be odd."""
    assert scale % 2 == 1, "fold scale must be odd (1,3,5,...)"
    out = list(ops)
    for _ in range((scale - 1) // 2):
        out += inverse_ops(ops) + list(ops)
    return out


def to_qasm2(ops, n):
    """Minimal, backend-portable OpenQASM 2.0 (ry/rx/rz/cx + full measurement)."""
    lines = ['OPENQASM 2.0;', 'include "qelib1.inc";',
             f'qreg q[{n}];', f'creg c[{n}];']
    for g, wires, a in ops:
        if g == "cx":
            lines.append(f"cx q[{wires[0]}],q[{wires[1]}];")
        else:
            lines.append(f"{g}({a:.12f}) q[{wires[0]}];")
    lines += [f"measure q[{i}] -> c[{i}];" for i in range(n)]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Counts -> all Z-diagonal observables (the single-setting readout)
# ---------------------------------------------------------------------------
def _norm_counts(counts, n):
    """Normalize keys to plain bitstrings, qubit 0 = leftmost char."""
    out = {}
    for k, v in counts.items():
        k = "".join(str(b) for b in k) if not isinstance(k, str) else k.replace(" ", "")
        out[k.zfill(n)] = out.get(k.zfill(n), 0) + int(v)
    return out


def probs_from_counts(counts, n):
    counts = _norm_counts(counts, n)
    p = np.zeros(2 ** n)
    for k, v in counts.items():
        p[int(k, 2)] += v
    return p / max(p.sum(), 1)


_ZCACHE = {}


def _zmat(n):
    if n not in _ZCACHE:
        bits = (np.arange(2 ** n)[:, None] >> (n - 1 - np.arange(n))) & 1
        _ZCACHE[n] = 1 - 2 * bits          # (2^n, n) of +-1; bit 0 = leftmost = qubit 0
    return _ZCACHE[n]


def features_from_probs(p, n):
    """All <Z_i> then <Z_iZ_j> from ONE probability vector (single-setting readout)."""
    Z = _zmat(n)
    zi = p @ Z
    zz = [float(p @ (Z[:, i] * Z[:, j])) for i in range(n) for j in range(i + 1, n)]
    return np.concatenate([zi, zz])


# ---------------------------------------------------------------------------
# Readout-error mitigation (tensor-product confusion model, exact inversion)
# ---------------------------------------------------------------------------
def confusion_from_calibration(c0, c1, n):
    """Per-qubit 2x2 confusion matrices M_q[meas, true] from |0..0> / |1..1> counts."""
    p0, p1 = probs_from_counts(c0, n), probs_from_counts(c1, n)
    Z = _zmat(n)
    Ms = []
    for q in range(n):
        e0 = float(((1 - Z[:, q]) / 2) @ p0)     # P(read 1 | true 0)
        e1 = float(((1 + Z[:, q]) / 2) @ p1)     # P(read 0 | true 1)
        Ms.append(np.array([[1 - e0, e1], [e0, 1 - e1]]))
    return Ms


def mitigation_matrix(Ms):
    """Inverse of the full tensor-product confusion matrix (2^n x 2^n; fine at n<=10)."""
    M = np.array([[1.0]])
    for Mq in Ms:
        M = np.kron(M, Mq)
    return np.linalg.inv(M)


def mitigate_probs(p, Minv):
    q = Minv @ p
    q = np.clip(q, 0, None)
    return q / max(q.sum(), 1e-12)


# ---------------------------------------------------------------------------
# ZNE over fold scales
# ---------------------------------------------------------------------------
def zne_extrapolate(scales, F_by_scale):
    """Per-observable extrapolation to scale->0. Returns (linear, richardson)."""
    S = np.array(scales, float)
    F = np.stack(F_by_scale)                    # (n_scales, n_feat)
    lin = np.empty(F.shape[1]); rich = np.empty(F.shape[1])
    for k in range(F.shape[1]):
        lin[k] = np.polyval(np.polyfit(S, F[:, k], 1), 0.0)
        # Richardson: exact polynomial through all points, evaluated at 0
        rich[k] = np.polyval(np.polyfit(S, F[:, k], len(S) - 1), 0.0)
    return lin, rich


# ---------------------------------------------------------------------------
# Independent QASM2 verification (exact NumPy interpreter for ry/rx/rz/cx)
# ---------------------------------------------------------------------------
def _apply_1q(psi, M, q, n):
    psi = psi.reshape(2 ** q, 2, 2 ** (n - 1 - q))
    return np.einsum("ab,ibj->iaj", M, psi).reshape(-1)


def _apply_cx(psi, c, t, n):
    idx = np.arange(2 ** n)
    cbit = (idx >> (n - 1 - c)) & 1
    flipped = idx ^ (1 << (n - 1 - t))
    out = psi.copy()
    out[idx[cbit == 1]] = psi[flipped[cbit == 1]]
    return out


def simulate_qasm_exact(qasm, n):
    """Exact statevector simulation of the EMITTED QASM string by an independent
    interpreter (not PennyLane, not the engine) -> all <Z_i>,<Z_iZ_j> features."""
    import re
    psi = np.zeros(2 ** n, complex); psi[0] = 1.0
    for line in qasm.splitlines():
        m = re.match(r"(ry|rx|rz)\((-?[0-9.e+-]+)\) q\[(\d+)\];", line)
        if m:
            g, a, q = m.group(1), float(m.group(2)), int(m.group(3))
            c, s = np.cos(a / 2), np.sin(a / 2)
            M = {"ry": np.array([[c, -s], [s, c]]),
                 "rx": np.array([[c, -1j * s], [-1j * s, c]]),
                 "rz": np.diag([np.exp(-1j * a / 2), np.exp(1j * a / 2)])}[g]
            psi = _apply_1q(psi, M, q, n)
            continue
        m = re.match(r"cx q\[(\d+)\],q\[(\d+)\];", line)
        if m:
            psi = _apply_cx(psi, int(m.group(1)), int(m.group(2)), n)
    return features_from_probs(np.abs(psi) ** 2, n)


def selftest(n=8, layers=20, seed=0):
    """Prove the QASM the QPU will receive IS the reservoir: independent-interpreter
    simulation of the emitted string vs the exact NumPy engine, plus fold-identity."""
    J = generate_coupling_matrix(n, CONN, seed=seed)
    w = real_rv_windows(n, k=1)[0]
    ops = base_ops(w, n, J, layers)
    F_qasm = simulate_qasm_exact(to_qasm2(ops, n), n)
    F_eng = engine_features(n, seed)(w)
    d_trot = float(np.max(np.abs(F_qasm - F_eng)))
    # folding must be an exact identity in the noiseless limit
    F_fold3 = simulate_qasm_exact(to_qasm2(folded_ops(ops, 3), n), n)
    d_fold = float(np.max(np.abs(F_fold3 - F_qasm)))
    print("QPU-PATH SELFTEST (independent QASM2 interpreter):")
    print(f"  max|QASM(Trotter{layers}) - exact engine|  = {d_trot:.4f}  "
          f"(Trotter systematic; expect ~<0.05 at 20 layers)")
    print(f"  max|fold-3 - fold-1| (noiseless identity) = {d_fold:.2e}  (expect ~1e-12)")
    ok = d_trot < 0.06 and d_fold < 1e-8
    print("  PASS - the emitted QASM is the reservoir; folding is noise-only."
          if ok else "  FAIL - investigate before hardware submission.")
    return ok


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------
def run_counts_pennylane(ops, n, shots, device_str=None, p_gate=0.0, p_read=0.0):
    """Execute an op list and return counts. device_str=None -> local simulator
    (mixed if noise requested: the offline stand-in QPU); else any PL plugin device."""
    import pennylane as qml
    if device_str:
        dev = qml.device(device_str, wires=n, shots=shots)
    elif p_gate > 0 or p_read > 0:
        dev = qml.device("default.mixed", wires=n, shots=shots)
    else:
        dev = qml.device("default.qubit", wires=n, shots=shots)

    @qml.qnode(dev)
    def circ():
        for g, wires, a in ops:
            if g == "cx":
                qml.CNOT(wires=list(wires))
                if p_gate > 0:                   # noise rides every 2q gate (the NISQ cost)
                    qml.DepolarizingChannel(p_gate, wires=wires[0])
                    qml.DepolarizingChannel(p_gate, wires=wires[1])
            elif g == "ry":
                qml.RY(a, wires=wires[0])
            elif g == "rx":
                qml.RX(a, wires=wires[0])
            elif g == "rz":
                qml.RZ(a, wires=wires[0])
        if p_read > 0:
            for q in range(n):
                qml.BitFlip(p_read, wires=q)     # readout-error stand-in
        return qml.counts(wires=range(n))
    return circ()


class QbraidRunner:
    """Real-hardware adapter: qBraid runtime SDK. Submits QASM2, logs job IDs, polls."""

    def __init__(self, device_id):
        from qbraid.runtime import QbraidProvider
        self.provider = QbraidProvider()          # needs QBRAID_API_KEY (qBraid account)
        self.device = self.provider.get_device(device_id)
        self.job_ids = []
        self.max_shots = getattr(self.device.profile, "max_shots", None) or 10 ** 9

    def _run_one(self, qasm, shots):
        job = self.device.run(qasm, shots=shots)
        jid = getattr(job, "id", None) or getattr(job, "job_id", "n/a")
        self.job_ids.append(str(jid))
        print(f"    submitted job {jid} ({shots} shots) - waiting...", flush=True)
        res = job.result()
        data = res.data
        return data.get_counts() if hasattr(data, "get_counts") else data.measurement_counts

    def run(self, qasm, shots):
        """Respect the device's per-job shot cap by splitting into batches and
        summing counts (effective shot count preserved). The cap is discovered
        adaptively from the API error if the profile does not expose it."""
        import re
        total = {}
        remaining = shots
        while remaining > 0:
            s = min(remaining, self.max_shots)
            try:
                counts = self._run_one(qasm, s)
            except Exception as e:
                m = re.search(r"maximum of (\d+)", str(e))
                if m and int(m.group(1)) < s:
                    self.max_shots = int(m.group(1))
                    print(f"    (device shot cap discovered: {self.max_shots}/job — batching)",
                          flush=True)
                    continue
                raise
            for k, v in counts.items():
                total[k] = total.get(k, 0) + int(v)
            remaining -= s
        return total


def list_devices():
    from qbraid.runtime import QbraidProvider
    try:
        devs = QbraidProvider().get_devices()
    except Exception as e:
        print(f"Could not list devices ({str(e).splitlines()[0][:120]}).")
        print("Set QBRAID_API_KEY (qBraid account -> API key). No credits needed to list.")
        return
    print(f"{'device id':<44}{'status':<12}qubits")
    for d in devs:
        prof = getattr(d, "profile", None)
        nq = getattr(prof, "num_qubits", "?") if prof else "?"
        try:
            status = str(d.status()).split(".")[-1]
        except Exception:
            status = "?"
        print(f"{str(d.id):<44}{status:<12}{nq}")


# ---------------------------------------------------------------------------
# The validation protocol (identical for rehearsal and hardware)
# ---------------------------------------------------------------------------
def run_protocol(mode, device, n, layers, shots, seed, k_windows, scales, p_gate, p_read):
    J = generate_coupling_matrix(n, CONN, seed=seed)
    wins = real_rv_windows(n, k=k_windows)
    eng = engine_features(n, seed)
    F_exact = np.array([eng(w) for w in wins])          # classical cross-check target
    nobs = n + n * (n - 1) // 2

    runner = None
    if mode == "hw":
        runner = QbraidRunner(device)
    state = {"reverse": False}

    def execute(ops):
        if mode == "hw":
            counts = runner.run(to_qasm2(ops, n), shots)
        else:
            counts = run_counts_pennylane(ops, n, shots, device if mode == "pl" else None,
                                          p_gate=(p_gate if mode == "rehearsal" else 0.0),
                                          p_read=(p_read if mode == "rehearsal" else 0.0))
        if state["reverse"]:
            counts = {k[::-1]: v for k, v in _norm_counts(counts, n).items()}
        return counts

    # 0) bit-order orientation probe: |1> on qubit 0 ONLY. If the backend keys
    #    bitstrings with qubit 0 rightmost, every <Z_i> would be mis-assigned.
    print("\n[0/3] bit-order orientation probe (1 tiny circuit)...", flush=True)
    zi = features_from_probs(probs_from_counts(execute([("ry", (0,), np.pi)]), n), n)[:n]
    if zi[0] < -0.5:
        print("    orientation OK (qubit 0 = leftmost bit)")
    elif zi[-1] < -0.5:
        state["reverse"] = True
        print("    REVERSED bit order detected -> auto-correcting all subsequent counts")
    else:
        print(f"    WARNING: ambiguous orientation (<Z_0>={zi[0]:+.2f}, <Z_{n-1}>={zi[-1]:+.2f}) "
              f"- proceeding unreversed; inspect results")

    # 1) readout calibration: |0..0> and |1..1> (RY(pi)|0> = |1>)
    print("[1/3] readout calibration (2 circuits)...", flush=True)
    cal0 = execute([])                                   # identity -> |0...0>
    cal1 = execute([("ry", (q,), np.pi) for q in range(n)])   # RY(pi)|0> = |1>
    Ms = confusion_from_calibration(cal0, cal1, n)
    Minv = mitigation_matrix(Ms)
    e0s = [float(M[1, 0]) for M in Ms]; e1s = [float(M[0, 1]) for M in Ms]
    print(f"    measured readout errors: mean P(1|0)={np.mean(e0s):.4f}  "
          f"mean P(0|1)={np.mean(e1s):.4f}")

    # 2) folded circuits per window -> mitigated features per scale -> ZNE
    print(f"[2/3] {len(wins)} windows x fold scales {scales} "
          f"({len(wins)*len(scales)} circuits, {shots} shots each)...", flush=True)
    raw1, mit1, zlin, zrich = [], [], [], []
    for wi, w in enumerate(wins):
        ops = base_ops(w, n, J, layers)
        F_scales_raw, F_scales_mit = [], []
        for s in scales:
            counts = execute(folded_ops(ops, s))
            p = probs_from_counts(counts, n)
            F_scales_raw.append(features_from_probs(p, n))
            F_scales_mit.append(features_from_probs(mitigate_probs(p, Minv), n))
        raw1.append(F_scales_raw[0])                     # unmitigated, scale 1
        mit1.append(F_scales_mit[0])                     # readout-mitigated, scale 1
        lin, rich = zne_extrapolate(scales, F_scales_mit)
        zlin.append(lin); zrich.append(rich)
        print(f"    window {wi+1}/{len(wins)} done", flush=True)
    raw1, mit1 = np.array(raw1), np.array(mit1)
    zlin, zrich = np.array(zlin), np.array(zrich)

    # 3) score the accuracy chain against the exact engine (the cross-check)
    def err(F):
        return float(np.mean(np.abs(F - F_exact))), float(np.max(np.abs(F - F_exact)))
    chain = {"raw (scale 1)": err(raw1), "readout-mitigated": err(mit1),
             "+ ZNE linear": err(zlin), "+ ZNE Richardson": err(zrich)}
    print(f"\n[3/3] CLASSICAL CROSS-CHECK - |features - exact engine| over "
          f"{len(wins)} windows x {nobs} observables:")
    print(f"    {'stage':<22}{'mean err':>10}{'max err':>10}")
    for k, (m, mx) in chain.items():
        print(f"    {k:<22}{m:>10.4f}{mx:>10.4f}")
    shot_floor = 1 / np.sqrt(shots)
    trotter_note = 0.04 if layers == 20 else None
    print(f"    (context: shot-noise floor ~{shot_floor:.4f}"
          + (f"; Trotter({layers}) systematic ~{trotter_note}" if trotter_note else "") + ")")
    improved = chain["+ ZNE linear"][0] <= chain["raw (scale 1)"][0] + 1e-9
    print(("    MITIGATION CHAIN VERDICT: readout mitigation + ZNE RECOVER accuracy "
           "(mean error reduced) - pipeline validated." if improved else
           "    MITIGATION CHAIN VERDICT: no improvement at these settings (reported honestly)."))
    return dict(mode=mode, device=device, n=n, layers=layers, shots=shots, scales=list(scales),
                readout_e0=e0s, readout_e1=e1s, chain={k: list(v) for k, v in chain.items()},
                improved=bool(improved),
                job_ids=(runner.job_ids if runner else []),
                p_gate=p_gate, p_read=p_read)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rehearsal", "hw", "pl"], default="rehearsal")
    ap.add_argument("--device", type=str, default=None,
                    help="hw: qBraid device id (see --list-devices); pl: PennyLane device string")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--layers", type=int, default=20)
    ap.add_argument("--shots", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--windows", type=int, default=3)
    ap.add_argument("--scales", type=int, nargs="+", default=[1, 3, 5])
    ap.add_argument("--p-gate", type=float, default=0.004,
                    help="rehearsal: depolarizing prob per qubit per 2q gate (stand-in QPU)")
    ap.add_argument("--p-read", type=float, default=0.02,
                    help="rehearsal: readout bit-flip prob (stand-in QPU)")
    ap.add_argument("--list-devices", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the emitted QASM equals the reservoir (independent interpreter)")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.list_devices:
        list_devices(); return
    if args.selftest:
        ok = selftest(args.n, args.layers, args.seed)
        raise SystemExit(0 if ok else 1)
    if args.mode == "hw" and not args.device:
        raise SystemExit("--mode hw requires --device <qBraid device id> (try --list-devices)")

    n = args.n
    layers = 8 if args.quick else args.layers
    k = 2 if args.quick else args.windows
    shots = 1000 if args.quick else args.shots
    t0 = time.time()
    print("#" * 76)
    print(f"CHIMERA-QRC QPU RUN  mode={args.mode}  device={args.device or 'local stand-in QPU'}")
    print(f"  n={n} layers={layers} shots={shots} windows={k} fold-scales={args.scales}")
    if args.mode == "rehearsal":
        print(f"  stand-in QPU noise: depolarizing {args.p_gate}/qubit/2q-gate + "
              f"readout flip {args.p_read}  (full-dress offline rehearsal)")
    print("#" * 76)

    out = run_protocol(args.mode, args.device, n, layers, shots, args.seed, k,
                       tuple(args.scales), args.p_gate, args.p_read)
    out["wall_clock_s"] = round(time.time() - t0, 1)

    if not args.quick:
        tag = "hw" if args.mode == "hw" else args.mode
        np.save(f"qpu_run_{tag}_results.npy", out, allow_pickle=True)
        with open(f"results/qpu_run_{tag}.json", "w") as f:
            json.dump(out, f, indent=1)
        print(f"\nsaved qpu_run_{tag}_results.npy + results/qpu_run_{tag}.json "
              f"[{out['wall_clock_s']}s]")
        if out["job_ids"]:
            print("job IDs: " + ", ".join(out["job_ids"]))
    else:
        print(f"\n[--quick] results not written  [{out['wall_clock_s']}s]")


if __name__ == "__main__":
    main()
