"""
preregistration.py - Pre-registered, falsifiable Phase-3 hypotheses and their
confirm/refute thresholds for CHIMERA-QRC.

WHY THIS FILE EXISTS (honesty doctrine)
---------------------------------------
The criteria below are transcribed from the Team EIGENNEXUS Phase-2 submission,
Section 7 ("Phase-3 plan, falsifiable hypothesis, and impact"), and are committed
to version control *before* any Phase-3 scaling experiment is run. Fixing the
thresholds in advance means we cannot move the goalposts after seeing the data.
Every Phase-3 experiment reports its outcome against these criteria - including,
explicitly, negative results.

This module has NO side effects on import (safe to import from experiments). Run
it directly (`python3 preregistration.py`) to print the registered hypotheses.

Source of record: EIGENNEXUS Phase-2 paper (submitted), Section 7, and the
challenge brief's requirement (criterion 6) for concrete, reproducible results.
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np

# ---------------------------------------------------------------------------
# Decision-level constants (fixed in advance)
# ---------------------------------------------------------------------------
DM_ALPHA = 0.05          # Diebold-Mariano significance level for "significant"
SPEARMAN_MIN = 0.0       # g(n) must trend strictly upward => rho_s > this
# "g keeps growing" must clear the classical-classical control band: the increase
# in g across the tested qubit range must exceed the control geometric difference
# (a second ESN seed), i.e. the change must be larger than classical re-seeding noise.
GROWTH_OVER_CONTROL = True


@dataclass(frozen=True)
class Hypothesis:
    key: str
    statement: str   # the paper's own words (verbatim intent)
    confirm: str     # operationalized confirm condition
    refute: str      # operationalized refute condition


# ---------------------------------------------------------------------------
# H0 - the central, falsifiable claim
# ---------------------------------------------------------------------------
H0 = Hypothesis(
    key="H0",
    statement=(
        "The measured parameter-efficiency gap becomes a forecasting-accuracy "
        "gap at scale. Beyond the classical-simulation frontier, H0 is CONFIRMED "
        "if the geometric difference g keeps growing with qubit count AND the "
        "regime-transition Mincer-Zarnowitz gap over HAR turns positive and "
        "significant out-of-sample; REFUTED if g saturates or that gap stays <= 0."
    ),
    confirm=(
        "g(n) trends strictly upward over the tested range (Spearman rho_s > 0) "
        "AND g(n_max) - g(n_min) exceeds the classical-classical control g "
        "AND MZ_R2(CHIMERA, n) - MZ_R2(HAR) > 0 for some n with DM p < 0.05 "
        "in CHIMERA's favour on the crisis/transition window."
    ),
    refute=(
        "g(n) flat or saturating (Spearman rho_s <= 0, or its rise is within the "
        "classical control band) OR the MZ gap over HAR stays <= 0 across the "
        "tested range."
    ),
)

# ---------------------------------------------------------------------------
# H1 - accuracy gap narrows monotonically with scale
# ---------------------------------------------------------------------------
H1 = Hypothesis(
    key="H1",
    statement=(
        "Scale 12 -> 50 -> 128 -> 256 qubits, tracking RMSE/QLIKE vs HAR. "
        "REFUTED if the gap does not narrow monotonically."
    ),
    confirm=(
        "The CHIMERA-minus-HAR RMSE (and QLIKE) gap is non-increasing in n "
        "(monotone narrowing) across the tested range."
    ),
    refute="The gap vs HAR fails to narrow monotonically with n.",
)

# ---------------------------------------------------------------------------
# H4 - effective feature-rank scales with qubits (encoding-density axis)
# ---------------------------------------------------------------------------
H4 = Hypothesis(
    key="H4",
    statement=(
        "Effective feature-rank and encoding-density scaling, with qubits scaled "
        "in lockstep with input richness so added qubits encode NEW information "
        "rather than reprocessing the same eight lags. REFUTED if rank saturates "
        "with qubits."
    ),
    confirm=(
        "Effective dimension D_eff(n) (and numerical rank) of the CHIMERA kernel "
        "increases with n when input richness scales with n (data re-uploading / "
        "multivariate panel)."
    ),
    refute="D_eff(n) / rank saturates as n grows.",
)

# ---------------------------------------------------------------------------
# H2 / H3 - documented here for completeness; adjudicated by later experiments
# ---------------------------------------------------------------------------
H2 = Hypothesis(
    key="H2",
    statement=(
        "Hardware vs noiseless-simulation feature maps at matched size, with "
        "noise and shot-budget sweeps. REFUTED if hardware adds no accuracy and "
        "noise only degrades (never helps)."
    ),
    confirm="At matched size, a noise/shot setting matches or improves on noiseless.",
    refute="Hardware/noise never matches noiseless and only degrades accuracy.",
)

H3 = Hypothesis(
    key="H3",
    statement=(
        "Hard targets - multi-step, crisis-transition and jump RV. REFUTED if "
        "quantum never beats HAR where HAR is weak."
    ),
    confirm="CHIMERA beats HAR on at least one hard-target regime (e.g. transition MZ).",
    refute="CHIMERA never beats HAR on any hard target.",
)

ALL = [H0, H1, H2, H3, H4]


# ---------------------------------------------------------------------------
# Evaluators (pure functions; return structured verdicts)
# ---------------------------------------------------------------------------
def _rankdata(a):
    """Tie-averaged ranks (like scipy.stats.rankdata, 'average'), no SciPy dependency."""
    a = np.asarray(a, float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(1, len(a) + 1)
    # average ranks within tie groups
    i = 0
    sa = a[order]
    while i < len(a):
        j = i
        while j + 1 < len(a) and sa[j + 1] == sa[i]:
            j += 1
        if j > i:
            avg = (ranks[order[i]] + ranks[order[j]]) / 2.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(x, y):
    """Spearman rank correlation (tie-aware) without a SciPy dependency.
    Returns NaN for <3 points or when either variable has zero rank variance
    (e.g. a perfectly flat/saturated curve), so a flat curve never reports rho=1."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3:
        return float("nan")
    rx = _rankdata(x); ry = _rankdata(y)
    rx = rx - rx.mean(); ry = ry - ry.mean()
    denom = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / denom) if denom > 0 else float("nan")


