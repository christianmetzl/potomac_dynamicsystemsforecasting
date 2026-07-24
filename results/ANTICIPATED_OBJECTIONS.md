# Anticipated questions — answered with evidence

*Questions a careful reviewer is likely to ask, answered here with a pointer to committed,
reproducible evidence. Nothing below is new work introduced after the fact — every artifact
referenced was committed with the result it supports (verifiable by the `commit` tag on each
QPU job and by `git log`). One command checks the lot: `python3 cli.py verify`.*

### 1. "There is no quantum advantage — is this still a meaningful result?"
We think so, and we report the negative as the headline: against strong *fair* baselines (HAR-X, recurrent ESN,
RFF; 8 seeds; HAC-DM; Holm) the reservoir shows **no significant forecasting advantage at
simulable scale — H0 refuted** (`axisB_rigorous_findings.md`). A pre-registered,
adversarially-controlled negative — plus a hardware program that refuted **three of its own
four** predictions under controls — is a more reliable contribution to the field than an
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
the size-matched limit), not the point value — and every regime verdict sits **9.7–24σ** beyond
shot noise (`qpu_bootstrap_ci.md`). The size effect is drift-controlled by a **same-session n=8
anchor** and the generation effect by a **same-window two-chip pair** — both pre-registered.

### 6. "The n=10/n=12 signal-bearing results rest on single seed-0 instances."
Acknowledged in the paper (mechanism "honestly open"). We pre-registered the discriminating
experiment, **S7** (`qpu_scaling_outlook.md`): the same instance re-embedded on a permuted qubit
subset, one session — falsifiable both ways (embedding-dominant vs instance-dominant). Committed
before execution; unrun only because it is post-ceiling/post-deadline.

### 7. "Can judges actually reproduce this, and is the data accessible?"
Yes — verified. The full reproduction runs **offline** with no qBraid account, credits, or
network (`python3 reproduce.py --quick`); every dataset it needs is committed under `data/` and
`v{2,3}_research/`. Demonstrated by running the pipeline with the network cut. QPU runs are
**committed evidence** (job IDs + counts), verified via qBraid's platform records and re-derived
by `credit_audit.py` / `qpu_bootstrap_ci.py`, not re-executed (they cost real credits and aren't
bit-for-bit rerunnable).

### 8. "Are the hardware runs real, or self-reported?"
Independently verifiable three ways: (a) every job embeds the **repo commit hash** in qBraid's
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
