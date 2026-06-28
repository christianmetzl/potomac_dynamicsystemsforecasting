"""
fetch_noaa.py  [V3 — Track B, the SUGGESTED data source]

The Track-B brief names NOAA ISD/ASOS as the suggested source ("hourly temperature, pressure,
humidity, wind"). NOAA ISD is public on AWS S3 (reachable here), so we use it directly. We pull
hourly ISD records for one major station (Chicago O'Hare, USAF 725300 / WBAN 94846) over several
years, parse the mandatory fields, derive humidity, resample to a regular hourly grid, and cache to
the SAME panel format as Jena (so v3_weather.py runs on it unchanged via --data).

ISD mandatory fixed-width fields (0-indexed): date[15:23] time[23:27] windspeed[65:69]
air-temp[87:92] dewpoint[93:98] sea-level-pressure[99:104]; scaled /10; sentinels 9999/99999.
RH and saturation vapor pressure (VPmax) are computed from T and dewpoint via the Magnus formula.

Output: noaa_hourly.npz (X [T,K], dates, cols == jena cols).
Then:   python3 v3_research/v3_weather.py --data noaa_hourly.npz
"""
import argparse
import gzip
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://noaa-isd-pds.s3.amazonaws.com/data"
STATION = "725300-94846"          # Chicago O'Hare Intl (ASOS), long continuous hourly record
OUT = os.path.join(HERE, "noaa_hourly.npz")
COLS = ["T (degC)", "p (mbar)", "rh (%)", "VPmax (mbar)", "wv (m/s)", "Tdew (degC)"]


def _num(s, miss):
    s = s.strip()
    if not s or s.lstrip("+-") == miss:
        return np.nan
    try:
        return int(s)
    except ValueError:
        return np.nan


def _es(t):                        # Magnus saturation vapor pressure (hPa)
    return 6.112 * np.exp(17.62 * t / (243.12 + t))


def _is_gzip(path):                 # gzip magic bytes (guards against S3 XML error pages)
    try:
        with open(path, "rb") as fh:
            return fh.read(2) == b"\x1f\x8b"
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int, default=list(range(2010, 2017)))
    ap.add_argument("--station", default=STATION)
    ap.add_argument("--out", default=OUT, help="output npz path (default noaa_hourly.npz)")
    ap.add_argument("--name", default="Chicago O'Hare", help="human label for the station")
    args = ap.parse_args()
    out_path = args.out if os.path.isabs(args.out) else os.path.join(HERE, args.out)
    import subprocess
    recs = []
    for yr in args.years:
        gz = os.path.join(HERE, f"_isd_{args.station}_{yr}.gz")
        if not (os.path.exists(gz) and os.path.getsize(gz) > 1000 and _is_gzip(gz)):
            r = subprocess.run(["curl", "-sSL", "--max-time", "120", "-o", gz,
                                f"{BASE}/{yr}/{args.station}-{yr}.gz"])
            if r.returncode != 0 or not os.path.exists(gz):
                print(f"  {yr}: download failed — skipped"); continue
        if not _is_gzip(gz):     # S3 returns a small XML 'NoSuchKey' page for missing station-years
            print(f"  {yr}: no ISD file for this station-year — skipped")
            try: os.remove(gz)
            except OSError: pass
            continue
        lines = gzip.open(gz, "rt", errors="replace").read().splitlines()
        for l in lines:
            if len(l) < 105:
                continue
            try:
                dt = pd.Timestamp(l[15:23] + l[23:27], tz="UTC")
            except Exception:
                continue
            T = _num(l[87:92], "9999"); Td = _num(l[93:98], "9999")
            slp = _num(l[99:104], "99999"); wv = _num(l[65:69], "9999")
            recs.append((dt, T, Td, slp, wv))
        print(f"  {yr}: {len(lines)} ISD records")
    df = pd.DataFrame(recs, columns=["dt", "T", "Td", "slp", "wv"]).set_index("dt").sort_index()
    df = df[~df.index.duplicated()]
    df["T"] /= 10.0; df["Td"] /= 10.0; df["slp"] /= 10.0; df["wv"] /= 10.0   # ISD scaling
    df = df.dropna(subset=["T"])
    # regular hourly grid; interpolate short gaps
    h = df.resample("1h").mean().interpolate(limit=6).dropna(subset=["T", "Td"])
    rh = (100.0 * _es(h["Td"]) / _es(h["T"])).clip(1, 100)
    vpmax = _es(h["T"])
    out = pd.DataFrame({
        "T (degC)": h["T"], "p (mbar)": h["slp"].fillna(h["slp"].median()),
        "rh (%)": rh, "VPmax (mbar)": vpmax, "wv (m/s)": h["wv"].fillna(0).clip(lower=0),
        "Tdew (degC)": h["Td"]}).dropna()
    np.savez_compressed(out_path, X=out[COLS].values,
                        dates=out.index.tz_localize(None).values.astype("datetime64[ns]"),
                        cols=np.array(COLS))
    print(f"\nsaved {out_path}")
    print(f"  {out.shape[0]} hourly rows x {out.shape[1]} vars, "
          f"{out.index.min().date()}..{out.index.max().date()}  station={args.station} ({args.name})")
    print(f"  T range {out['T (degC)'].min():.1f}..{out['T (degC)'].max():.1f} C")
    print(f"Now:  python3 v3_research/v3_weather.py --data {os.path.basename(out_path)}")


if __name__ == "__main__":
    main()
