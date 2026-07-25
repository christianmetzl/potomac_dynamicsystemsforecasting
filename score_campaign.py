#!/usr/bin/env python3
"""Score a completed QPU campaign against the pre-registered predictions.

Reads the results JSON written by qpu_run.py (results/qpu_run_<tag>.json) and
prints (a) the measured mitigation chain, (b) the verdict on each applicable
pre-registered statement from results/qpu_hardware_predictions.md, and (c) the
findings-ready comparison table against the other executed devices.

Usage:
    python3 score_campaign.py results/qpu_run_hw_garnet_native.json
    python3 score_campaign.py results/qpu_run_hw_ionq_native.json

Pure read-only analysis - no jobs, no credits, deterministic.
"""
import json
import sys

# Pre-registered point predictions (results/qpu_hardware_predictions.md, committed
# before any hardware run; 4k-shot rehearsal-calibrated chains).
PREDICTIONS = {
    "garnet": {"raw (scale 1)": 0.171, "readout-mitigated": 0.168,
               "+ ZNE linear": 0.165, "+ ZNE Richardson": 0.147},
    "ionq":   {"raw (scale 1)": 0.149, "readout-mitigated": 0.149,
               "+ ZNE linear": 0.144, "+ ZNE Richardson": 0.122},
}
# Fixed references for interpretation.
# The fully-depolarized limit is mean|F_exact| — the error a device would show if it returned
# the maximally-mixed state. F_exact depends on the reservoir INSTANCE (the seeded coupling
# graph), not on n alone, so the comparator is instance-matched. The table below is keyed
# (n, seed); the seed-0 row is the default used by every org-funded campaign, and the seed-1
# rows are the S7 cross-seed controls. Regenerate any entry with:
#   python3 -c "import numpy as np;from qbraid_submit import engine_features,real_rv_windows;\
#   print(np.abs([engine_features(N,S)(w) for w in real_rv_windows(N,k=3)]).mean())"
DEPOLARIZED_LIMITS_BY_INSTANCE = {
    (8, 0): 0.1958, (10, 0): 0.1790, (12, 0): 0.2140,
    (8, 1): 0.1806, (10, 1): 0.1693,          # S7 cross-seed control instances
}
DEPOLARIZED_LIMITS = {8: 0.1958, 10: 0.1790, 12: 0.2140}   # seed-0 (default instance)
DEPOLARIZED_LIMIT = DEPOLARIZED_LIMITS[8]


def depolarized_limit(n, seed=0):
    """Instance-matched fully-depolarized limit (mean|F_exact| for that seeded reservoir)."""
    return DEPOLARIZED_LIMITS_BY_INSTANCE[(n, seed)]
RIGETTI_MEASURED_RAW = 0.2611       # committed characterized negative (2k shots)
RIGETTI_REPLICATE_RAW = 0.2226      # 4k-shot replication (day-scale drift band ~0.04)
GARNET_OQ_PREVIEW_RAW = 0.2382      # single-window OQ-route preview (4k shots)
GARNET_NATIVE_RAW = 0.2301          # full protocol, native route, 4k shots (Campaign A, n=8)
GARNET_N8_EXCESS = GARNET_NATIVE_RAW - DEPOLARIZED_LIMITS[8]  # 0.0343, the S2 baseline

STAGES = ["raw (scale 1)", "readout-mitigated", "+ ZNE linear", "+ ZNE Richardson"]


