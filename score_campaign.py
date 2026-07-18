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
DEPOLARIZED_LIMIT = 0.1958          # mean |engine features| over the 3 RV windows
RIGETTI_MEASURED_RAW = 0.2611       # committed characterized negative (2k shots)
GARNET_OQ_PREVIEW_RAW = 0.2382      # single-window OQ-route preview (4k shots)

STAGES = ["raw (scale 1)", "readout-mitigated", "+ ZNE linear", "+ ZNE Richardson"]


def main(path):
    out = json.load(open(path))
    chain = out["chain"]
    device = str(out.get("device", path))
    kind = ("garnet" if "garnet" in device.lower()
            else "ionq" if "ionq" in device.lower() else None)
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
              f"Rigetti {RIGETTI_MEASURED_RAW:.4f} (Garnet OQ preview "
              f"{GARNET_OQ_PREVIEW_RAW:.4f}) -> "
              f"{'CONFIRMED' if raw < min(RIGETTI_MEASURED_RAW, GARNET_OQ_PREVIEW_RAW) else 'REFUTED'}"
              f" (finalize against the native Garnet number when both landed)")
        print(f"      signal-bearing? raw {'<' if raw < DEPOLARIZED_LIMIT else '>='} "
              f"depolarized limit {DEPOLARIZED_LIMIT:.4f} -> "
              f"{'device retains signal at scale 1' if raw < DEPOLARIZED_LIMIT else 'noise-flattened/scrambled regime (as on superconducting)'}")
    if kind == "garnet":
        print(f"(iii) Garnet measured raw exceeds the routing-free 0.171 prediction: "
              f"{'CONFIRMED' if raw > pred['raw (scale 1)'] else 'REFUTED'} "
              f"({raw:.4f} vs 0.171)")
        print(f"      vs depolarized limit {DEPOLARIZED_LIMIT:.4f}: raw is "
              f"{'BEYOND (coherent/routing scrambling, as on Rigetti)' if raw > DEPOLARIZED_LIMIT else 'within (noise not yet fully scrambling)'}")
        print(f"      vs OQ-route single-window preview {GARNET_OQ_PREVIEW_RAW:.4f}: "
              f"full-protocol raw {raw:.4f}")

    print("\n--- cross-platform table (findings-ready) ---")
    print(f"{'device':<26}{'type':<17}{'raw':>8}{'best mitigated':>16}")
    print(f"{'Rigetti Cepheus-1 (107q)':<26}{'superconducting':<17}"
          f"{RIGETTI_MEASURED_RAW:>8.4f}{0.2558:>16.4f}")
    label = {"garnet": "IQM Garnet (20q)", "ionq": "IonQ Forte-1 (36q)"}.get(kind, device)
    typ = {"garnet": "superconducting", "ionq": "trapped-ion"}.get(kind, "?")
    best = min(chain[s][0] for s in STAGES[1:])
    print(f"{label:<26}{typ:<17}{raw:>8.4f}{best:>16.4f}")
    print(f"\njob provenance: {len(out.get('job_ids', []))} job IDs in {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/qpu_run_hw_garnet_native.json")
