"""
fetch_massive_panel.py  [V2 helper] — build a HIGH-QUALITY multi-asset realized-variance
panel from the Massive.com (Polygon-compatible) API, to verify/strengthen the V2 cross-asset
test with proper data over a long, crisis-inclusive window.

WHY: the first cross-asset run (v2_cross_asset.py) used a *daily Garman-Klass* proxy over a
calm-ish 2013-2018 single-stock window. This fetcher upgrades both axes:
  * window:  default 2004-01-01 .. today  -> includes the 2008 GFC and the 2020 COVID crash
  * assets:  liquid index ETFs across regions/sectors (less noisy than single stocks)
  * measure: 'daily' (Garman-Klass from daily OHLC, 1 call/asset, robust) OR
             'rv5'   (true 5-minute realized variance from intraday bars, heavier)

WHERE TO RUN: anywhere api.polygon.io / massive.com is reachable (your machine, a notebook,
or a Claude web environment whose network policy allows it). In the current sandbox those
hosts are blocked by policy, so this script is provided READY-TO-RUN, not executed here.

REQUIRES:  MASSIVE_API_KEY  (or POLYGON_API_KEY) in the environment.
OUTPUT:    v2_research/cross_asset_panel_hq.npz  — exactly the format v2_cross_asset.py loads
           (logrv [T,K] float, dates [T] datetime64, cols [K] str). Then:
               python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_hq.npz

Usage:
  python3 fetch_massive_panel.py                         # daily GK, 2004->today, default ETFs
  python3 fetch_massive_panel.py --mode rv5 --start 2004-01-01
  python3 fetch_massive_panel.py --tickers SPY QQQ DIA IWM EFA EEM TLT GLD
"""
import argparse
import os
import sys
import time
import json
import urllib.request

import numpy as np
import pandas as pd

BASE = os.environ.get("MASSIVE_API_BASE", "https://api.polygon.io")
KEY = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cross_asset_panel_hq.npz")
# liquid, long-history index/sector ETFs (proxy the global index complex; low single-name noise)
DEFAULT_TICKERS = ["SPY", "QQQ", "DIA", "IWM", "EFA", "EEM", "TLT", "GLD", "XLF", "XLE", "XLK", "VNQ"]


def _get(url, retries=4):
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:                      # transient / rate-limit backoff
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"request failed after {retries} tries: {last}\nURL host: {url.split('?')[0]}")


def _gk_logrv(o, h, l, c):
    gk = 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    return np.log(max(gk, 1e-8))


def fetch_daily(tk, start, end):
    """Daily OHLC -> Garman-Klass log realized variance. One paginated call per ticker."""
    url = (f"{BASE}/v2/aggs/ticker/{tk}/range/1/day/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    rows = {}
    while url:
        j = _get(url)
        for b in j.get("results", []):
            d = pd.Timestamp(b["t"], unit="ms").normalize()
            if all(k in b for k in ("o", "h", "l", "c")) and b["o"] > 0 and b["l"] > 0:
                rows[d] = _gk_logrv(b["o"], b["h"], b["l"], b["c"])
        nxt = j.get("next_url")
        url = (nxt + f"&apiKey={KEY}") if nxt else None
    return pd.Series(rows).sort_index()


def fetch_rv5(tk, start, end):
    """True 5-minute realized variance = sum of squared 5-min log returns per day.
    Heavier (many intraday bars); paginates over the whole range, then groups by day."""
    url = (f"{BASE}/v2/aggs/ticker/{tk}/range/5/minute/{start}/{end}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    closes = []
    while url:
        j = _get(url)
        for b in j.get("results", []):
            closes.append((pd.Timestamp(b["t"], unit="ms"), b["c"]))
        nxt = j.get("next_url")
        url = (nxt + f"&apiKey={KEY}") if nxt else None
    if not closes:
        return pd.Series(dtype=float)
    s = pd.Series({t: c for t, c in closes}).sort_index()
    r = np.log(s).diff()
    rv = (r ** 2).groupby(r.index.normalize()).sum()
    return np.log(rv.clip(lower=1e-10))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    ap.add_argument("--start", default="2004-01-01")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    ap.add_argument("--mode", choices=["daily", "rv5"], default="daily")
    args = ap.parse_args()
    if not KEY:
        sys.exit("ERROR: set MASSIVE_API_KEY (or POLYGON_API_KEY) in the environment first.")

    print(f"Fetching {args.mode} panel: {len(args.tickers)} assets {args.start}..{args.end}")
    fetch = fetch_daily if args.mode == "daily" else fetch_rv5
    panel = {}
    for tk in args.tickers:
        try:
            s = fetch(tk, args.start, args.end)
            if len(s) > 100:
                panel[tk] = s
                print(f"  {tk}: {len(s)} days")
            else:
                print(f"  {tk}: too few rows ({len(s)}) — skipped")
        except Exception as e:
            print(f"  {tk}: FAILED ({e})")
    if len(panel) < 3:
        sys.exit("ERROR: too few assets fetched; check API key / reachability / entitlements.")

    P = pd.DataFrame(panel).dropna()
    cols = list(P.columns)
    np.savez_compressed(OUT, logrv=P.values, dates=P.index.values.astype("datetime64[ns]"),
                        cols=np.array(cols))
    print(f"\nsaved {OUT}\n  {P.shape[0]} days x {P.shape[1]} assets, "
          f"{P.index.min().date()}..{P.index.max().date()}, measure={args.mode}")
    print("Now (where this repo lives):  python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_hq.npz")


if __name__ == "__main__":
    main()
