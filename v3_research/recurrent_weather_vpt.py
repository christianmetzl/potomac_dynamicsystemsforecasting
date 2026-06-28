"""
recurrent_weather_vpt.py  [V3 — recurrent CHIMERA, autonomous rollout on REAL station weather]

Extends the recurrent-QRC VPT idea (recurrent_qrc.py, Lorenz-63) to REAL weather. Instead of a clean
deterministic chaotic system we free-run the recurrent reservoir on an actual station's hourly
temperature, in AUTONOMOUS (closed-loop) mode: the model feeds its own temperature prediction back as
the next input, while the wall-clock (hour-of-day, always knowable in the future) is injected as an
exogenous driver so the rollout can phase-lock to the diurnal cycle. This is the architecturally
correct quantum reservoir (persistent state, input-qubit reset; Fujii-Nakajima / Kornjaca / Li) run
on the messy real series. Honest by construction; no V1 file touched.

IMPORTANT, stated up front: real station weather is stochastic-plus-chaotic, NOT a clean deterministic
chaotic flow, so a Lyapunov time is ill-defined. We therefore report VPT in HOURS (and in diurnal
cycles = hours/24), not Lyapunov times. The decisive comparison is still the FAIR one — recurrent-
CHIMERA vs a SIZE-MATCHED recurrent ESN — plus a strong ESN and the climatology baseline a long
autonomous weather rollout is really judged against (predict the hour-of-day mean).

Input u_t = [T_norm_t, sin(2pi h/24), cos(2pi h/24)] (n_in=3); target T_norm_{t+1}; readout = ridge.
VPT = first hour where |pred - true|/std(T) > 0.4, averaged over many starts.

Usage:  python3 recurrent_weather_vpt.py                       # Jena, n=8, 20 starts, seeds 0-1
        python3 recurrent_weather_vpt.py --data denver_hourly.npz
        python3 recurrent_weather_vpt.py --quick                # n=7, 8 starts, seed 0
"""
import argparse
import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from recurrent_qrc import RecurrentQRC
from classical_baselines import EchoStateNetwork

HERE = os.path.dirname(os.path.abspath(__file__))
THRESH = 0.4
WARM = 60


def load_series(data, span):
    d = np.load(os.path.join(HERE, data), allow_pickle=True)
    X = d["X"].astype(float); cols = [str(c) for c in d["cols"]]
    T = X[:, cols.index("T (degC)")]
    if span and len(T) > span:
        T = T[-span:]
    lo, hi = T.min(), T.max()
    Tn = (T - lo) / (hi - lo)                      # [0,1] for the encoder
    idx = np.arange(len(T))
    h = idx % 24                                    # hour-of-day (data is hourly, regular grid)
    clk_s = (np.sin(2 * np.pi * h / 24) + 1) / 2    # clock features in [0,1]
    clk_c = (np.cos(2 * np.pi * h / 24) + 1) / 2
    U = np.column_stack([Tn, clk_s, clk_c])         # input rows [T, sin, cos]
    return Tn, U, h, idx


def _harmonics(idx):
    """Design matrix for a seasonal+diurnal climatology: diurnal (1st/2nd) + annual (1st/2nd)."""
    hod = idx % 24
    day = idx / 24.0
    d = 2 * np.pi * hod / 24.0
    a = 2 * np.pi * day / 365.25
    return np.column_stack([np.ones_like(day), np.sin(d), np.cos(d), np.sin(2 * d), np.cos(2 * d),
                            np.sin(a), np.cos(a), np.sin(2 * a), np.cos(2 * a)])


def _vpt_hours(true, pred, std):
    err = np.abs(pred - true) / std
    bad = np.where(err > THRESH)[0]
    return int(bad[0]) if len(bad) else len(err)


