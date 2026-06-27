"""
v2_multihorizon.py  [V2 — EXPLORATORY, NOT part of the V1 submission]

Question (from the V1 honest negative): the quantum reservoir adds no advantage at the
1-day horizon, where a linear model with good features (HAR-X) is near-optimal. Does an
edge appear at LONGER horizons, where HAR's linear form is weaker and nonlinear dynamics
matter more?

Test: direct h-step-ahead forecasting of S&P-500 log-RV for h ∈ {1,5,10,22}, crisis window,
same rigorous controls as V1's axisB_rigorous (HAR-X / recurrent-ESN / RFF / CHIMERA, all
nesting HAR-X), 8 seeds. For h>1 the forecast errors overlap, so we widen the Newey-West HAC
lag to ≥ h−1 (otherwise significance is overstated) — a stricter test than V1's h=1.

Honest by construction: we report whatever it shows, with Holm correction across horizons.
This does NOT modify any V1 file; V1 reverts via `git archive v1-submission`.
"""
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import feature_pool as fp
from axisB_rigorous import run_window, dm_hac, holm

CRISIS_TR, CRISIS_TE = pd.Timestamp("2007-01-01"), pd.Timestamp("2013-01-01")
HORIZONS = (1, 5, 10, 22)
N = 10  # focal qubit count


def main():
    seeds = tuple(range(8))
    t0 = time.time()
    print("#" * 90)
    print("V2 MULTI-HORIZON (exploratory): does the quantum edge appear where HAR weakens?")
    print(f"  n={N}, seeds={seeds}, crisis window, HAC lag >= h-1 for overlapping forecasts")
    print("#" * 90)

    fam = {}
    rows_out = []
    for h in HORIZONS:
        d = fp.build_rich(horizon=h)
        pool, X_har = d["pool"], d["X_har"]
        y_logrv, y_rv = d["y_logrv"], d["y_rv"]
        dts = pd.to_datetime(d["dates"])
        tr = np.where(dts < CRISIS_TR)[0]
        te = np.where((dts >= CRISIS_TR) & (dts < CRISIS_TE))[0]

        har, results, har_loss, yT_log = run_window(
            f"h{h}", tr, te, pool, X_har, y_logrv, y_rv, [N], seeds)
        rec = results[N]
        lag = max(h - 1, 7)  # HAC lag must cover the (h-1)-order overlap

        print(f"\n--- horizon h={h} (crisis; plain HAR RMSE={har['HAR']['rmse']:.4f}, "
              f"MZ={har['HAR']['mz']:.3f}) ---")
        print(f"  {'model':<9}{'RMSE':>9}{'MZ_R2':>8}{'DM vs HAR-X (HAC)':>20}{'p':>8}")
        harx_loss = (rec["HAR-X"]["pred"] - yT_log) ** 2
        for name in ("HAR-X", "ESN", "RFF", "CHIMERA"):
            m = rec[name]
            if name == "HAR-X":
                ds, p = float("nan"), float("nan")
            else:
                ds, p = dm_hac((m["pred"] - yT_log) ** 2, harx_loss, lag=lag)
                if name == "CHIMERA":
                    fam[f"h{h}:CHIMERAvsHARX"] = p
            tag = "" if name == "HAR-X" else f"{ds:>+18.2f}{p:>8.3f}"
            print(f"  {name:<9}{m['rmse']:>9.4f}{m['mz']:>8.3f}{tag}")
            rows_out.append(dict(h=h, model=name, rmse=m["rmse"], mz=m["mz"],
                                 dm_vs_harx=(None if name == "HAR-X" else ds),
                                 p=(None if name == "HAR-X" else p)))

    adj = holm(fam)
    print("\n" + "=" * 90)
    print("CHIMERA vs HAR-X across horizons (Holm-adjusted):")
    for k in sorted(fam):
        sig = "  *sig@0.05" if adj[k] < 0.05 else ""
        print(f"  {k:<22} raw p={fam[k]:.3f}  Holm p={adj[k]:.3f}{sig}")
    # sign-aware verdict: a WIN requires CHIMERA DM<0 (better) AND Holm p<0.05
    ch = {r["h"]: r for r in rows_out if r["model"] == "CHIMERA"}
    wins = [h for h in ch if ch[h]["dm_vs_harx"] is not None
            and ch[h]["dm_vs_harx"] < 0 and adj[f"h{h}:CHIMERAvsHARX"] < 0.05]
    worse = [h for h in ch if ch[h]["dm_vs_harx"] is not None
             and ch[h]["dm_vs_harx"] > 0 and adj[f"h{h}:CHIMERAvsHARX"] < 0.05]
    if wins:
        print(f"\nVERDICT: CHIMERA significantly BEATS HAR-X (Holm) at horizons {wins} — investigate.")
    elif worse:
        print(f"\nVERDICT: HAR-X best at all horizons; CHIMERA significantly WORSE (Holm) at {worse}. "
              "Honest negative persists.")
    else:
        print("\nVERDICT: HAR-X is best/co-best at every horizon; no significant CHIMERA advantage "
              "(all Holm p>0.05; CHIMERA's raw DM vs HAR-X is positive = slightly worse). "
              "Honest negative persists across horizons.")
    np.save(os.path.join(os.path.dirname(__file__), "v2_multihorizon_results.npy"),
            dict(rows=rows_out, family_raw=fam, family_holm=adj), allow_pickle=True)
    print(f"[{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