def evaluate_H0(ns, g_quantum, mz_gap, dm_p, control_g):
    """Adjudicate H0 against the pre-registered thresholds.

    ns          : list of qubit counts (sorted ascending)
    g_quantum   : g(ESN(n) || CHIMERA(n)) per n  (distinctness; larger=more distinct)
    mz_gap      : MZ_R2(CHIMERA,n) - MZ_R2(HAR) per n  (crisis window)
    dm_p        : Diebold-Mariano p-value (CHIMERA vs HAR) per n
    control_g   : representative classical-classical control g(ESN||ESN')
    """
    ns = np.asarray(ns, float)
    g = np.asarray(g_quantum, float)
    mzg = np.asarray(mz_gap, float)
    dmp = np.asarray(dm_p, float)

    rho = _spearman(ns, g)
    if len(ns) < 3 or np.isnan(rho):
        return {"hypothesis": "H0", "verdict": "NOT-EVALUABLE",
                "reason": "trend test needs >=3 qubit counts (got %d)" % len(ns)}
    g_rise = float(g[-1] - g[0]) if len(g) else float("nan")
    g_grows = (rho > SPEARMAN_MIN) and (g_rise > control_g if GROWTH_OVER_CONTROL else g_rise > 0)

    pos_sig = [(int(ns[i]), float(mzg[i]), float(dmp[i]))
               for i in range(len(ns)) if mzg[i] > 0 and dmp[i] < DM_ALPHA]
    mz_ok = len(pos_sig) > 0

    if g_grows and mz_ok:
        verdict = "CONFIRMED"
    elif (rho <= SPEARMAN_MIN) or (not mz_ok and np.all(mzg <= 0)):
        verdict = "REFUTED"
    else:
        verdict = "INCONCLUSIVE"

    return {
        "hypothesis": "H0",
        "verdict": verdict,
        "g_spearman_rho": rho,
        "g_rise": g_rise,
        "control_g": float(control_g),
        "g_grows_over_control": bool(g_grows),
        "mz_gap_positive_significant_at": pos_sig,
        "mz_ok": bool(mz_ok),
        "note": ("Input-bottleneck caveat: until the multivariate / data-"
                 "re-uploading encoder (Axis B) lands, qubits beyond the number "
                 "of encoded lags carry NO new input, so g(n) and the MZ gap may "
                 "saturate at n ~ #lags. A flat curve here is expected pre-Axis-B "
                 "and is NOT yet a refutation of H0 at richer encodings."),
    }


def evaluate_H4(ns, d_eff):
    """H4: does effective feature-rank grow with qubits?"""
    ns = np.asarray(ns, float); d = np.asarray(d_eff, float)
    rho = _spearman(ns, d)
    if len(ns) < 3 or np.isnan(rho):
        return {"hypothesis": "H4", "verdict": "NOT-EVALUABLE",
                "reason": "trend test needs >=3 qubit counts (got %d)" % len(ns)}
    grows = rho > SPEARMAN_MIN and d[-1] > d[0]
    return {
        "hypothesis": "H4",
        "verdict": "CONFIRMED" if grows else "REFUTED/SATURATED",
        "d_eff_spearman_rho": rho,
        "d_eff_rise": float(d[-1] - d[0]) if len(d) else float("nan"),
        "note": ("With a FIXED univariate-lag encoder, saturation is expected "
                 "(the input bottleneck). H4 is properly tested only once input "
                 "richness scales with n (Axis B)."),
    }


def evaluate_H1(ns, rmse_gap, qlike_gap=None):
    """H1: do the RMSE/QLIKE gaps over HAR narrow monotonically with n?

    rmse_gap[i] = RMSE(CHIMERA,n_i) - RMSE(HAR)  (smaller/more-negative is better)
    Monotone narrowing => the gap is non-increasing in n.
    """
    g = np.asarray(rmse_gap, float)
    diffs = np.diff(g)
    monotone = bool(np.all(diffs <= 1e-9))
    out = {
        "hypothesis": "H1",
        "verdict": "CONFIRMED" if monotone else "REFUTED",
        "rmse_gap_monotone_narrowing": monotone,
        "rmse_gap": [float(x) for x in g],
    }
    if qlike_gap is not None:
        q = np.asarray(qlike_gap, float)
        out["qlike_gap_monotone_narrowing"] = bool(np.all(np.diff(q) <= 1e-9))
    return out


if __name__ == "__main__":
    print("=" * 78)
    print("CHIMERA-QRC Phase-3 PRE-REGISTRATION  (committed before running)")
    print("Source: EIGENNEXUS Phase-2 submission, Section 7")
    print("=" * 78)
    for h in ALL:
        print(f"\n[{h.key}] {h.statement}")
        print(f"   CONFIRM if: {h.confirm}")
        print(f"   REFUTE  if: {h.refute}")
    print("\nDecision constants:")
    print(f"   DM_ALPHA={DM_ALPHA}  SPEARMAN_MIN={SPEARMAN_MIN}  "
          f"GROWTH_OVER_CONTROL={GROWTH_OVER_CONTROL}")