def rqrc_rollout(Tn, U, tr, starts, horizon, std, n, n_in, seed):
    qr = RecurrentQRC(n, n_in, seed)
    qr.reset()
    for t in range(WARM):
        qr.step(U[t])
    F = [qr.step(U[t]) for t in range(WARM, tr - 1)]
    F = np.array(F); Y = Tn[WARM + 1:tr]            # features at t -> T_{t+1}
    Fb = np.hstack([F, np.ones((len(F), 1))])
    nfit = int(0.85 * len(F))
    Wt = np.linalg.solve(Fb[:nfit].T @ Fb[:nfit] + 1e-4 * np.eye(Fb.shape[1]), Fb[:nfit].T @ Y[:nfit])
    pr = Fb[nfit:] @ Wt                             # one-step diagnostic R^2 on held-out train tail
    r2 = 1 - np.sum((Y[nfit:] - pr) ** 2) / np.sum((Y[nfit:] - Y[nfit:].mean()) ** 2)
    vpts = []
    for s0 in starts:
        qr.reset()
        for t in range(s0 - 1 - WARM, s0 - 1):      # warm up on true inputs
            qr.step(U[t])
        cur = Tn[s0 - 1]; true = Tn[s0:s0 + horizon]; pred = np.empty(horizon)
        for hh in range(horizon):
            u = np.array([cur, U[s0 - 1 + hh, 1], U[s0 - 1 + hh, 2]])   # own T + TRUE clock
            f = qr.step(u)
            cur = np.hstack([f, 1.0]) @ Wt
            pred[hh] = cur
        vpts.append(_vpt_hours(true, pred, std))
    return float(np.mean(vpts)), float(np.std(vpts)), float(r2)


def esn_rollout(Tn, U, tr, starts, horizon, std, n_res, seed):
    esn = EchoStateNetwork(n_reservoir=n_res, spectral_radius=0.95, leaking_rate=0.3,
                           input_scaling=1.0, connectivity=0.1, ridge_alpha=1e-6, seed=seed)
    esn._init_input_weights(3); esn.reset()
    S = np.array([esn.step(U[t]) for t in range(tr - 1)])
    Fb = np.hstack([S, np.ones((tr - 1, 1))])
    Wt = np.linalg.solve(Fb.T @ Fb + 1e-6 * np.eye(Fb.shape[1]), Fb.T @ Tn[1:tr])
    vpts = []
    for s0 in starts:
        esn.reset()
        for t in range(s0 - 1 - WARM, s0 - 1):
            esn.step(U[t])
        cur = Tn[s0 - 1]; true = Tn[s0:s0 + horizon]; pred = np.empty(horizon)
        for hh in range(horizon):
            st = esn.step(np.array([cur, U[s0 - 1 + hh, 1], U[s0 - 1 + hh, 2]]))
            cur = np.hstack([st, 1.0]) @ Wt
            pred[hh] = cur
        vpts.append(_vpt_hours(true, pred, std))
    return float(np.mean(vpts))


def clim_vpt(Tn, idx, tr, starts, horizon, std):
    """Seasonal+diurnal climatology baseline (harmonic regression fit on train)."""
    Phi = _harmonics(idx)
    Wt = np.linalg.solve(Phi[:tr].T @ Phi[:tr] + 1e-6 * np.eye(Phi.shape[1]), Phi[:tr].T @ Tn[:tr])
    clim = Phi @ Wt
    vpts = []
    for s0 in starts:
        true = Tn[s0:s0 + horizon]
        pred = clim[s0:s0 + horizon]
        vpts.append(_vpt_hours(true, pred, std))
    return float(np.mean(vpts))


