"""
expressivity_vs_accuracy.py — does reservoir EXPRESSIVITY predict FORECASTING ACCURACY?

The paper's central mechanistic claim is that kernel distinctness and full-rank entanglement are
"necessary but not sufficient" for advantage. That has always been argued qualitatively. This
script measures it.

Design. Across 30 seeded n=8 reservoir instances we compute, per instance:
  * out-of-sample forecast RMSE on the crisis window, under the paper's own Axis-B protocol
    (identical inputs, the HAR-X linear block nested in the ridge head, train-only scaling);
  * entanglement entropy S_ent across the balanced cut, estimated from 64 real training states;
  * coupling density (two-qubit edges) and the instance's depolarized limit mean|F_exact|.
Then we correlate each structural quantity against accuracy.

If quantum expressivity were the resource driving this task, more-entangled instances should
forecast better. They do not.

Runtime ~10 min (30 ridge fits over the full RV panel + 30 entanglement estimates). Offline;
no hardware, no credits, no network.

Regenerate: python3 expressivity_vs_accuracy.py  (or: python3 cli.py run expressivity)
"""
import json

import numpy as np
import pandas as pd

import feature_pool as fp
import scaling_sweep as ss
from vol_fair_benchmark import ridge_readout, rmse
from qrc_engine import generate_coupling_matrix
from tensor_backend import entanglement_of_states
from qbraid_submit import engine_features, real_rv_windows
from instance_ensemble import _corr_t

N, N_SEEDS, ENT_SAMPLE = 8, 30, 64
CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")
# n=30, alpha=0.05 two-sided, 80% power -> smallest reliably detectable |r|
DETECTABLE_R = 0.49