def main(path):
    out = json.load(open(path))
    chain = out["chain"]
    device = str(out.get("device", path))
    kind = ("garnet" if "garnet" in device.lower()
            else "emerald" if "emerald" in device.lower()
            else "ionq" if "ionq" in device.lower() else None)
    n = out.get("n", 8)
    shots = out.get("shots")
    shot_floor = (1.0 / max(shots, 1)) ** 0.5 if shots else float("nan")

    print(f"device: {device}   shots/circuit: {shots}   "
          f"(shot floor ~{shot_floor:.4f}, Trotter-20 systematic ~0.04)")
    print(f"\n{'stage':<22}{'measured':>10}{'predicted':>11}")
    pred = PREDICTIONS.get(kind, {})
    for s in STAGES:
        m = chain[s][0]
        p = f"{pred[s]:.3f}" if s in pred else "-"
        print(f"{s:<22}{m:>10.4f}{p:>11}")

    raw = chain[STAGES[0]][0]
    rich = chain[STAGES[-1]][0]
    monotone = all(chain[STAGES[i + 1]][0] <= chain[STAGES[i]][0] + 1e-12
                   for i in range(len(STAGES) - 1))

    print("\n--- pre-registered statements ---")
    print(f"(i)   monotone mitigation recovery on this device: "
          f"{'CONFIRMED' if monotone else 'REFUTED'} "
          f"(raw {raw:.4f} -> Richardson {rich:.4f})")
    if kind == "ionq":
        print(f"(ii)  IonQ raw < superconducting raw: measured {raw:.4f} vs "
              f"Garnet {GARNET_NATIVE_RAW:.4f} / Rigetti {RIGETTI_MEASURED_RAW:.4f} -> "
              f"{'CONFIRMED' if raw < min(RIGETTI_MEASURED_RAW, GARNET_NATIVE_RAW) else 'REFUTED'}"
              f" (both full-protocol native-route numbers)")
        print(f"      signal-bearing? raw {'<' if raw < DEPOLARIZED_LIMIT else '>='} "
              f"depolarized limit {DEPOLARIZED_LIMIT:.4f} -> "
              f"{'device retains signal at scale 1' if raw < DEPOLARIZED_LIMIT else 'noise-flattened/scrambled regime (as on superconducting)'}")
    if kind == "garnet" and n == 8:
        print(f"(iii) Garnet measured raw exceeds the routing-free 0.171 prediction: "
              f"{'CONFIRMED' if raw > pred['raw (scale 1)'] else 'REFUTED'} "
              f"({raw:.4f} vs 0.171)")
        print(f"      vs depolarized limit {DEPOLARIZED_LIMIT:.4f}: raw is "
              f"{'BEYOND (coherent/routing scrambling, as on Rigetti)' if raw > DEPOLARIZED_LIMIT else 'within (noise not yet fully scrambling)'}")
        print(f"      vs OQ-route single-window preview {GARNET_OQ_PREVIEW_RAW:.4f}: "
              f"full-protocol raw {raw:.4f}")
    if kind == "garnet" and n in (10, 12):
        lim = DEPOLARIZED_LIMITS[n]
        excess = raw - lim
        print(f"--- scaling program (qpu_scaling_outlook.md), n={n} ---")
        print(f"(S1)  wall persists at n={n} (raw >= limit {lim:.4f}): "
              f"{'CONFIRMED' if raw >= lim else 'REFUTED - signal-bearing superconducting run, publishable news'} "
              f"(raw {raw:.4f}, excess {excess:+.4f})")
        tail = ("FINAL VERDICT: " + ("CONFIRMED" if excess > GARNET_N8_EXCESS else "REFUTED")
                if n == 12 else "final S2 verdict needs n=12")
        print(f"(S2)  excess vs n=8 baseline {GARNET_N8_EXCESS:+.4f}: this n {excess:+.4f} "
              f"({'grows with depth' if excess > GARNET_N8_EXCESS else 'does NOT grow'}; {tail})")
        print(f"(S4)  ZNE recovery at n={n}: "
              f"{'ABSENT (consistent with S4)' if rich >= raw - 1e-12 else f'present (raw {raw:.4f} -> Richardson {rich:.4f}) - against S4'}")
    if kind == "emerald":
        lim = DEPOLARIZED_LIMITS.get(n, DEPOLARIZED_LIMIT)
        print(f"--- scaling program (qpu_scaling_outlook.md), Emerald n={n} ---")
        print(f"(S3a) newer chip below Garnet n=8 raw {GARNET_NATIVE_RAW:.4f}: "
              f"{'CONFIRMED' if raw < GARNET_NATIVE_RAW else 'REFUTED'} (raw {raw:.4f})")
        print(f"(S3b) still at/above the depolarized limit {lim:.4f}: "
              f"{'CONFIRMED' if raw >= lim else 'REFUTED HIGH - first signal-bearing superconducting execution'} "
              f"(raw {raw:.4f})")

    print("\n--- cross-platform table (findings-ready) ---")
    print(f"{'device':<26}{'type':<17}{'raw':>8}{'best mitigated':>16}")
    print(f"{'Rigetti Cepheus-1 (107q)':<26}{'superconducting':<17}"
          f"{RIGETTI_MEASURED_RAW:>8.4f}{0.2558:>16.4f}")
    if kind != "garnet":
        print(f"{'IQM Garnet (20q)':<26}{'superconducting':<17}"
              f"{GARNET_NATIVE_RAW:>8.4f}{0.2266:>16.4f}")
    label = {"garnet": "IQM Garnet (20q)", "emerald": "IQM Emerald (54q)",
             "ionq": "IonQ Forte-1 (36q)"}.get(kind, device)
    if n != 8:
        label += f" n={n}"
    typ = {"garnet": "superconducting", "emerald": "superconducting",
           "ionq": "trapped-ion"}.get(kind, "?")
    best = min(chain[s][0] for s in STAGES[1:])
    print(f"{label:<26}{typ:<17}{raw:>8.4f}{best:>16.4f}")
    print(f"\njob provenance: {len(out.get('job_ids', []))} job IDs in {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/qpu_run_hw_garnet_native.json")
