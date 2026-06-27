"""
fetch_oxfordman_panel.py  [V2 helper] — build a HIGH-QUALITY multi-asset realized-variance
panel from the Oxford-Man Institute Realized Library, to verify/strengthen the V2 cross-asset
test with proper data over a long, CRISIS-INCLUSIVE window.

WHY this upgrades the first cross-asset run (v2_cross_asset.py, which used a *daily*
Garman-Klass proxy over a calm 2013-2018 single-stock window):
  * measure: TRUE 5-minute realized variance (the canonical 'rv5' column), not a daily
             OHLC proxy  -> the actual quantity the volatility literature forecasts.
  * window:  2000-01 .. 2016-09  -> INCLUDES the 2008 Global Financial Crisis (the most
             important volatility regime there is; SPX 5-min RV peaks near ~140% annualised
             around Lehman, Sep-2008).
  * assets:  liquid GLOBAL equity indices across regions (US large/small/tech, Europe, Asia)
             -> a genuine cross-MARKET volatility-spillover setting (Diebold-Yilmaz style),
             far less noisy than single stocks.

DATA SOURCE & PROVENANCE (honest): the Oxford-Man Institute Realized Library was the standard
academic realized-measures dataset (Heber, Lunde, Shephard, Sheppard). The Institute
discontinued hosting it in 2022; its official host is unreachable here. We fetch a widely
mirrored copy of the library spreadsheet (vintage 2016-09-28) from a public GitHub mirror.
Caveat reported openly: this 2016 vintage covers the 2008 GFC but NOT the 2020 COVID crash.
For a COVID-inclusive panel use fetch_massive_panel.py (Polygon/Massive) where that API is
reachable; the *experiment code is identical* — only the data source differs.

OUTPUT:  v2_research/cross_asset_panel_oxfordman.npz  (logrv [T,K] float, dates [T]
         datetime64, cols [K] str) — exactly the format v2_cross_asset.py loads. Then:
             python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_oxfordman.npz \
                     --targets SPX DAX N225 --train-end 2007-01-01

REQUIRES (fetch time only): pandas, numpy, openpyxl. The produced .npz needs none of these
extras to load, so the downstream experiment has no new dependency.

Usage:
  python3 fetch_oxfordman_panel.py                       # default 10-index cross-region basket
  python3 fetch_oxfordman_panel.py --tickers SPX DJI NDX RUT FTSE DAX CAC STOXX50E N225 HSI
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

# public mirror of the Oxford-Man Realized Library spreadsheet (vintage 2016-09-28)
URL = ("https://raw.githubusercontent.com/yools56/Neural-Network-based-HAR-models/master/"
       "OxfordManRealizedVolatilityIndices(20160928).xlsx")
HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "_oxfordman_full.xlsx")
OUT = os.path.join(HERE, "cross_asset_panel_oxfordman.npz")

# Oxford-Man display-name -> clean ticker (all 21 indices in the library)
TICK = {
    'S&P 500 (Live)': 'SPX', 'FTSE 100 (Live)': 'FTSE', 'Nikkei 225 (Live)': 'N225',
    'DAX (Live)': 'DAX', 'Russel 2000 (Live)': 'RUT', 'All Ordinaries (Live)': 'AORD',
    'DJIA  (Live)': 'DJI', 'Nasdaq 100 (Live)': 'NDX', 'CAC 40 (Live)': 'CAC',
    'Hang Seng (Live)': 'HSI', 'KOSPI Composite Index (Live)': 'KOSPI',
    'AEX Index (Live)': 'AEX', 'Swiss Market Index (Live)': 'SSMI', 'IBEX 35 (Live)': 'IBEX',
    'S&P CNX Nifty (Live)': 'NIFTY', 'IPC Mexico (Live)': 'MXX', 'Bovespa Index (Live)': 'BVSP',
    'S&P/TSX Composite Index (Live)': 'GSPTSE', 'Euro STOXX 50 (Live)': 'STOXX50E',
    'FT Straits Times Index': 'STI', 'FTSE MIB (Live)': 'FTSEMIB',
}
RV5 = "Realized Variance (5-minute)"   # the canonical 5-min realized-variance measure
# default basket: 10 liquid cross-region indices (dense-statevector-simulable at 10 qubits)
DEFAULT = ['SPX', 'DJI', 'NDX', 'RUT', 'FTSE', 'DAX', 'CAC', 'STOXX50E', 'N225', 'HSI']


def _download():
    if os.path.exists(XLSX) and os.path.getsize(XLSX) > 1e7:
        return
    import subprocess
    print(f"(downloading Oxford-Man Realized Library once -> {XLSX})")
    r = subprocess.run(["curl", "-sSL", "--max-time", "300", "-o", XLSX, URL])
    if r.returncode != 0 or not os.path.exists(XLSX) or os.path.getsize(XLSX) < 1e7:
        raise RuntimeError("could not download Oxford-Man library (network restricted?).")


def build(tickers):
    _download()
    raw = pd.read_excel(XLSX, header=None)            # wide format: 3 header rows
    idx_names = [str(x) for x in raw.iloc[0].tolist()]    # row 0: index display name
    meas_names = [str(x) for x in raw.iloc[1].tolist()]   # row 1: measure display name
    # row 2 holds short codes (e.g. SPX2.rv); data begins at row 3 with DateID YYYYMMDD
    dates = pd.to_datetime(raw.iloc[3:, 0].astype(float).astype(int).astype(str),
                           format="%Y%m%d")
    cols = {}
    for j in range(1, raw.shape[1]):
        if meas_names[j] == RV5 and idx_names[j] in TICK:
            t = TICK[idx_names[j]]
            if t not in cols:                         # first rv5 column per index block
                cols[t] = pd.to_numeric(raw.iloc[3:, j], errors="coerce").values
    P = pd.DataFrame(cols, index=dates).sort_index()
    miss = [t for t in tickers if t not in P.columns]
    if miss:
        raise SystemExit(f"tickers not in library: {miss}\navailable: {sorted(P.columns)}")
    sub = P[tickers].apply(lambda s: np.log(s.clip(lower=1e-12)))   # log 5-min realized variance
    sub = sub.dropna()                                # common trading days across the basket
    return sub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", default=DEFAULT,
                    help=f"subset of Oxford-Man indices (default cross-region 10: {DEFAULT})")
    args = ap.parse_args()
    P = build(args.tickers)
    np.savez_compressed(OUT, logrv=P.values,
                        dates=P.index.values.astype("datetime64[ns]"),
                        cols=np.array(list(P.columns)))
    print(f"saved {OUT}")
    print(f"  {P.shape[0]} days x {P.shape[1]} assets, "
          f"{P.index.min().date()}..{P.index.max().date()}, measure=5-min realized variance")
    gfc = P[(P.index >= '2008-09-01') & (P.index <= '2009-03-31')]
    print(f"  GFC core window (2008-09..2009-03): {len(gfc)} trading days present")
    print("Now:  python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_oxfordman.npz "
          "--targets SPX DAX N225 --train-end 2007-01-01")


if __name__ == "__main__":
    main()
