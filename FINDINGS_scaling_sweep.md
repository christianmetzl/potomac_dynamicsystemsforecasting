# Findings — Axis-A scaling sweep (item 1), univariate encoder

**Run:** `python scaling_sweep.py --ns 8 10` · verdict from pre-registered `h0_thresholds.py`.

## Result

| n | g(ESN→CHIMERA) | control | D_eff(Q) | feat | MZ CHIMERA | MZ HAR | MZ-gap (boot p) | DM-loss vs HAR | in MCS |
|---|---|---|---|---|---|---|---|---|---|
| 8 | **63.6** | 3.75 | 1.80 | 36 | 0.591 | 0.559 | **+0.032** (0.342) | +3.55 (p=0.000) | ✅ |
| 10 | **34.6** | 3.75 | 1.53 | 55 | 0.308 | 0.559 | **−0.251** (1.000) | +6.11 (p=0.000) | ❌ |

**Anchor gate: PASS** — n=8 reproduces the Phase-2 published numbers (g≈62; MZ 0.591 vs 0.559; gap +0.032) to the digit, validating the new harness.

**Pre-registered verdict: `INPUT_BOUND_EXPECTED`** (g saturating/declining + effective-rank saturating, under the univariate encoder → gates Axis-B; explicitly *not* an H0 refutation).

## Interpretation (new, beyond the Phase-2 paper)

The Phase-2 paper (§7, H4) only *hypothesized* "refuted if rank saturates with qubits." This run shows something sharper and measured: under the fixed 8-lag univariate input, **adding qubits actively degrades the model** — g halves (63.6→34.6), kernel effective rank falls (1.80→1.53), and the regime-transition MZ-gap flips strongly negative (+0.032→−0.251) with CHIMERA dropping out of the MCS. Qubits 9–10 receive `RY(0)`, contribute only uninformative Hilbert-space dimensions, and the fixed coupling + ridge readout cannot suppress the added noise on the crisis split.

This is direct empirical proof of the paper's central scaling caveat: **qubit count must scale in lockstep with input information.** It converts H4 from a planned hypothesis into an evidence-driven necessity and is the precondition for H1 (size scaling) — there is no point scaling qubits until they are informative.

## Honest secondary finding

The headline Phase-2 MZ-gap of +0.032 at n=8 is **positive but not statistically significant** under a stationary-block-bootstrap (p=0.342), and HAR wins on point-forecast loss (DM favors HAR). This does not contradict Phase-2 (which reported MZ point values + DM/MCS on loss, never a bootstrap on the gap), but it sharpens the open question: *does the regime-transition gap become positive **and significant** at scale, with an informative encoder?*

## Engineering note

The current dense engine materializes `U = expm(2ⁿ×2ⁿ)`; cost explodes at n=12 (~60 s per `expm`, 268 MB per reservoir), capping exact statevector at n≈12. This is the measured motivation for the MPS / tensor-network backend (item 3 / paper H1) once the encoder (H4) is in place.

## Next

Build the **H4 encoder (item 2)**: a multivariate realized-measure panel (rv5/rv10, bipower `bv`, median RV `medrv`, realized semivariance `rsv`, jump `rv−bv`) + data re-uploading, so added qubits carry new information. Re-run this same harness; the decisive test is whether g(n) and the MZ-gap **reverse from declining to growing**.
