"""
v2_cross_asset.py  [V2 — EXPLORATORY, NOT part of the V1 submission]

The highest-value untested lead from the V1 review: a HIGH-DIMENSIONAL, many-interacting-
series setting, where a high-dimensional quantum feature map is most likely to matter.

Question: does the quantum reservoir capture nonlinear CROSS-ASSET volatility spillovers
that a strong LINEAR model using the SAME cross-asset information (HAR-X-cross) cannot?

Data (public): S&P-500 daily OHLCV 2013-2018 (the well-known 'all_stocks_5yr' set, mirrored
at plotly/datasets). We compute a daily Garman-Klass realized-variance proxy per stock from
OHLC, for a cross-sector basket. Honest caveats vs V1's .SPX: (i) daily GK proxy, not 5-min
RV; (ii) 2013-2018 has volatility episodes (Aug-2015, Feb-2018) but no GFC-scale crisis. The
data is fetched once and cached to v2_research/cross_asset_panel.npz for offline reuse.

Setup: forecast each target asset's next-day log-RV from the lag-1 log-RV of the FULL basket
(cross-asset state -> n qubits). Same rigorous controls as V1: HAR-X-cross (cross-asset info
used LINEARLY) is the bar; CHIMERA / recurrent-ESN / RFF all NEST it; HAC-DM, multi-seed,
Holm across targets. We report whatever it shows. No V1 file is modified.
"""
import argparse
import os
import sys
import time
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import scaling_sweep as ss
from vol_fair_benchmark import ridge_readout, rmse, qlike, mz_r2
from volatility_data import har_components
from axisB_rigorous import dm_hac, holm, esn_recurrent_features, rff_features, rbf_gamma

URL = "https://raw.githubusercontent.com/plotly/datasets/master/all_stocks_5yr.csv"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cross_asset_panel.npz")
BASKET = ["AAPL", "MSFT", "JPM", "XOM", "JNJ", "PG", "KO", "WMT", "HD", "CAT"]  # 10, cross-sector
TARGETS = ["AAPL", "JPM", "XOM"]           # tech / financials / energy
N = len(BASKET)                            # 10 qubits (dense-simulable)
SEEDS = (0, 1, 2, 3, 4, 5)
TRAIN_END = pd.Timestamp("2017-01-01")


def _gk_logrv(o, h, l, c):
    """Garman-Klass daily variance proxy -> log."""
    o, h, l, c = map(lambda x: pd.to_numeric(x, errors="coerce"), (o, h, l, c))
    gk = 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    gk = gk.clip(lower=1e-8)
    return np.log(gk)


