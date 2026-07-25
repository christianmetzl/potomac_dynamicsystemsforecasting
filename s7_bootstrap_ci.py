"""
s7_bootstrap_ci.py — shot-noise bootstrap for the three S7 cross-seed campaigns.

Why this exists (and a correction). An earlier version of `qpu_hardware_findings.md` stated that
S7 "stores chains, not raw counts, so no multinomial bootstrap is computed here". **That was
wrong.** `results/qpu_ckpt_hw_s7_*.json` contain full per-window raw counts (3 windows x 4,000
shots), the identical schema `qpu_bootstrap_ci.py` consumes for the other nine campaigns. The only
reason S7 was not in that table is that `qpu_bootstrap_ci.campaign_ci()` hardcodes the seed-0
reservoir instance; S7's seed-1 arms need seed-aware exact features. This script supplies them.

We report the result even though part of it is unflattering, because the result is unflattering in
a specific and important way: under the STRICTER instance-matched comparator that we ourselves
introduced in the S7 self-correction, the n=8 margin sits close enough to the pre-registered +-0.02
"unresolved" band that shot noise alone puts it inside the band in roughly a third of draws.

What the numbers show:
  * Under the PRE-REGISTERED comparator (seed-0 limits, as committed at 89cce5f before launch) the
    verdict is fully shot-noise robust: P(inside the band) = 0.000 for both seed-1 arms.
  * Under the stricter instance-matched comparator, seed-1 n=10 stays robust (P ~ 0.005) but
    seed-1 n=8 does NOT (P ~ 0.32). The band test alone therefore does not carry the n=8 arm.
  * The decisive contrast does not depend on any limit: seed-1 n=8 (0.1594) vs the same-session
    seed-0 anchor (0.2284) is a raw-vs-raw gap of 0.069 at fixed size on one chip in one session,
    many sigma of shot noise. That is what carries "instance-dependent, not size-driven".

Offline; reads only committed counts. Regenerate: python3 s7_bootstrap_ci.py
(or: python3 cli.py run s7_bootstrap)
"""
import json

import numpy as np

from qpu_bootstrap_ci import probs_from_counts, features_from_probs
from qbraid_submit import engine_features, real_rv_windows

B = 20000
SEED = 20260725
BAND = 0.02                      # the pre-registered "unresolved" half-width

# (checkpoint tag, n, reservoir seed, pre-registered limit, instance-matched limit, label)
CAMPAIGNS = [
    ("hw_s7_garnet_seed0_n8",  8, 0, 0.1958, 0.1958, "seed-0 n=8 (same-session re-anchor)"),
    ("hw_s7_garnet_seed1_n8",  8, 1, 0.1958, 0.1806, "seed-1 n=8 (independent instance)"),
    ("hw_s7_garnet_seed1_n10", 10, 1, 0.1790, 0.1693, "seed-1 n=10"),
]


def campaign(tag, n, seed, rng):
    ck = json.load(open(f"results/qpu_ckpt_{tag}.json"))
    wins = real_rv_windows(n, k=3)
    F_exact = np.array([engine_features(n, seed)(w) for w in wins])
    p_emp, shots = [], []
    for i in range(3):
        c = ck["jobs"][f"w{i}_s1"]["counts"]
        p_emp.append(probs_from_counts(c, n))
        shots.append(int(sum(c.values())))
    raw = float(np.mean(np.abs(np.array([features_from_probs(p, n) for p in p_emp]) - F_exact)))
    errs = np.empty(B)
    for b in range(B):
        Fb = [features_from_probs(rng.multinomial(shots[i], p_emp[i]) / shots[i], n)
              for i in range(3)]
        errs[b] = np.mean(np.abs(np.array(Fb) - F_exact))
    return raw, errs, shots[0], float(np.mean(np.abs(F_exact)))


