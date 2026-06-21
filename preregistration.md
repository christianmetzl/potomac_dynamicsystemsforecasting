# CHIMERA-QRC Phase-3 — Pre-Registration of H0 Confirm/Refute Thresholds

**Team EIGENNEXUS · Global Industry Challenge 2026 · Track A (Financial Volatility)**
**Locked: 2026-06-21 (v1.0) · Amended 2026-06-21 (v1.1) — before any *scaling* result was seen.**

> **Amendment log**
> - **v1.1 (2026-06-21):** During harness validation (n=8 anchor only — a reproduction of
>   already-published Phase-2 numbers, *not* a new scaling result), we found the v1.0
>   accuracy gate used Diebold–Mariano on *point-forecast loss* as the significance test,
>   whereas H0 is stated in terms of the *regime-transition MZ-R² gap*. These diverge
>   (CHIMERA wins on regime efficiency; HAR wins on point RMSE), so the v1.0 `refute`
>   branch could mislabel a genuine regime-transition win as a failure. Fix ("require both,
>   soften refute"): CONFIRM still requires a **significant** MZ-gap (point estimate **and**
>   a block-bootstrap test) **and** a DM point-loss win **and** MCS membership; but a
>   *significant positive MZ-gap with MCS membership* now returns **INCONCLUSIVE**, never
>   REFUTE. No n=10/12 scaling result had been observed at amendment time, and the change
>   makes CONFIRM *harder*, not easier (the n=8 gap is bootstrap-insignificant, p≈0.34).

> This document and its machine-readable companion `h0_thresholds.py` fix the decision
> rules for the Phase-3 scaling study **in advance**, so the experiment is honestly
> bounded. `scaling_sweep.py` imports `h0_thresholds.py` and emits the verdict
> mechanically — the thresholds cannot be tuned after seeing the curves. We commit to
> reporting a **refutation** as a publishable finding.

---

## 1. Hypothesis

**H0.** The 8-qubit kernel-*distinctness* (geometric difference *g*) and parameter-efficiency
edge measured in Phase 2 becomes a **forecasting-accuracy** gap at scale, in the regime
where exact classical simulation is infeasible.

The whole study reduces to two curves in qubit count *n*:

| Curve | Definition | H0 requires |
|---|---|---|
| **g(n)** | geometric difference *g*(ESN → CHIMERA) on the train-window kernel | keeps **growing** (does not saturate) |
| **mz_gap(n)** | MZ-R²(CHIMERA) − MZ-R²(HAR) on the regime-transition (GFC-in-test) split | turns **positive & significant** (DM, MCS) beyond the exact-sim frontier |

---

## 2. Anchor-reproduction gate (must pass before any new *n* is trusted)

The new sweep harness must reproduce the Phase-2 published anchors within locked tolerance,
or the harness is presumed wrong and **no swept point may be reported**:

| Anchor | Phase-2 value | Tolerance (`h0_thresholds.py`) |
|---|---|---|
| g(n=8, 1-scale) = g(ESN-108 → CHIMERA-1scale) | **62** | ±15 % → [52.7, 71.3] |
| g control (ESN-108 → ESN-108′) | **4.3** | reported alongside (sanity) |
| mz_gap(n=8, 3-scale) = 0.591 − 0.559 | **+0.032** | ±0.020 → [+0.012, +0.052] |

Enforced by `anchor_ok()` and surfaced as `HARNESS_FAIL` in `h0_verdict()`.

---

## 3. Locked thresholds

All constants live in `h0_thresholds.py` (single source of truth):

- **Exact-simulation frontier:** `EXACT_SIM_FRONTIER_N = 30` qubits. Verdicts are only
  *decisive* beyond this.
- **g(n) "growing":** top-step Δg ≥ `2.0 ×` the classical-classical control magnitude
  (`G_GROWTH_CONTROL_MULT`). **"saturating":** top-step Δg ≤ the control magnitude
  (rise has flattened to within classical noise).
- **Effective-rank guard:** kernel participation ratio rise ≥ `0.5` per +2 qubits to count
  as still "rising" (`DEFF_SAT_PER_2Q`). Distinguishes *input-bound* from *size-bound*.
- **Accuracy confirm (v1.1):** the regime-transition MZ-gap is **significant** — mz_gap ≥
  `+0.020` (`MZ_GAP_CONFIRM`) **and** a stationary-block-bootstrap of the gap rejects at
  `α = 0.05` (`MZ_GAP_BOOT_ALPHA`) — **and** CHIMERA also beats HAR on point loss (one-sided
  Diebold–Mariano at `α = 0.05`, correct sign) **and** CHIMERA in the 95 % MCS.
- **Accuracy soften (v1.1):** a **significant positive MZ-gap with MCS membership** but no
  point-loss win returns **INCONCLUSIVE**, never REFUTE — a real regime-transition edge that
  has not (yet) become a point-accuracy edge is not a refutation.

### Decision rules
- **CONFIRM** — *both* curves favourable (g growing **and** accuracy-confirm), evaluated
  **beyond the exact-sim frontier with the new-information (Axis-B) encoder.**
- **REFUTE** (reported as a finding) — at decisive scale/encoding, *either* g saturates
  *or* there is genuinely no accuracy edge over HAR (mz_gap ≤ 0, or no significant edge on
  either axis and not in the MCS).
- **INPUT_BOUND_EXPECTED** — g(n) **and** effective rank saturate **under the univariate
  8-lag encoder.** This is the *predicted* input-bottleneck signature; it **gates the move
  to Axis-B** and is **explicitly not** an H0 refutation (see §4).
- **INCONCLUSIVE** — favourable/unfavourable but below the decisive encoding/scale.

---

## 4. The input-bottleneck guard (why the first sweep cannot refute H0)

The current encoder injects one lag per qubit and fills only `min(8, n)` qubits — verified
in code (`delay_qrc.py: _step_features`). With the fixed 8-lag input, **qubits beyond 8
receive no independent information**; they enter the dynamics only through the fixed
coupling. We therefore **pre-register the prediction** that, under the univariate encoder,
**g(n) and kernel effective-rank D_eff(n) will saturate for n > 8.**

Consequently the first experiment — `scaling_sweep.py` over **n ∈ {8, 10, 12}, univariate**
— is scoped as a **harness validation + input-bound diagnostic**, not as a test of H0.
Its only H0-relevant outputs are:
- confirmation that the harness reproduces the n=8 anchor, and
- the empirical D_eff(n) trace that **justifies prioritising Axis-B** (multivariate sector/index
  RV panel + data re-uploading) as the real scaling test.

A `saturating` g under `univariate` encoding returns `INPUT_BOUND_EXPECTED`, never `REFUTE`.

---

## 5. What would make us *abandon* the thesis

To pre-commit symmetrically (guarding against motivated reasoning), we will report H0 as
**refuted** if, **with the Axis-B encoder active and n beyond the exact-sim frontier**, the
geometric difference saturates (Δg ≤ control magnitude) while D_eff still rises — i.e. the
distinctness fails to grow even though added qubits *do* carry new information — **or** the
regime-transition accuracy gap over HAR fails to become positive and DM-significant at the
largest scale we can reach (simulated or hardware). A clean negative at ≈80 qubits is a real
result about the limits of QRC for volatility, and we will publish it as such.

---

*Companion file:* `h0_thresholds.py` (constants + `anchor_ok`, `g_curve_status`,
`deff_status`, `accuracy_status`, `h0_verdict`). *Consumer:* `scaling_sweep.py` (to be added
in the next commit, after these thresholds are locked).