def build_panel():
    if os.path.exists(CACHE):
        d = np.load(CACHE, allow_pickle=True)
        return pd.DataFrame(d["logrv"], index=pd.to_datetime(d["dates"]),
                            columns=[str(c) for c in d["cols"]])
    print("(cross-asset cache miss -> fetching S&P-500 OHLCV once...)")
    raw = os.path.join(os.path.dirname(CACHE), "_all_stocks_5yr.csv")
    if not os.path.exists(raw):
        r = subprocess.run(["curl", "-sSL", "--max-time", "240", "-o", raw, URL])
        if r.returncode != 0 or not os.path.exists(raw) or os.path.getsize(raw) < 1e6:
            raise RuntimeError("could not download cross-asset data (network restricted).")
    df = pd.read_csv(raw)
    df = df[df["Name"].isin(BASKET)].copy()
    df["date"] = pd.to_datetime(df["date"])
    panel = {}
    for tk, g in df.groupby("Name"):
        g = g.sort_values("date").set_index("date")
        panel[tk] = _gk_logrv(g["open"], g["high"], g["low"], g["close"])
    P = pd.DataFrame(panel).dropna()
    P = P[BASKET]                                  # fixed column order
    np.savez_compressed(CACHE, logrv=P.values, dates=P.index.values.astype("datetime64[ns]"),
                        cols=np.array(BASKET))
    print(f"  cached -> {CACHE}  ({P.shape[0]} days x {P.shape[1]} assets, "
          f"{P.index.min().date()}..{P.index.max().date()})")
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None,
                    help="npz in v2_research/ (e.g. cross_asset_panel_hq.npz from "
                         "fetch_massive_panel.py); default = built-in S&P-500 daily GK 2013-2018")
    ap.add_argument("--train-end", default=None, help="YYYY-MM-DD train/test cutoff")
    ap.add_argument("--targets", nargs="+", default=None)
    args = ap.parse_args()
    t0 = time.time()

    if args.panel:
        dd = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), args.panel),
                     allow_pickle=True)
        P = pd.DataFrame(dd["logrv"], index=pd.to_datetime(dd["dates"]),
                         columns=[str(c) for c in dd["cols"]])
        src = f"external panel {args.panel}"
    else:
        P = build_panel()
        src = "built-in S&P-500 daily Garman-Klass 2013-2018"

    # locals shadow the module defaults so the body below is panel-agnostic
    BASKET = list(P.columns)
    N = len(BASKET)
    TARGETS = (args.targets
               or [t for t in ("AAPL", "JPM", "XOM", "SPY", "QQQ", "TLT") if t in BASKET]
               or BASKET[:3])
    if args.train_end:
        TRAIN_END = pd.Timestamp(args.train_end)
    else:
        TRAIN_END = (pd.Timestamp("2019-01-01") if P.index.max() > pd.Timestamp("2019-06-01")
                     else pd.Timestamp("2017-01-01"))
    SEEDS = (0, 1, 2, 3, 4, 5)
    dates = P.index
    # dense statevector engine up to 12 qubits; sparse-exact backend beyond (to ~16)
    if N <= 12:
        chimera_fn = lambda Q, sd: ss.chimera_features_n(Q, N, (2.0,), sd)
    else:
        from tensor_backend import chimera_features_sparse
        chimera_fn = lambda Q, sd: chimera_features_sparse(Q, N, 2.0, sd)

    print("#" * 92)
    print("V2 CROSS-ASSET (exploratory): quantum nonlinear spillovers vs linear HAR-X-cross")
    print(f"  source={src}")
    print(f"  basket={BASKET}  n={N} qubits  targets={TARGETS}  seeds={SEEDS}")
    print(f"  panel {P.shape[0]} days {dates.min().date()}..{dates.max().date()}  "
          f"train<{TRAIN_END.date()}")
    print("#" * 92)

    # cross-asset predictor = lag-1 log-RV of every basket asset (the spillover state)
    X_all = P.shift(1)                              # info at t-1
    tr_mask = dates < TRAIN_END

    fam = {}
    rows = []
    for tgt in TARGETS:
        rv_t = np.exp(P[tgt])                       # target RV level
        y_log = P[tgt]
        har = np.log(har_components(rv_t))          # daily/weekly/monthly HAR of target
        data = pd.concat([X_all.add_prefix("x_"), har.add_prefix("har_"),
                          y_log.rename("y")], axis=1).dropna()
        dts = data.index
        tr = np.where(dts < TRAIN_END)[0]
        te = np.where(dts >= TRAIN_END)[0]
        Xc = data[[f"x_{a}" for a in BASKET]].values     # cross-asset lag-1 log-RV (raw)
        Xhar = data[["har_rv_d", "har_rv_w", "har_rv_m"]].values
        yl = data["y"].values
        yrv = np.exp(yl)
        yT = yl[te]; yTrv = yrv[te]

        # scale cross-asset input to [0,1] on TRAIN only (for encoders)
        lo, hi = Xc[tr].min(0), Xc[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
        Xc_s = np.clip((Xc - lo) / rng, 0, 1)
        LINX = np.hstack([Xc, Xhar])                # HAR-X-cross block (cross-asset linear + HAR)

        def met(p):
            v = np.exp(p); return rmse(yT, p), qlike(yTrv, v), mz_r2(yTrv, v)

        # HAR (target only) and HAR-X-cross (strong linear bar)
        har_pred, _ = ridge_readout(Xhar[tr], yl[tr], Xhar[te])
        harx_pred, _ = ridge_readout(LINX[tr], yl[tr], LINX[te])
        harx_loss = (harx_pred - yT) ** 2
        gamma = rbf_gamma(Xc_s[tr])

        per = {"ESN": [], "RFF": [], "CHIMERA": []}
        for sd in SEEDS:
            for nm, F in (("CHIMERA", chimera_fn(Xc_s, sd)),
                          ("ESN", esn_recurrent_features(Xc_s, ss.feat_dim(N), sd)),
                          ("RFF", rff_features(Xc_s, ss.feat_dim(N), sd, gamma))):
                D = np.hstack([F, LINX])
                pr, _ = ridge_readout(D[tr], yl[tr], D[te])
                per[nm].append(pr)

        print(f"\n--- target {tgt}  (plain HAR: RMSE={met(har_pred)[0]:.4f}, MZ={met(har_pred)[2]:.3f}) ---")
        print(f"  {'model':<10}{'RMSE':>9}{'MZ_R2':>8}{'DM vs HAR-X-cross':>20}{'p(HAC)':>9}")
        hr = met(harx_pred)
        print(f"  {'HAR-X-cross':<10}{hr[0]:>9.4f}{hr[2]:>8.3f}")
        for nm in ("ESN", "RFF", "CHIMERA"):
            ens = np.mean(per[nm], axis=0)
            r, q, m = met(ens)
            ds, p = dm_hac((ens - yT) ** 2, harx_loss)
            if nm == "CHIMERA":
                fam[f"{tgt}:CHIMERAvsHARXcross"] = p
            rows.append(dict(target=tgt, model=nm, rmse=r, mz=m, dm=ds, p=p,
                             harx_rmse=hr[0], harx_mz=hr[2]))
            print(f"  {nm:<10}{r:>9.4f}{m:>8.3f}{ds:>+20.2f}{p:>9.3f}")

    adj = holm(fam)
    print("\n" + "=" * 92)
    print("CHIMERA vs HAR-X-cross across targets (Holm-adjusted):")
    ch = {r["target"]: r for r in rows if r["model"] == "CHIMERA"}
    wins = [t for t in ch if ch[t]["dm"] < 0 and adj[f"{t}:CHIMERAvsHARXcross"] < 0.05]
    worse = [t for t in ch if ch[t]["dm"] > 0 and adj[f"{t}:CHIMERAvsHARXcross"] < 0.05]
    for t in sorted(fam):
        print(f"  {t:<28} raw p={fam[t]:.3f}  Holm p={adj[t]:.3f}  "
              f"DM={ch[t.split(':')[0]]['dm']:+.2f}")
    if wins:
        print(f"\nVERDICT: CHIMERA significantly BEATS HAR-X-cross (Holm) for {wins} — a real lead, investigate.")
    elif worse:
        print(f"\nVERDICT: HAR-X-cross best; CHIMERA significantly WORSE (Holm) for {worse}. Honest negative.")
    else:
        print("\nVERDICT: no significant CHIMERA advantage over HAR-X-cross (Holm). "
              "Honest negative persists in the cross-asset setting too.")

    # name the artifact per data source / split so distinct runs don't clobber each other
    if args.panel:
        tag = "_" + os.path.splitext(os.path.basename(args.panel))[0].replace("cross_asset_panel", "").strip("_")
        tag = (tag + f"_tr{TRAIN_END.date()}").replace("__", "_")
    else:
        tag = ""
    np.save(os.path.join(os.path.dirname(__file__), f"v2_cross_asset_results{tag}.npy"),
            dict(rows=rows, family_raw=fam, family_holm=adj, basket=BASKET, targets=TARGETS,
                 source=src, train_end=str(TRAIN_END.date())),
            allow_pickle=True)
    print(f"[{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
