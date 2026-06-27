"""
build_massive_etf_panel.py  [V2 helper] — convert the Massive.com ETF daily-RV CSV
(produced by the n8n pipeline) into the npz panel v2_cross_asset.py consumes.

PROVENANCE (honest, important):
  The CSV data/massive_etf_daily_panel.csv was fetched by an n8n workflow
  ("CHIMERA V2 — Massive Multi-Asset Daily RV", id 5b6nLfOYIvHR888Q) that calls the
  Massive.com aggregates API (Polygon-compatible) for 10 liquid ETFs and computes a daily
  Garman-Klass log realized-variance per asset. n8n runs on its own infrastructure, which
  CAN reach Massive even though this sandbox cannot.

  TIER LIMITS discovered by direct probe (reported, not hidden):
    * 5-minute intraday history -> 403 NOT_AUTHORIZED ("plan doesn't include this timeframe").
      => true 5-min realized variance is NOT available on this plan.
    * daily history -> only ~5 years returned (2021-06-28 .. 2026-06-01), even when 2004 was
      requested. => NO 2020 COVID, NO 2008 GFC on this plan.

  So this panel is, honestly, a DAILY GARMAN-KLASS proxy over a RECENT, crisis-light window.
  It is NOT a quality upgrade over the Oxford-Man panel (true 5-min RV, GFC-inclusive) or
  V1's .SPX (2000-2020, GFC+COVID). Its value is a THIRD, INDEPENDENT cross-check on a
  different universe — cross-ASSET-CLASS ETFs (equity / bonds / gold / sectors), recent regime.

OUTPUT: v2_research/cross_asset_panel_massive_etf.npz (logrv [T,K], dates [T], cols [K]).
Then: python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_massive_etf.npz \
            --targets SPY TLT GLD --train-end 2024-06-01
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(os.path.dirname(HERE), "data", "massive_etf_daily_panel.csv")
OUT = os.path.join(HERE, "cross_asset_panel_massive_etf.npz")


def main():
    if not os.path.exists(CSV):
        raise SystemExit(f"missing {CSV} (produced by the n8n Massive workflow; commit it).")
    df = pd.read_csv(CSV, parse_dates=["date"]).set_index("date").sort_index()
    df = df.dropna()
    np.savez_compressed(OUT, logrv=df.values,
                        dates=df.index.values.astype("datetime64[ns]"),
                        cols=np.array(list(df.columns)))
    print(f"saved {OUT}")
    print(f"  {df.shape[0]} days x {df.shape[1]} assets, "
          f"{df.index.min().date()}..{df.index.max().date()}, measure=daily Garman-Klass")
    print("Now:  python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_massive_etf.npz "
          "--targets SPY TLT GLD --train-end 2024-06-01")


if __name__ == "__main__":
    main()
