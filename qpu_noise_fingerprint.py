"""
qpu_noise_fingerprint.py - separate COHERENT from BIASED-INCOHERENT error in the
scrambled hardware regime, from the COMMITTED counts (no new hardware, no credits).

Motivation (reviewer point, 2026-07): "raw error > the 0.196 depolarized limit proves
the noise is not pure depolarization - but a fully depolarizing channel is not the only
incoherent option. Amplitude damping (T1 decay) drives <Z_i> toward +1, and asymmetric
readout also biases <Z> toward +1; either can push error above the limit WITHOUT any
coherent error. So 'coherent/routing scrambling' is under-determined by the threshold test."

This is correct. The threshold test proves "beyond depolarizing"; it does not by itself
separate coherent (unitary/routing) error from biased incoherent error. Here we make that
separation directly from the data, so the mechanism label rests on evidence, not assertion.

Method. For each campaign, readout-correct the scale-1 window counts with that campaign's own
cal0/cal1 (removes the readout contribution to any +1 bias), then over all (qubit x window)
single-qubit expectations fit the affine model
        <Z_i>_measured = a * <Z_i>_exact + b .
Any purely incoherent channel that acts symmetrically across qubits is captured by this model:
  - pure depolarizing  -> a in (0,1), b = 0            (shrink toward 0)
  - amplitude damping  -> a in (0,1), b > 0            (shrink toward, and bias to, |0> => +1)
The RESIDUAL after the best affine fit is what NO scalar shrink-and-bias can explain - the
coherent / structured component. We report:
  b            : the ground-state bias (amplitude-damping / T1 fingerprint), readout-corrected
  a            : the contraction (depolarizing-like shrinkage)
  R2           : fraction of the <Z_i> pattern the incoherent affine model explains
  coh_frac     : residual (coherent) share of the single-qubit error variance = 1 - R2-on-error

Output: results/qpu_noise_fingerprint.md + .json
"""
import json
import numpy as np

from qpu_run import (probs_from_counts, confusion_from_calibration,
                     mitigation_matrix, mitigate_probs)
from qbraid_submit import engine_features, real_rv_windows

CAMPAIGNS = [
    ("hw_rigetti_rep",      8,  "Rigetti (4k rep)",   "scrambled"),
    ("hw_garnet_native",    8,  "Garnet (Camp. A)",   "scrambled"),
    ("hw_garnet_n8_anchor", 8,  "Garnet (anchor)",    "scrambled"),
    ("hw_garnet_n8_pair",   8,  "Garnet (pair)",      "scrambled"),
    ("hw_ionq_native",      8,  "IonQ Forte-1",       "signal-bearing"),
    ("hw_emerald_n8",       8,  "Emerald",            "signal-bearing"),
    ("hw_garnet_n10",       10, "Garnet n=10",        "signal-bearing"),
]


def single_qubit_measured_exact(tag, n):
    ck = json.load(open(f"results/qpu_ckpt_{tag}.json"))
    # readout confusion from this campaign's own calibrations
    Ms = confusion_from_calibration(ck["jobs"]["cal0"]["counts"],
                                    ck["jobs"]["cal1"]["counts"], n)
    Minv = mitigation_matrix(Ms)
    wins = real_rv_windows(n, k=3)
    eng = engine_features(n, 0)
    meas, exact = [], []
    for i in range(3):
        p = probs_from_counts(ck["jobs"][f"w{i}_s1"]["counts"], n)
        p = mitigate_probs(p, Minv)            # readout-corrected
        Z = ((np.arange(2 ** n)[:, None] >> (n - 1 - np.arange(n))) & 1)
        Z = 1 - 2 * Z
        meas.append(p @ Z)                     # measured <Z_i>, i=0..n-1
        exact.append(eng(wins[i])[:n])         # exact  <Z_i>
    return np.concatenate(meas), np.concatenate(exact)


