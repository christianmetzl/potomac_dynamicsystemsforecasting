"""
cli.py - CHIMERA-QRC unified, agent-executable reproduction interface (qBraid Skill).

This is the single functional entry point the Phase-3 brief asks for: "a structured,
agent-executable package that allows an AI coding agent to navigate the codebase,
configure the reservoir, run training, and reproduce results end-to-end."

Every headline result is a named ACTION. An agent (or a human, or a judge) can list
actions and run any of them without reading the source:

  python3 cli.py list                 # enumerate actions (also see qbraid_skill.yaml)
  python3 cli.py run <action>         # run one action
  python3 cli.py run all --quick      # fast end-to-end smoke of everything
  python3 cli.py run headline         # the Phase-3 headline results
  python3 cli.py reproduce            # full Phase-2 + Phase-3 reproduction

Actions wrap the individual scripts so the interface stays stable even as internals
change. `--quick` is passed through where supported for a fast smoke.

Team EIGENNEXUS | GIC 2026 - Phase 3 (qBraid Skill / reproduction interface)
"""
import argparse
import subprocess
import sys
import time

PY = sys.executable

# action -> (script + args, one-line description, supports_quick)
ACTIONS = {
    # ---- Phase-2 headline reproductions ----
    "tests":        (["tests.py"], "Engine sanity tests (23 checks)", False),
    "calm":         (["vol_fair_benchmark.py"], "Calm-window Table 1 + Model Confidence Set", False),
    "crisis":       (["vol_crisis_benchmark.py"], "Crisis split (GFC in test): RMSE/QLIKE/MZ + MCS", False),
    "kernel":       (["kernel_analysis.py"], "Kernel geometry: g(ESN->CHIMERA)~62 vs ~4 control", False),
    "sdk":          (["sdk_demo.py"], "Explicit PennyLane circuit (engine match ~5e-16)", False),
    "gk":           (["gk_validation.py"], "Independent 2022-2026 SPY (Garman-Klass) check", False),
    "baselines":    (["har_garch_baselines.py"], "HAR/GARCH/GJR/AR(3)/persistence baselines", False),
    "lstm":         (["lstm_baseline.py"], "LSTM baseline (Track A, brief-named)", True),
    # ---- Phase-3 deliverables ----
    "prereg":       (["preregistration.py"], "Print pre-registered H0/H1/H4 thresholds", False),
    "scaling":      (["scaling_sweep.py"], "Scaling sweep: g(n), MZ-gap(n), rank(n) + noise", True),
    "axisB":        (["scaling_sweep_axisB.py"], "Axis-B: informed encoding vs idle qubits (n=10 beat)", True),
    "mnist":        (["mnist_benchmark.py"], "MNIST common cross-team benchmark (accuracy vs n)", True),
    "mnist_noise":  (["mnist_benchmark.py", "--noise-only"], "MNIST noise-rate robustness curve", False),
    "tensor":       (["tensor_backend.py"], "Sparse/TN frontier + bond-dimension complexity metric", True),
    "axisB_rig":    (["axisB_rigorous.py"], "Axis-B HARDENED: HAR-X + recurrent-ESN + RFF, HAC-DM, Holm", True),
    "tensor_check": (["tensor_backend.py", "--check"], "Verify sparse backend matches dense engine", False),
}

# curated bundles
GROUPS = {
    "headline": ["prereg", "scaling", "axisB_rig", "mnist", "tensor"],   # Phase-3 story (axisB_rig = honest test)
    "phase2":   ["tests", "calm", "crisis", "kernel", "sdk"],            # Phase-2 reproduction
    "all":      list(ACTIONS.keys()),
    "reproduce": ["tests", "calm", "crisis", "kernel", "sdk",
                  "baselines", "lstm", "prereg", "scaling", "axisB", "axisB_rig",
                  "mnist", "tensor"],
}


def _run_one(name, quick):
    if name not in ACTIONS:
        print(f"!! unknown action: {name}"); return 1
    script_args, desc, supports_quick = ACTIONS[name]
    cmd = [PY] + script_args + (["--quick"] if (quick and supports_quick) else [])
    print("\n" + "=" * 84)
    print(f">>> action '{name}': {desc}")
    print(f"    $ {' '.join(cmd)}")
    print("=" * 84, flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd).returncode
    print(f"--- action '{name}' finished rc={rc} in {time.time()-t0:.1f}s")
    return rc


def main():
    ap = argparse.ArgumentParser(description="CHIMERA-QRC reproduction interface")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="list available actions and groups")
    r = sub.add_parser("run", help="run an action or group")
    r.add_argument("action")
    r.add_argument("--quick", action="store_true", help="fast smoke where supported")
    # convenience aliases (one subparser per group, including 'reproduce')
    for g in GROUPS:
        sub.add_parser(g, help=f"run group '{g}'").add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.cmd in (None, "list"):
        print("CHIMERA-QRC actions (python3 cli.py run <action>):\n")
        for k, (s, d, q) in ACTIONS.items():
            print(f"  {k:<14} {d}{'  [--quick]' if q else ''}")
        print("\nGroups (python3 cli.py run <group>  or  python3 cli.py <group>):")
        for g, items in GROUPS.items():
            print(f"  {g:<14} {' '.join(items)}")
        return 0

    quick = getattr(args, "quick", False)
    target = args.action if args.cmd == "run" else args.cmd
    names = GROUPS.get(target, [target])

    rcs = {}
    for name in names:
        rcs[name] = _run_one(name, quick)
    print("\n" + "#" * 84)
    print("SUMMARY:", ", ".join(f"{k}={'OK' if v == 0 else 'FAIL('+str(v)+')'}"
                                for k, v in rcs.items()))
    print("#" * 84)
    return 0 if all(v == 0 for v in rcs.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