def main():
    rng = np.random.default_rng(SEED)
    res = {}
    print(f"S7 shot-noise bootstrap (B={B:,}, multinomial from committed counts)\n")
    print(f"{'campaign':<36}{'raw':>8}{'95% CI':>20}{'sd':>8}")
    for tag, n, seed, lim_pre, lim_inst, lab in CAMPAIGNS:
        raw, errs, shots, lim_check = campaign(tag, n, seed, rng)
        lo, hi = np.percentile(errs, [2.5, 97.5])
        res[tag] = dict(n=n, seed=seed, raw=raw, lo=float(lo), hi=float(hi),
                        sd=float(errs.std()), shots=shots,
                        limit_prereg=lim_pre, limit_instance=lim_inst,
                        limit_recomputed=lim_check, errs_mean=float(errs.mean()),
                        p_inside_band_prereg=float(np.mean(np.abs(errs - lim_pre) < BAND)),
                        p_inside_band_instance=float(np.mean(np.abs(errs - lim_inst) < BAND)))
        print(f"{lab:<36}{raw:8.4f}  [{lo:.4f}, {hi:.4f}]  {errs.std():7.5f}")

    a, b = res["hw_s7_garnet_seed1_n8"], res["hw_s7_garnet_seed0_n8"]
    gap = b["raw"] - a["raw"]
    gap_sd = float(np.hypot(a["sd"], b["sd"]))
    gap_sigma = gap / gap_sd

    print(f"\nBand test vs the +-{BAND} pre-registered unresolved band:")
    print(f"{'campaign':<36}{'P(inside) prereg':>18}{'P(inside) instance':>20}")
    for tag, n, seed, lp, li, lab in CAMPAIGNS[1:]:
        r = res[tag]
        print(f"{lab:<36}{r['p_inside_band_prereg']:18.3f}{r['p_inside_band_instance']:20.3f}")
    print(f"\nLimit-independent contrast: seed-1 n=8 {a['raw']:.4f} vs same-session seed-0 "
          f"{b['raw']:.4f}\n  gap {gap:.4f} +- {gap_sd:.5f} = {gap_sigma:.0f} sigma of shot noise")

    with open("results/s7_bootstrap_ci.md", "w", encoding="utf-8") as fh:
        fh.write(f"""# S7 shot-noise bootstrap — including the part that does not flatter us

*Generated by `s7_bootstrap_ci.py` (`python3 cli.py run s7_bootstrap`). Multinomial bootstrap,
B={B:,}, from the committed per-window counts in `results/qpu_ckpt_hw_s7_*.json`. Offline.*

> **Correction.** An earlier version of `qpu_hardware_findings.md` said S7 "stores chains, not raw
> counts, so no multinomial bootstrap is computed here." **That was false** — the checkpoints hold
> full counts (3 windows x 4,000 shots), the same schema the nine-campaign table uses. The reason
> S7 was absent is mundane: `qpu_bootstrap_ci.campaign_ci()` hardcodes the seed-0 instance, and the
> seed-1 arms need seed-aware exact features. We wrote this script, ran it, and report the outcome
> below including the part that weakens our own claim.

## Bootstrap

| campaign | n | seed | raw | 95% shot CI | bootstrap sd |
|---|---|---|---|---|---|
""")
        for tag, n, seed, lp, li, lab in CAMPAIGNS:
            r = res[tag]
            fh.write(f"| {lab} | {n} | {seed} | **{r['raw']:.4f}** | "
                     f"[{r['lo']:.4f}, {r['hi']:.4f}] | {r['sd']:.5f} |\n")
        s1 = res["hw_s7_garnet_seed1_n8"]; s2 = res["hw_s7_garnet_seed1_n10"]
        fh.write(f"""
## The band test, under both comparators

The committed decision rule declares a point **unresolved** if its raw error sits within
**±{BAND}** of its limit. Probability that shot noise alone puts the margin inside that band:

| campaign | pre-registered comparator (seed-0 limits, as committed) | stricter instance-matched comparator |
|---|---|---|
| seed-1 n=8 | margin {s1['raw']-s1['limit_prereg']:+.4f} — **P(inside) = {s1['p_inside_band_prereg']:.3f}** | margin {s1['raw']-s1['limit_instance']:+.4f} — **P(inside) = {s1['p_inside_band_instance']:.3f}** |
| seed-1 n=10 | margin {s2['raw']-s2['limit_prereg']:+.4f} — **P(inside) = {s2['p_inside_band_prereg']:.3f}** | margin {s2['raw']-s2['limit_instance']:+.4f} — **P(inside) = {s2['p_inside_band_instance']:.3f}** |

**Read this honestly.** Under the **pre-registered** comparator — the rule as committed at
`89cce5f` before launch — both seed-1 verdicts are fully shot-noise robust (P = 0.000). Under the
**stricter instance-matched** comparator we introduced ourselves in the S7 self-correction, the
n=10 arm stays robust ({s2['p_inside_band_instance']:.3f}) but the **n=8 arm does not**:
about **{s1['p_inside_band_instance']*100:.0f}% of shot-noise realizations would return
"unresolved" rather than "signal-bearing" under the committed rule. **The band test alone does not
carry the n=8 arm under our own stricter comparator, and we say so.**

## What does carry the claim

The decisive comparison needs **no limit at all**: on one chip, in one session, at fixed size,

- seed-1 n=8 raw **{s1['raw']:.4f}**
- same-session seed-0 n=8 anchor raw **{res['hw_s7_garnet_seed0_n8']['raw']:.4f}**
- gap **{gap:.4f} ± {gap_sd:.5f} = {gap_sigma:.0f}σ** of shot noise

Day-drift is excluded (same session) and size is excluded (fixed n=8). Two instances of the same
circuit family at the same size on the same chip land on opposite sides of any reasonable
threshold. That is what establishes **instance dependence**, and it is unaffected by which
comparator one prefers. The n=10 arm independently reproduces off the seed-0 instance under both
comparators.

## Net effect on the S7 conclusion

**H-INSTANCE remains refuted**, on: (a) the pre-registered rule, robustly (P=0.000); (b) the
limit-independent {gap_sigma:.0f}σ raw-vs-raw contrast; and (c) the n=10 arm under both
comparators. What we withdraw is any suggestion that the **n=8 band test** is robust under the
stricter comparator — it is not, and a reviewer who noticed that before we did would have been
right to press on it.
""")
        json.dump(res, open("results/s7_bootstrap_ci.json", "w"), indent=1)
    print("\nsaved results/s7_bootstrap_ci.md + .json")


if __name__ == "__main__":
    main()