def persist_vpt(Tn, starts, horizon, std):
    vpts = []
    for s0 in starts:
        true = Tn[s0:s0 + horizon]
        pred = np.full(horizon, Tn[s0 - 1])         # closed-loop persistence -> constant
        vpts.append(_vpt_hours(true, pred, std))
    return float(np.mean(vpts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--data", default="jena_hourly.npz")
    args = ap.parse_args()
    n = 7 if args.quick else 8
    n_in = 3
    seeds = (0,) if args.quick else (0, 1)
    n_starts = 8 if args.quick else 24
    span = 12000 if args.quick else 26000
    horizon = 240                                   # 10 days of hourly autonomous rollout
    t0 = time.time()

    Tn, U, hod, idx = load_series(args.data, span)
    tr = int(0.6 * len(Tn))
    std = float(Tn.std())
    feat = n + n * (n - 1) // 2
    rng = np.random.RandomState(0)
    starts = rng.randint(tr + WARM + 1, len(Tn) - horizon, size=n_starts)
    stem = os.path.basename(args.data).replace("_hourly.npz", "").replace(".npz", "")

    print("#" * 88)
    print("V3 RECURRENT CHIMERA on REAL station weather — autonomous closed-loop VPT (hours)")
    print(f"  data={stem}  n={n} ({n_in} input + {n-n_in} memory)  horizon={horizon}h  "
          f"{n_starts} starts  seeds={seeds}")
    print(f"  VPT = first hour where |pred-true|/std(T) > {THRESH}; clock injected (diurnal phase known)")
    print("#" * 88)

    rq = [rqrc_rollout(Tn, U, tr, starts, horizon, std, n, n_in, sd) for sd in seeds]
    rq_m = float(np.mean([x[0] for x in rq])); rq_sd = float(np.std([x[0] for x in rq]))
    rq_r2 = float(np.mean([x[2] for x in rq]))
    esM = float(np.mean([esn_rollout(Tn, U, tr, starts, horizon, std, feat, sd) for sd in seeds]))
    esS = float(np.mean([esn_rollout(Tn, U, tr, starts, horizon, std, 300, sd) for sd in seeds]))
    clim = clim_vpt(Tn, idx, tr, starts, horizon, std)
    per = persist_vpt(Tn, starts, horizon, std)

    print(f"\n  recurrent-CHIMERA one-step train R^2 = {rq_r2:.3f}")
    print(f"\n  {'model':<34}{'VPT (hours)':>12}{'(diurnal cycles)':>18}")
    rows = [("Persistence (closed-loop)", per), ("Seasonal+diurnal climatology", clim),
            (f"Recurrent-CHIMERA (n={n})", rq_m),
            (f"ESN, size-matched ({feat} nodes)", esM), ("ESN, strong (300 nodes)", esS)]
    for nm, v in rows:
        print(f"  {nm:<34}{v:>12.1f}{v/24:>18.2f}")

    print("\n" + "=" * 88)
    fair = "MATCHES/EXCEEDS" if rq_m >= esM else "is below"
    print(f"FAIR test (size-matched, both recurrent): recurrent-CHIMERA ({rq_m:.1f}h) {fair} the "
          f"size-matched ESN ({esM:.1f}h).")
    if rq_m >= esM:
        print("  -> at matched size the recurrent quantum reservoir is COMPETITIVE on real-weather VPT.")
    else:
        print("  -> no quantum advantage on real-weather VPT even in the fair matched recurrent paradigm.")
    print(f"NOTE: seasonal+diurnal climatology ({clim:.1f}h) and closed-loop persistence ({per:.1f}h) are "
          f"the trivial bars; recurrent-CHIMERA {'beats' if rq_m > max(clim, per) else 'does NOT beat'} both.")
    print("  Real station weather is stochastic-plus-chaotic (no clean Lyapunov time); VPT is in hours.")
    if not args.quick:
        np.save(os.path.join(HERE, f"recurrent_weather_vpt_{stem}.npy"),
                dict(persist=per, clim=clim, rqrc=rq_m, rqrc_sd=rq_sd, rqrc_r2=rq_r2,
                     esn_matched=esM, esn_strong=esS, n=n, feat=feat, horizon=horizon, data=args.data),
                allow_pickle=True)
        print(f"saved recurrent_weather_vpt_{stem}.npy  [{time.time()-t0:.1f}s]")
    else:
        print(f"[--quick] not written  [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