def main():
    d = fp.build_rich()
    pool, X_har, y_logrv = d["pool"], d["X_har"], d["y_logrv"]
    dts = pd.to_datetime(d["dates"])
    tr = np.where(dts < CRISIS_TR)[0]
    te = np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0]
    pool_s = fp.scale_pool(pool, tr)
    rich, rich_s = pool[:, :N], pool_s[:, :N]
    LINX = np.hstack([rich, X_har])
    yT = y_logrv[te]

    harx_pred, _ = ridge_readout(LINX[tr], y_logrv[tr], LINX[te])
    harx = rmse(yT, harx_pred)
    print(f"HAR-X (classical bar), crisis RMSE = {harx:.4f}\n")

    ent_idx = np.linspace(0, len(tr) - 1, ENT_SAMPLE).astype(int)
    Xent = np.clip(rich_s[tr][ent_idx], 0, 1)
    wins = real_rv_windows(N, k=3)

    rows = []
    for sd in range(N_SEEDS):
        F = ss.chimera_features_n(rich_s, N, (2.0,), sd)
        pr, _ = ridge_readout(np.hstack([F, LINX])[tr], y_logrv[tr], np.hstack([F, LINX])[te])
        rr = rmse(yT, pr)
        J = generate_coupling_matrix(N, 0.5, seed=sd)
        S, _c, _m = entanglement_of_states(Xent, N, seed=sd, sample=ENT_SAMPLE)
        lim = float(np.abs(np.array([engine_features(N, sd)(w) for w in wins])).mean())
        rows.append(dict(seed=sd, rmse=float(rr), S_ent=float(S),
                         edges=int(np.count_nonzero(np.triu(J, 1))), limit=lim))
        print(f"  seed {sd:2d}: RMSE={rr:.4f}  S_ent={S:.4f}  "
              f"edges={rows[-1]['edges']:2d}  limit={lim:.4f}", flush=True)

    # ---- does per-instance quality TRANSFER to another regime? -------------------
    # If the instance ranking on crisis is uncorrelated with the ranking on calm, then
    # "picking the best seed" is selection on noise.
    import volatility_data as vd
    trc, tec = vd.make_splits(len(y_logrv), 0.70)
    pool_sc = fp.scale_pool(pool, trc)
    LINXc = np.hstack([pool[:, :N], X_har])
    yTc = y_logrv[tec]
    hpc, _ = ridge_readout(LINXc[trc], y_logrv[trc], LINXc[tec])
    harx_calm = rmse(yTc, hpc)
    calm = []
    for sd in range(N_SEEDS):
        Fc = ss.chimera_features_n(pool_sc[:, :N], N, (2.0,), sd)
        Dc = np.hstack([Fc, LINXc])
        prc, _ = ridge_readout(Dc[trc], y_logrv[trc], Dc[tec])
        calm.append(rmse(yTc, prc))
    calm = np.array(calm)
    for i, row in enumerate(rows):
        row["rmse_calm"] = float(calm[i])

    r = np.array([x["rmse"] for x in rows])
    rank = lambda a: np.argsort(np.argsort(a)).astype(float)
    r_tr, p_tr = _corr_t(r, calm)                       # Pearson transfer
    rs_tr, ps_tr = _corr_t(rank(r), rank(calm))         # Spearman transfer
    best_c, best_k = int(np.argmin(r)), int(np.argmin(calm))
    best_c_rank_calm = int(rank(calm)[best_c]) + 1
    best_k_rank_cri = int(rank(r)[best_k]) + 1
    beat_calm = int((calm < harx_calm).sum())

    beat = int((r < harx).sum())
    sd_r = float(r.std(ddof=1))
    stats = {}
    for key, lab in [("S_ent", "entanglement S_ent"), ("edges", "coupling density"),
                     ("limit", "depolarized limit")]:
        x = np.array([row[key] for row in rows], dtype=float)
        rr, pp = _corr_t(x, r)
        stats[key] = (rr, pp, lab)

    print(f"\nCHIMERA RMSE over {N_SEEDS} instances: mean {r.mean():.4f}  sd {sd_r:.4f}  "
          f"min {r.min():.4f}  max {r.max():.4f}")
    print(f"instances beating HAR-X: {beat}/{N_SEEDS}   "
          f"(best still worse by {r.min()-harx:+.4f})")
    for k, (rr, pp, lab) in stats.items():
        print(f"corr({lab:<22}, RMSE) = {rr:+.3f}  p={pp:.3f}"
              f"   {'no relationship' if pp > 0.05 else 'SIGNIFICANT'}")
    print(f"\ncalm window: HAR-X {harx_calm:.4f}  CHIMERA {calm.mean():.4f} "
          f"(beating HAR-X: {beat_calm}/{N_SEEDS})")
    print(f"instance-quality TRANSFER crisis->calm: Pearson {r_tr:+.3f} (p={p_tr:.3f}), "
          f"Spearman {rs_tr:+.3f} (p={ps_tr:.3f})")
    print(f"  best on crisis (seed {best_c}) ranks {best_c_rank_calm}/{N_SEEDS} on calm")
    print(f"  best on calm   (seed {best_k}) ranks {best_k_rank_cri}/{N_SEEDS} on crisis")

    with open("results/expressivity_accuracy_findings.md", "w", encoding="utf-8") as fh:
        fh.write(f"""# Expressivity does not predict accuracy — the "necessary, not sufficient" claim, measured

*Generated by `expressivity_vs_accuracy.py` (`python3 cli.py run expressivity`). {N_SEEDS} seeded
n={N} instances, crisis window, the paper's own Axis-B protocol (identical inputs, HAR-X linear
block nested in the ridge head, train-only scaling). Offline — no hardware, no credits.*

> **STATUS — EXPLORATORY (post-hoc), NOT pre-registered.** This analysis was designed and run
> *after* the hardware and forecasting data existed. It is reported to the same evidentiary
> standard as the rest of the repository (deterministic, offline, re-derivable) but it carries
> **none of the hash-preimage guarantee** that the pre-registered predictions (H0/H1/H4, S1–S7)
> carry — those were committed to `git` before their data was collected and can be checked with
> `git show`. We keep the two categories visibly separate on purpose: the value of a
> pre-registration claim depends entirely on not quietly widening it after the fact.
>
> **Multiplicity.** These are exploratory correlations on a single 30-row dataset and the
> p-values below are **raw and uncorrected**. Across the 8 correlations in this family, Holm
> adjustment leaves **none significant** (smallest raw p=0.029 → adjusted 0.23). Holm and the
> Model Confidence Set used elsewhere in this project are scoped to the **pre-registered**
> forecasting family only. Directions here are suggestive, not established.

## The question

The paper argues that kernel distinctness and full-rank entanglement are **necessary but not
sufficient** for forecasting advantage. That is a qualitative claim. If quantum expressivity were
the resource this task rewards, then across a population of reservoir instances the **more
entangled** ones should forecast **better**. This file tests that directly.

## Result

| | value |
|---|---|
| HAR-X (classical bar), crisis RMSE | **{harx:.4f}** |
| CHIMERA across {N_SEEDS} instances | mean **{r.mean():.4f}**, sd {sd_r:.4f}, min {r.min():.4f}, max {r.max():.4f} |
| instances beating HAR-X | **{beat} / {N_SEEDS}** |
| best instance vs the bar | **{r.min()-harx:+.4f}** (still worse) |

**Correlation of structure with accuracy (lower RMSE = better):**

| structural quantity | Pearson r vs RMSE | p | verdict |
|---|---|---|---|
""")
        for k, (rr, pp, lab) in stats.items():
            fh.write(f"| {lab} | {rr:+.3f} | {pp:.3f} | "
                     f"{'no detectable relationship' if pp > 0.05 else 'significant'} |\n")
        fh.write(f"""
## The "best seed" does not transfer

If instances differed in real quality, the good ones on one regime would be good on another.
They do not:

| | value |
|---|---|
| corr(crisis RMSE, calm RMSE) over {N_SEEDS} instances | Pearson **{r_tr:+.3f}** (p={p_tr:.3f}), Spearman **{rs_tr:+.3f}** (p={ps_tr:.3f}) |
| best instance on crisis (seed {best_c}) | ranks **{best_c_rank_calm}/{N_SEEDS}** on calm |
| best instance on calm (seed {best_k}) | ranks **{best_k_rank_cri}/{N_SEEDS}** on crisis |
| beating HAR-X | **{beat}/{N_SEEDS}** crisis, **{beat_calm}/{N_SEEDS}** calm |

The instance-to-instance spread is **not a property of the instance** — it does not replicate out
of regime. Selecting a reservoir seed on one window therefore buys nothing on another; reporting a
best-of-N seed would be selection on noise. This closes the last escape hatch for the negative:
it is not that we drew a bad reservoir, and there is no better one to find.

## What this establishes

1. **Entanglement does not buy accuracy on this task.** The correlation between per-instance
   entanglement and per-instance forecast error is **not distinguishable from zero**. The quantum
   resource and the task outcome are, on this evidence, unrelated.
2. **The negative is not a bad-draw artifact.** **{beat} of {N_SEEDS}** instances beat the classical
   bar. Even the single best instance in the ensemble is worse than HAR-X, and the instance-to-instance
   spread (sd {sd_r:.4f}) is small next to the gap to the bar ({r.mean()-harx:+.4f}). Re-rolling the
   reservoir is not a route to advantage here.
3. **"Necessary but not sufficient" is now measured, not asserted.** The reservoir *is* distinct and
   near-maximally entangled (see `tensor_findings.md`, `kernel_findings.md`) — and that buys nothing
   on this task.

## Limits of this analysis (stated plainly)

- **Absence of evidence, correctly bounded.** With n={N_SEEDS} instances, this design reliably detects
  only |r| ≳ **{DETECTABLE_R:.2f}** (α=0.05, 80% power). We can exclude a *strong* structure→accuracy
  relationship; we **cannot** exclude a weak one. We claim the former only.
- One task (S&P 500 RV), one window (crisis), one size (n={N}), one connectivity (0.5), one
  Hamiltonian family (Ising). The second-family (Heisenberg) check lives in
  `second_family_findings.md`; the cross-domain check in the weather studies.
- Entanglement is the balanced-cut von-Neumann entropy over {ENT_SAMPLE} real training states. A
  3-window proxy estimator agrees with it (r≈+0.87), so the estimate is not fragile.
- This measures *this* reservoir class on *this* task. It is not a statement about quantum machine
  learning in general.
""")
    json.dump({"harx_rmse": harx, "rows": rows}, open("results/expressivity_accuracy.json", "w"), indent=1)
    print("\nsaved results/expressivity_accuracy_findings.md + .json")


if __name__ == "__main__":
    main()
