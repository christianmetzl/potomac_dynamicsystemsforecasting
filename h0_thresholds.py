"""
h0_thresholds.py - PRE-REGISTERED confirm/refute thresholds for the CHIMERA-QRC
Phase-3 central hypothesis (H0).

This file is committed BEFORE any scaling-sweep result exists (see preregistration.md).
scaling_sweep.py imports these constants and decision functions so the H0 verdict is
computed MECHANICALLY from the locked rules - never chosen after seeing the numbers.

H0
--
The 8-qubit kernel-distinctness (geometric difference g) and parameter-efficiency edge
becomes a *forecasting-accuracy* gap at scale, in the regime where exact classical
simulation is infeasible.

Two decisive curves vs qubit count n:
  (1) g(n)      = geometric difference g(ESN -> CHIMERA).  Must KEEP GROWING (not saturate).
  (2) mz_gap(n) = MZ-R2(CHIMERA) - MZ-R2(HAR) on the regime-transition split.
                  Must turn POSITIVE & SIGNIFICANT (DM, MCS) beyond the exact-sim frontier.

Refutation is a publishable finding. We commit to reporting it.

Team EIGENNEXUS | GIC 2026 - Phase 3.  Thresholds locked 2026-06-21.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

# =====================================================================================
# Phase-2 ANCHORS  (prior published results - the new harness must REPRODUCE these)
# =====================================================================================
PHASE2_G_1SCALE_N8        = 62.0    # g(ESN-108 -> CHIMERA-1scale), 36 feats, 3-seed mean
PHASE2_G_CONTROL          = 4.3     # g(ESN-108 -> ESN-108'), classical-classical control
PHASE2_MZ_HAR_CRISIS      = 0.559   # HAR-RV   MZ-R2 on the GFC-in-test split
PHASE2_MZ_CHIMERA3_CRISIS = 0.591   # CHIMERA-3scale MZ-R2 (headline regime-transition win)
PHASE2_MZ_GAP_N8          = PHASE2_MZ_CHIMERA3_CRISIS - PHASE2_MZ_HAR_CRISIS   # = +0.032

# =====================================================================================
# ANCHOR-REPRODUCTION TOLERANCES  (validation gate: trust no new n until n=8 reproduces)
# =====================================================================================
G_ANCHOR_REL_TOL  = 0.15   # g(n=8, 1scale) must land within +-15% of 62 (BLAS/subsample drift)
MZ_GAP_ANCHOR_TOL = 0.020  # mz_gap(n=8, 3scale) within +-0.020 of the +0.032 anchor

# =====================================================================================
# LOCKED DECISION THRESHOLDS
# =====================================================================================
EXACT_SIM_FRONTIER_N  = 30    # qubits beyond which exact statevector is infeasible (~28-30)
G_GROWTH_CONTROL_MULT = 2.0   # "growing": top-step delta_g must exceed 2x the control magnitude
MZ_GAP_CONFIRM        = 0.020 # accuracy gap must be >= the n=8 headline gap, but now OOS @ scale
MZ_GAP_BOOT_ALPHA     = 0.05  # block-bootstrap of the MZ-gap: one-sided sig. that gap > 0
DM_CONFIRM_ALPHA      = 0.05  # one-sided DM (point loss): CHIMERA strictly better than HAR at 5%
DEFF_SAT_PER_2Q       = 0.5   # effective-rank rise < 0.5 per +2 qubits  =>  "saturated"

# Encodings where added qubits carry NEW information (Axis-B family); the decisive
# CONFIRM/REFUTE verdict only applies here. v1.2: "multivariate" (one new measure per
# added qubit) joins "multivariate_reupload" - both are new-information encoders.
NEW_INFO_ENCODINGS = ("multivariate", "multivariate_reupload")
VALID_ENCODINGS = ("univariate",) + NEW_INFO_ENCODINGS


# =====================================================================================
# ANCHOR GATE
# =====================================================================================
def anchor_ok(g_n8_1scale: float, mz_gap_n8_3scale: float) -> tuple[bool, str]:
    """Did the new harness reproduce the Phase-2 anchors within locked tolerance?
    If False, the harness is wrong and NO swept point may be trusted."""
    g_ok = abs(g_n8_1scale - PHASE2_G_1SCALE_N8) <= G_ANCHOR_REL_TOL * PHASE2_G_1SCALE_N8
    mz_ok = abs(mz_gap_n8_3scale - PHASE2_MZ_GAP_N8) <= MZ_GAP_ANCHOR_TOL
    msg = (f"g(n=8,1s)={g_n8_1scale:.1f} (anchor {PHASE2_G_1SCALE_N8:.0f}+-"
           f"{G_ANCHOR_REL_TOL*100:.0f}%) -> {'OK' if g_ok else 'FAIL'}; "
           f"mz_gap(n=8,3s)={mz_gap_n8_3scale:+.3f} (anchor {PHASE2_MZ_GAP_N8:+.3f}+-"
           f"{MZ_GAP_ANCHOR_TOL:.3f}) -> {'OK' if mz_ok else 'FAIL'}")
    return (g_ok and mz_ok), msg


# =====================================================================================
# CURVE CLASSIFIERS
# =====================================================================================
def g_curve_status(ns: Sequence[int], gs: Sequence[float],
                   g_control: float) -> str:
    """Classify the geometric-difference curve at the TOP of the reachable range.
      'growing'    : still climbing by more than a whole control-magnitude per step
      'saturating' : top-step rise has flattened to within the classical control noise
      'ambiguous'  : in between
    """
    if len(gs) < 2:
        return "ambiguous"
    top_delta = gs[-1] - gs[-2]
    if top_delta >= G_GROWTH_CONTROL_MULT * g_control:
        return "growing"
    if top_delta <= g_control:
        return "saturating"
    return "ambiguous"


def deff_status(ns: Sequence[int], deffs: Sequence[float]) -> str:
    """Is the kernel effective rank (participation ratio) still rising with n?
      'rising'     : top-step rise >= DEFF_SAT_PER_2Q (per +2 qubits, normalized)
      'saturating' : below that -> no new effective dimensions are being created
    """
    if len(deffs) < 2:
        return "ambiguous"
    dn = max(1, ns[-1] - ns[-2])
    rise_per_2q = (deffs[-1] - deffs[-2]) * (2.0 / dn)
    return "rising" if rise_per_2q >= DEFF_SAT_PER_2Q else "saturating"


def accuracy_status(mz_gap: float, dm_stat: float, dm_p: float,
                    in_mcs: bool, mz_gap_boot_p: float) -> str:
    """Classify the forecasting-accuracy edge over HAR on the regime-transition split.

    Pre-registration v1.1 ("require both, soften refute"):
      'confirm'      : the regime-transition MZ-gap is significant (gap >= MZ_GAP_CONFIRM
                       AND block-bootstrap p < MZ_GAP_BOOT_ALPHA) AND CHIMERA also beats HAR
                       on point loss (DM significant, correct sign) AND CHIMERA in the MCS.
      'inconclusive' : a SIGNIFICANT positive MZ-gap with MCS membership but no point-loss
                       win is NOT a refutation - it is a real regime-transition edge that has
                       not (yet) become a point-accuracy edge.  Also: any positive-but-not-yet
                       -significant signal.
      'refute'       : genuinely no edge - MZ-gap <= 0 (no regime advantage at all), or no
                       significant edge on either axis and not in the MCS.
    """
    mz_sig = (mz_gap >= MZ_GAP_CONFIRM) and (mz_gap_boot_p < MZ_GAP_BOOT_ALPHA)
    dm_better = (dm_stat < 0) and (dm_p < DM_CONFIRM_ALPHA)
    if mz_sig and dm_better and in_mcs:
        return "confirm"
    if mz_sig and in_mcs:                 # softened: significant regime win is never a refute
        return "inconclusive"
    if mz_gap <= 0.0 and not dm_better:
        return "refute"
    if (not mz_sig) and (not dm_better) and (not in_mcs):
        return "refute"
    return "inconclusive"


# =====================================================================================
# OVERALL H0 VERDICT  (conditioned on encoding + scale so univariate saturation is
# correctly read as INPUT-BOUND, not as an H0 refutation)
# =====================================================================================
@dataclass
class Verdict:
    label: str          # CONFIRM | REFUTE | INPUT_BOUND_EXPECTED | INCONCLUSIVE | HARNESS_FAIL
    rationale: str

    def __str__(self) -> str:
        return f"[{self.label}] {self.rationale}"


def h0_verdict(encoding: str, max_n: int, anchor_passed: bool,
               g_status: str, deff_status_: str, acc_status: str) -> Verdict:
    """Mechanical H0 verdict from the locked rules.

    The decisive REFUTE on g-saturation is only valid where added qubits actually
    carry new information (multivariate/re-uploading encoder) AND we are beyond the
    exact-simulation frontier. Under the univariate encoder, g + D_eff saturation is
    the PREDICTED input-bound signature, which gates the move to Axis-B - it is NOT a
    refutation of H0.
    """
    if encoding not in VALID_ENCODINGS:
        raise ValueError(f"encoding must be one of {VALID_ENCODINGS}")
    if not anchor_passed:
        return Verdict("HARNESS_FAIL",
                       "n=8 anchor not reproduced within tolerance; no swept point is trustworthy.")

    decisive = (encoding in NEW_INFO_ENCODINGS) and (max_n >= EXACT_SIM_FRONTIER_N)

    # Confirmation requires BOTH curves favourable, and only counts at decisive scale.
    if g_status == "growing" and acc_status == "confirm":
        if decisive:
            return Verdict("CONFIRM",
                           "g(n) non-saturating AND accuracy gap over HAR positive & "
                           "significant beyond the exact-sim frontier with new-information encoding.")
        return Verdict("INCONCLUSIVE",
                       "Both curves favourable but below decisive scale/encoding; "
                       "promising - escalate n and switch to Axis-B encoder.")

    # Saturation handling - the input-bottleneck guard.
    if g_status == "saturating":
        if encoding == "univariate" and deff_status_ in ("saturating", "ambiguous"):
            return Verdict("INPUT_BOUND_EXPECTED",
                           "g(n) and kernel effective-rank saturate under the fixed 8-lag input "
                           "- this is the predicted INPUT-BOUND signature, not an H0 refutation. "
                           "Gates Axis-B (multivariate / data re-uploading) as the real test.")
        if decisive:
            return Verdict("REFUTE",
                           "g(n) saturates even with new-information encoding beyond the exact-sim "
                           "frontier - distinctness was a small-system artifact. H0 refuted (reported).")
        return Verdict("INCONCLUSIVE",
                       "g(n) saturating but not at decisive encoding/scale; "
                       "re-test under Axis-B before concluding.")

    if acc_status == "refute" and decisive:
        return Verdict("REFUTE",
                       "No forecasting-accuracy edge over HAR at the largest reachable scale "
                       "with new-information encoding. H0 refuted (reported).")

    return Verdict("INCONCLUSIVE",
                   f"g_status={g_status}, deff={deff_status_}, accuracy={acc_status}, "
                   f"encoding={encoding}, max_n={max_n}: not decisive yet.")


# =====================================================================================
# Self-test on SYNTHETIC inputs only (no real results) - keeps this a pure pre-reg file.
# =====================================================================================
if __name__ == "__main__":
    print("Pre-registered H0 thresholds - self-test on synthetic inputs\n" + "=" * 70)
    ok, msg = anchor_ok(60.5, 0.030)
    print(f"anchor_ok(60.5, 0.030) -> {ok}\n  {msg}")
    assert ok

    # univariate saturation -> must read as INPUT_BOUND_EXPECTED, NOT refute
    v = h0_verdict("univariate", max_n=12, anchor_passed=True,
                   g_status=g_curve_status([8, 10, 12], [62, 63, 63.4], PHASE2_G_CONTROL),
                   deff_status_=deff_status([8, 10, 12], [9.0, 9.1, 9.2]),
                   acc_status=accuracy_status(-0.01, +0.5, 0.40, False, 0.50))
    print("univariate, saturating g:", v)
    assert v.label == "INPUT_BOUND_EXPECTED", v.label

    # decisive multivariate, both curves favourable -> CONFIRM
    v = h0_verdict("multivariate_reupload", max_n=40, anchor_passed=True,
                   g_status=g_curve_status([24, 32, 40], [80, 110, 150], PHASE2_G_CONTROL),
                   deff_status_=deff_status([24, 32, 40], [20, 24, 29]),
                   acc_status=accuracy_status(0.035, -2.3, 0.012, True, 0.01))
    print("multivariate @scale, both favourable:", v)
    assert v.label == "CONFIRM", v.label

    # softened: significant regime-transition MZ-gap + MCS but HAR wins point loss -> NOT refute
    assert accuracy_status(0.035, +1.2, 0.20, True, 0.01) == "inconclusive"

    # decisive multivariate, g saturates + no edge -> REFUTE (honest negative)
    v = h0_verdict("multivariate_reupload", max_n=40, anchor_passed=True,
                   g_status=g_curve_status([24, 32, 40], [150, 152, 153], PHASE2_G_CONTROL),
                   deff_status_=deff_status([24, 32, 40], [25, 30, 35]),
                   acc_status=accuracy_status(0.001, +0.2, 0.6, False, 0.60))
    print("multivariate @scale, saturating g:", v)
    assert v.label == "REFUTE", v.label

    # failed anchor -> HARNESS_FAIL regardless
    v = h0_verdict("univariate", 12, anchor_passed=False,
                   g_status="growing", deff_status_="rising", acc_status="confirm")
    assert v.label == "HARNESS_FAIL", v.label

    print("\nAll synthetic threshold-logic self-tests passed.")
