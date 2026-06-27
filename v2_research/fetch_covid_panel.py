"""
fetch_covid_panel.py  [V2 helper] — build a COVID-INCLUSIVE multi-index realized-variance
panel, to close the one crisis gap none of our other datasets reach.

WHY: V1's .SPX 5-min RV ends 2020-02-21 (the eve of the COVID crash); the Oxford-Man
multi-index mirror ends 2016; the Massive tier starts 2021. So the March-2020 COVID volatility
spike was untested. This builds a dated panel that DOES contain it (and the 2008 GFC).

DATA SOURCE & PROVENANCE (honest): daily OHLC index levels for 8 liquid global equity indices,
mirrored publicly in the GitHub repo `andymogul/SpilloverVolPrediction` ("global index etf
return/*.csv"), spanning 2006-10 .. 2022-06 — i.e. INCLUDING both the 2008 GFC and the 2020
COVID crash. We compute a daily GARMAN-KLASS log realized-variance per index from OHLC.

HONEST QUALITY NOTE: this is a DAILY Garman-Klass PROXY, not true 5-minute realized variance
(GK uses only OHLC and understates intraday spikes — e.g. SPX March-2020 reads ~81% annualised
vs the higher true intraday RV). It is therefore NOT a quality upgrade over V1's 5-min .SPX or
the Oxford-Man 5-min panel; its sole purpose is to add the otherwise-missing COVID regime.
A true-5-min COVID panel would need the post-2020 Oxford-Man library (discontinued/host blocked)
or a paid intraday feed.

OUTPUT: v2_research/cross_asset_panel_covid.npz (logrv [T,K], dates [T], cols [K]). Then:
    python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_covid.npz \
            --targets SPX DAX N225 --train-end 2020-01-01   # test = COVID era 2020-2022
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cross_asset_panel_covid.npz")
BASE = ("https://raw.githubusercontent.com/andymogul/SpilloverVolPrediction/main/"
        "global%20index%20etf%20return")
# repo filename -> clean ticker (8 global indices, dense-statevector-simulable at 8 qubits)
TICK = {"SPX": "SPX", "GDAXI": "DAX", "FCHI": "CAC", "FTSE": "FTSE",
        "OMXSPI": "OMXS", "N225": "N225", "KS11": "KOSPI", "HSI": "HSI"}


def _gk_logrv(o, h, l, c):
    v = 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    return np.log(v.clip(lower=1e-10))


def build():
    import subprocess
    panel = {}
    for fn, tk in TICK.items():
        raw = os.path.join(HERE, f"_covid_{fn}.csv")
        if not (os.path.exists(raw) and os.path.getsize(raw) > 1000):
            r = subprocess.run(["curl", "-sSL", "--max-time", "90", "-o", raw, f"{BASE}/{fn}.csv"])
            if r.returncode != 0 or not os.path.exists(raw):
                raise RuntimeError(f"could not download {fn}.csv (network?)")
        df = pd.read_csv(raw)
        for col in ("Price", "Open", "High", "Low"):
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        df["d"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
        df = df.dropna(subset=["d", "Open", "High", "Low", "Price"]).set_index("d").sort_index()
        panel[tk] = _gk_logrv(df["Open"], df["High"], df["Low"], df["Price"])
    P = pd.DataFrame(panel).dropna()
    return P


def main():
    P = build()
    np.savez_compressed(OUT, logrv=P.values,
                        dates=P.index.values.astype("datetime64[ns]"),
                        cols=np.array(list(P.columns)))
    print(f"saved {OUT}")
    print(f"  {P.shape[0]} days x {P.shape[1]} assets, "
          f"{P.index.min().date()}..{P.index.max().date()}, measure=daily Garman-Klass")
    for lbl, a, b in [("GFC 2008-09..2009-03", "2008-09-01", "2009-03-31"),
                      ("COVID 2020-02..2020-12", "2020-02-15", "2020-12-31")]:
        n = ((P.index >= a) & (P.index <= b)).sum()
        print(f"  {lbl}: {n} trading days present")
    print("Now:  python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_covid.npz "
          "--targets SPX DAX N225 --train-end 2020-01-01")


if __name__ == "__main__":
    main()
