"""
fetch_jena.py  [V3 — EXPLORATORY, NOT part of the V1 submission]

Track B (weather) exploration. NOTE: the official GIC-2026 Track-B brief is NOT in this repo, so
the precise task is INFERRED — we use the standard public weather-forecasting benchmark and a
standard target (temperature). If the real Track-B spec differs, the engine + protocol transfer;
only the target/series change.

Data: Jena Climate (Max-Planck-Institute for Biogeochemistry), 2009-2016, 10-minute sampling,
14 atmospheric variables — the canonical weather time-series benchmark (Keras tutorials). Fetched
from the public TF/Keras mirror on storage.googleapis.com (reachable here). We resample to HOURLY
(every 6th row, the standard choice) and cache the multivariate frame to v3_research/jena_hourly.npz.

Output: jena_hourly.npz  (cols [K] str, dates [T] datetime64, X [T,K] float).
Then:   python3 v3_research/v3_weather.py
"""
import os
import zipfile
import numpy as np
import pandas as pd

URL = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/jena_climate_2009_2016.csv.zip"
HERE = os.path.dirname(os.path.abspath(__file__))
ZIP = os.path.join(HERE, "_jena.csv.zip")
OUT = os.path.join(HERE, "jena_hourly.npz")
KEEP = ["T (degC)", "p (mbar)", "rh (%)", "VPmax (mbar)", "wv (m/s)", "Tdew (degC)"]


def main():
    if not (os.path.exists(ZIP) and os.path.getsize(ZIP) > 1e7):
        import subprocess
        print("(downloading Jena climate once ...)")
        r = subprocess.run(["curl", "-sSL", "--max-time", "300", "-o", ZIP, URL])
        if r.returncode != 0 or not os.path.exists(ZIP):
            raise RuntimeError("could not download Jena climate (network).")
    with zipfile.ZipFile(ZIP) as z:
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        with z.open(name) as f:
            df = pd.read_csv(f)
    df["Date Time"] = pd.to_datetime(df["Date Time"], format="%d.%m.%Y %H:%M:%S")
    df = df.set_index("Date Time").sort_index()
    df = df[~df.index.duplicated()]
    # Jena uses -9999 sentinels for a few bad wind rows -> clip wind to >=0
    if "wv (m/s)" in df:
        df["wv (m/s)"] = df["wv (m/s)"].clip(lower=0)
    hourly = df[KEEP].iloc[::6].dropna()                # every 6th 10-min row = hourly
    np.savez_compressed(OUT, X=hourly.values,
                        dates=hourly.index.values.astype("datetime64[ns]"),
                        cols=np.array(KEEP))
    print(f"saved {OUT}")
    print(f"  {hourly.shape[0]} hourly rows x {hourly.shape[1]} vars, "
          f"{hourly.index.min().date()}..{hourly.index.max().date()}")
    print(f"  vars: {KEEP}")
    print("Now:  python3 v3_research/v3_weather.py")


if __name__ == "__main__":
    main()