def analyze(tag, n):
    m, e = single_qubit_measured_exact(tag, n)
    # affine fit m = a*e + b
    A = np.vstack([e, np.ones_like(e)]).T
    (a, b), *_ = np.linalg.lstsq(A, m, rcond=None)
    fit = a * e + b
    ss_tot = np.sum((m - m.mean()) ** 2)
    r2 = 1 - np.sum((m - fit) ** 2) / max(ss_tot, 1e-12)
    # error decomposition: total single-qubit error vs affine-explained vs residual
    err_tot = np.mean(np.abs(m - e))
    err_resid = np.mean(np.abs(m - fit))       # coherent (unexplained by shrink+bias)
    coh_frac = np.var(m - fit) / max(np.var(m - e), 1e-12)
    return {"a": float(a), "b": float(b), "r2": float(r2),
            "mean_measured_Zi": float(m.mean()), "mean_exact_Zi": float(e.mean()),
            "err_tot_1q": float(err_tot), "err_resid_1q": float(err_resid),
            "coherent_frac": float(np.clip(coh_frac, 0, 1))}


def main():
    out, rows = {}, []
    for tag, n, label, regime in CAMPAIGNS:
        r = analyze(tag, n); r["regime"] = regime; out[tag] = r
        rows.append((label, regime, r))
        print(f"{label:20s} [{regime:14s}] bias b={r['b']:+.3f}  a={r['a']:.3f}  "
              f"R2={r['r2']:.2f}  coherent-residual share={r['coherent_frac']*100:4.0f}%  "
              f"(mean measured <Z>={r['mean_measured_Zi']:+.3f})")
    with open("results/qpu_noise_fingerprint.json", "w") as f:
        json.dump(out, f, indent=1)

    scr = [r for _, reg, r in rows if reg == "scrambled"]
    mean_b = np.mean([r["b"] for r in scr])
    mean_coh = np.mean([r["coherent_frac"] for r in scr])
    md = ["# Noise fingerprint: coherent vs biased-incoherent error in the scrambled regime",
          "",
          "*Readout-corrected re-analysis of the committed counts (no new hardware). Answers",
          "whether the beyond-limit superconducting error is coherent (routing/unitary) or",
          "biased-incoherent (amplitude damping / T1). Method and caveats in the module header.*",
          "",
          "| campaign | regime | ground-state bias b | contraction a | affine R² | coherent-residual share |",
          "|---|---|---|---|---|---|"]
    for label, regime, r in rows:
        md.append(f"| {label} | {regime} | {r['b']:+.3f} | {r['a']:.3f} | {r['r2']:.2f} | "
                  f"{r['coherent_frac']*100:.0f}% |")
    md += ["",
           f"**Scrambled-regime summary:** mean ground-state bias b = {mean_b:+.3f}, "
           f"mean coherent-residual share = {mean_coh*100:.0f}%.",
           "",
           "**Reading.** A large positive `b` with high affine R² would mean amplitude damping /",
           "readout bias (an *incoherent* channel) explains the beyond-limit error — in which case",
           "'coherent scrambling' would be the wrong label. A `b` near zero with a large",
           "coherent-residual share means no scalar shrink-and-bias reproduces the measured pattern:",
           "the error is structured, consistent with coherent routing error. The measured values",
           "above place each scrambled campaign on that spectrum; the paper's wording is set to",
           "match what they show, and no headline verdict (which side of the limit) depends on this",
           "attribution — that is fixed by the threshold test and hardened to 9.7–24σ by the",
           "bootstrap (`results/qpu_bootstrap_ci.md`)."]
    with open("results/qpu_noise_fingerprint.md", "w") as f:
        f.write("\n".join(md) + "\n")
    print("\nsaved results/qpu_noise_fingerprint.md + .json")
    print(f"SCRAMBLED-REGIME: mean b={mean_b:+.3f}, mean coherent-residual share={mean_coh*100:.0f}%")


if __name__ == "__main__":
    main()
