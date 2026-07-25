# Anticipated questions — answered with evidence

*Questions a careful reviewer is likely to ask, answered here with a pointer to committed,
reproducible evidence. Nothing below is new work introduced after the fact — every artifact
referenced was committed with the result it supports (verifiable by the `commit` tag on each
QPU job and by `git log`). One command checks the lot: `python3 cli.py verify`.*

### 1. "There is no quantum advantage — is this still a meaningful result?"
We think so, and we report the negative as the headline: against strong *fair* baselines (HAR-X, recurrent ESN,
RFF; 8 seeds; HAC-DM; Holm) the reservoir shows **no significant forecasting advantage at
simulable scale — H0 refuted** (`axisB_rigorous_findings.md`). A pre-registered,
adversarially-controlled negative — plus a hardware program that refuted **four of its own
pre-registered** predictions under controls (S1, S2, S3b, and the S7 cross-seed control) — is a more reliable contribution to the field than an
overstated claim, and it is the opposite of cherry-picking.

### 2. "Weather RMSE (°C) appears in a financial-volatility submission."
Deliberate: it is a **cross-domain generality** check (the challenge itself has a weather
track). The *same* engine/protocol shows the same negative on chaotic weather as on RV, which
is stronger evidence than a finance-only result. Clearly labeled as such in §5 of the paper.

### 3. "IonQ ran 500 shots, not the pre-registered 4,000."
Disclosed, not hidden: a cost-forced deviation (4k config ≈ 352,000 credits at 8 cr/shot, out
of scope), documented in `qpu_campaign_manifest.md` *before* execution, with the statistical
justification (s.e. ≈ 0.004 over 108 observables). The IonQ verdict (raw 0.104, below the 0.196
limit) clears its decision boundary by **18σ** of shot noise (`qpu_bootstrap_ci.md`) — 500
shots is ample.

### 4. "Does raw error > the 0.196 depolarized limit really prove *coherent* scrambling? Amplitude
damping (T1) also biases ⟨Z⟩ and could exceed the limit."
A fair, precise objection — and we settle it with data, not assertion
(`qpu_noise_fingerprint.md`, `cli.py run qpu_fingerprint`). A readout-corrected affine
shrink-and-bias fit (which captures *any* depolarizing + damping mix) explains ≤8% of the
measured ⟨Z_i⟩ pattern; **77–99% is coherent residual** → predominantly coherent routing error.
The objection is partly right: Garnet shows a real but **subdominant** damping bias (b ≈
+0.15–0.24); Rigetti shows ≈0. "Beyond the limit" alone proves only *non-depolarizing*; the
fingerprint earns the coherent attribution. Wording corrected accordingly.

### 5. "Hardware point values drift day-to-day, so the numbers aren't reproducible."
True, and we measured it rather than hiding it: a 4k-shot Rigetti replication showed ~0.04
day-scale drift (> shot noise). The robust currency is therefore the **regime** (which side of
the size-matched limit), not the point value — and every **bootstrapped** regime verdict — the nine campaigns with committed counts — sits
**9.7–23.9σ** beyond shot noise (`qpu_bootstrap_ci.md`). The size effect is drift-controlled by a **same-session n=8
anchor** and the generation effect by a **same-window two-chip pair** — both pre-registered.

### 6. "The n=10/n=12 signal-bearing results rest on single seed-0 instances."
Acknowledged in the paper. We pre-registered the discriminating experiment, **S7**
(`qpu_scaling_outlook.md`, committed at `89cce5f` before launch), and **executed its primary
H-INSTANCE arm** (same-session Garnet, free personal OpenQuantum credits). Scored by the
committed decision rule: an **independent seed-1 instance at n=10 is signal-bearing** (raw 0.146
< 0.179) — the n=10 result **reproduces off the seed-0 instance**, directly answering this
objection for the signal-bearing sizes; and **seed-1 n=8 is signal-bearing** (0.159 < 0.196)
while the same-session seed-0 n=8 anchor stays scrambled (0.228), so the n=8 scrambling is
**seed-0-instance-specific, not a size law** — H-INSTANCE refuted, mechanism localized.
We also re-scored both seed-1 runs against the **stricter instance-matched** limits (0.1806 /
0.1693 — the pre-registered rule used the seed-0 values): the margins shrink to −0.021 / −0.024
but **both verdicts are unchanged**, and the decisive raw-vs-raw contrast (0.159 vs 0.228, same
chip and session, fixed size) needs no limit at all. Disclosed in full — see
`qpu_hardware_findings.md` (§S7, "Self-correction").

### 7. "Can judges actually reproduce this, and is the data accessible?"
Yes — verified. The full reproduction runs **offline** with no qBraid account, credits, or
network (`python3 reproduce.py --quick`); every dataset it needs is committed under `data/` and
`v{2,3}_research/`. Demonstrated by running the pipeline with the network cut. QPU runs are
**committed evidence** (job IDs + counts), verified via qBraid's platform records and re-derived
by `credit_audit.py` / `qpu_bootstrap_ci.py`, not re-executed (they cost real credits and aren't
bit-for-bit rerunnable).

### 8. "Are the hardware runs real, or self-reported?"
Independently verifiable three ways: (a) every job in every funded campaign (job tagging was added 2026-07-19, before the funded program; earlier de-risking jobs predate it) embeds the **repo commit hash** in qBraid's
timestamped records — a hash-preimage commitment that predictions predate data; (b) per-job
billing reconciles to the half-credit and is **re-derived from published pricing** by
`credit_audit.py` (no API key needed); (c) some job records are **public** on the OpenQuantum
dashboard. Whole-program spend: 60,698.25 of the 65,000 org ceiling, fully attributed
(`CREDIT_BUDGET.md`).

### 9. "The platform findings are unconfirmed."
Stated as such. Findings 1–2 (qir-sv anomaly; IonQ negative-angle loss) ship with full
reproduction bundles (`platform_feedback_bundle/`). Finding 3 (silent cross-account billing) is
explicitly labeled **our reconstruction, not yet vendor-confirmed**. We never claim vendor
endorsement we do not have.

### 10. "What would change your conclusion?"
Named in advance: S3b failing high on a newer chip (it did — Emerald is signal-bearing at n=8);
S5b (a hardware-in-the-loop forecast beating HAR-X) — we consider it very unlikely and say so.
The conclusion is falsifiable, and we committed the tests that would overturn it.
