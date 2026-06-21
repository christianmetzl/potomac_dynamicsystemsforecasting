"""
vol_fair_benchmark.py - HEADLINE Track A benchmark for CHIMERA-QRC.

Task: one-step-ahead forecasting of S&P 500 log realized variance (Oxford-Man rv5,
2000-2020, GFC included). Train 2000-2014, test 2014-2020, fully out-of-sample.

Fair-comparison discipline (carried from the Denver benchmark):
  * ESN and CHIMERA receive IDENTICAL inputs: 8 multi-horizon lagged log-RV values
    (lags 1,2,3,4,5,10,15,22 days), min-max scaled to [0,1] on TRAIN only.
  * Every reservoir readout is hybridized with the raw lags AND the HAR-RV
    information set (daily/weekly/monthly log-RV components), so any reservoir gain
    is genuine NONLINEARITY beyond what HAR/AR already capture - not missing linear
    structure. The reservoir must beat HAR *on top of* HAR's own inputs.
  * Ridge penalty selected per model on a validation tail of the training set
    (equal treatment). 3 random reservoir seeds; predictions ensembled.

Models:
  HAR-RV            linear benchmark (Corsi components)
  ESN-108           classical reservoir, matched to CHIMERA-3scale feature count
  ESN-400           classical reservoir, 4x larger reference
  CHIMERA-1scale    quantum, single timescale tau=2           (36 features)
  CHIMERA-3scale    quantum, geometric bank tau=(1,2,4)        (108 features)  [HEADLINE]

The CHIMERA-1scale vs CHIMERA-3scale contrast is the direct analogue of the anchor
paper's QR1 (one timescale) vs QR2 (two timescales) result - testing Innovation 1.

Metrics: RMSE(log-RV), QLIKE (variance level), Mincer-Zarnowitz R^2;
Diebold-Mariano (HLN) for the decisive pairwise tests; Model Confidence Set (95%).

Team EIGENNEXUS | GIC 2026 - Phase 2 (Track A, real data, fair comparison)
"""
import numpy as np
from scipy import stats
import volatility_data as vd
from classical_baselines import EchoStateNetwork
from multiscale_chimera import MultiScaleCHIMERA

LAGS = (1, 2, 3, 4, 5, 10, 15, 22)   # 8 multi-horizon lags -> 8 input qubits
N_QUBITS = 8
SEEDS = (0, 1, 2)
LAMBDAS = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1)
VAL_FRAC = 0.20
RIDGE_FEAT = 1e-7   # tiny load on reservoir feature extraction readout (unused: per-model select)


# ----------------------- metrics -----------------------
def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))

def qlike(rv_true, var_pred):
    var_pred = np.clip(var_pred, 1e-12, None)
    return float(np.mean(np.log(var_pred) + rv_true / var_pred))

def mz_r2(rv_true, var_pred):
    X = np.column_stack([np.ones_like(var_pred), var_pred])
    beta, *_ = np.linalg.lstsq(X, rv_true, rcond=None)
    pred = X @ beta
    ss = np.sum((rv_true - pred) ** 2); tot = np.sum((rv_true - rv_true.mean()) ** 2)
    return float(1 - ss / tot)

def dm_test(loss1, loss2, h=1):
    """HLN-corrected Diebold-Mariano on loss differential d=loss1-loss2.
    Negative & significant => model1 better than model2."""
    d = loss1 - loss2; T = len(d); db = d.mean()
    v = np.mean((d - db) ** 2)
    for l in range(1, h):
        v += 2 * (1 - l / h) * np.mean((d[l:] - db) * (d[:-l] - db))
    v /= T
    if v <= 0:
        return np.nan, np.nan
    s = db / np.sqrt(v) * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return float(s), float(2 * (1 - stats.t.cdf(abs(s), df=T - 1)))


def model_confidence_set(loss_dict, B=2000, block=20, alpha=0.05, seed=0):
    """MCS (Hansen-Lunde-Nason 2011) via stationary bootstrap + range statistic.
    loss_dict: name -> per-obs loss array (equal length). Returns (surviving, pvals)."""
    names = list(loss_dict)
    L = np.array([loss_dict[n] for n in names])  # (M,T)
    M, T = L.shape
    rng = np.random.RandomState(seed)
    boots = []
    for _ in range(B):
        idx = np.empty(T, int); i = 0
        while i < T:
            start = rng.randint(T); ln = max(1, rng.geometric(1.0 / block))
            for j in range(ln):
                if i >= T: break
                idx[i] = (start + j) % T; i += 1
        boots.append(idx)
    surviving = list(range(M)); pvals = {}
    while len(surviving) > 1:
        sub = L[surviving]; m = len(surviving)
        d_i = sub.mean(1) - sub.mean()
        boot_d = np.empty((B, m))
        for b, idx in enumerate(boots):
            sb = sub[:, idx]; boot_d[b] = sb.mean(1) - sb.mean()
        var_i = boot_d.var(0) + 1e-15
        t_i = d_i / np.sqrt(var_i)
        TR = t_i.max()
        boot_TR = ((boot_d - d_i) / np.sqrt(var_i)).max(axis=1)
        p = float((boot_TR >= TR).mean())
        worst = surviving[int(np.argmax(t_i))]
        pvals[names[worst]] = p
        if p > alpha:
            break
        surviving.remove(worst)
    for s in surviving:
        pvals.setdefault(names[s], 1.0)
    return [names[s] for s in surviving], pvals


# ----------------------- readout -----------------------
def _standardize(M, mu, sd):
    return (M - mu) / sd

def ridge_readout(D_tr, y_tr, D_te, lambdas=LAMBDAS, val_frac=VAL_FRAC):
    """Standardize (train stats), select ridge on a validation tail, refit on full
    train, return test predictions in original (log-RV) units and chosen lambda."""
    n = len(y_tr); nval = int(round(n * val_frac)); nfit = n - nval
    best_l, best_v = lambdas[0], np.inf
    # selection split
    Dft, yft, Dval, yval = D_tr[:nfit], y_tr[:nfit], D_tr[nfit:], y_tr[nfit:]
    mu, sd = Dft.mean(0), Dft.std(0); sd = np.where(sd < 1e-8, 1.0, sd)
    ym, ys = yft.mean(), yft.std() or 1.0
    Xft = _standardize(Dft, mu, sd); Xval = _standardize(Dval, mu, sd)
    yft_s = (yft - ym) / ys
    A = Xft.T @ Xft; rhs = Xft.T @ yft_s; I = np.eye(A.shape[0])
    for lam in lambdas:
        W = np.linalg.solve(A + lam * I, rhs)
        pred = (Xval @ W) * ys + ym
        v = rmse(yval, pred)
        if v < best_v:
            best_v, best_l = v, lam
    # refit on full train with best lambda
    mu, sd = D_tr.mean(0), D_tr.std(0); sd = np.where(sd < 1e-8, 1.0, sd)
    ym, ys = y_tr.mean(), y_tr.std() or 1.0
    Xtr = _standardize(D_tr, mu, sd); Xte = _standardize(D_te, mu, sd)
    ytr_s = (y_tr - ym) / ys
    W = np.linalg.solve(Xtr.T @ Xtr + best_l * np.eye(Xtr.shape[1]), Xtr.T @ ytr_s)
    return (Xte @ W) * ys + ym, best_l


# ----------------------- reservoir feature maps -----------------------
def esn_features(Q, n_res, seed):
    esn = EchoStateNetwork(n_reservoir=n_res, spectral_radius=0.9, leaking_rate=0.5,
                           input_scaling=1.0, connectivity=0.05, ridge_alpha=1e-6, seed=seed)
    esn._init_input_weights(Q.shape[1])
    F = np.empty((len(Q), n_res))
    for i, w in enumerate(Q):
        esn.reset(); F[i] = esn.step(w)
    return F

def chimera_features(Q, taus, seed):
    ch = MultiScaleCHIMERA(n_qubits=N_QUBITS, taus=taus, hamiltonian='ising',
                           hx=1.0, connectivity=0.5, seed=seed)
    ch._reset_feedback()
    return np.array([ch._all_features(w) for w in Q])


# ----------------------- run -----------------------
def main():
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1, lags=LAGS)
    Xlag, Xhar = data["X_lags"], data["X_har"]
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    dts = data["dates"]
    tr, te = vd.make_splits(len(y_logrv), train_frac=0.70)

    # scale lags to [0,1] on TRAIN for reservoir encoding
    lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rng = np.where((hi - lo) == 0, 1, hi - lo)
    Q = np.clip((Xlag - lo) / rng, 0.0, 1.0)
    LIN = np.hstack([Xlag, Xhar])  # raw lags + HAR components for the hybrid readout

    import pandas as pd
    print("=" * 84)
    print("CHIMERA-QRC Track A headline benchmark - S&P 500 realized variance (Oxford-Man rv5)")
    print(f"train {pd.Timestamp(dts[tr[0]]).date()}..{pd.Timestamp(dts[tr[-1]]).date()} (n={len(tr)}, incl. GFC) | "
          f"test {pd.Timestamp(dts[te[0]]).date()}..{pd.Timestamp(dts[te[-1]]).date()} (n={len(te)})")
    print("=" * 84)

    preds = {}   # name -> ensemble log-RV test prediction
    perseed = {} # name -> list of per-seed RMSE(logRV)

    # HAR-RV benchmark (linear, HAR components only)
    p, lam = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te])
    preds["HAR-RV"] = p

    reservoir_specs = [
        ("ESN-108", "esn", 108),
        ("ESN-400", "esn", 400),
        ("CHIMERA-1scale", "chim", (2.0,)),
        ("CHIMERA-3scale", "chim", (1.0, 2.0, 4.0)),
    ]
    for name, kind, arg in reservoir_specs:
        seed_preds, seed_rmse = [], []
        for sd in SEEDS:
            if kind == "esn":
                F = esn_features(Q, arg, sd)
            else:
                F = chimera_features(Q, arg, sd)
            D = np.hstack([F, LIN])
            pr, lam = ridge_readout(D[tr], y_logrv[tr], D[te])
            seed_preds.append(pr); seed_rmse.append(rmse(y_logrv[te], pr))
        preds[name] = np.mean(seed_preds, axis=0)   # ensemble across seeds
        perseed[name] = seed_rmse
        fdim = (N_QUBITS + N_QUBITS * (N_QUBITS - 1) // 2) * (len(arg) if kind == "chim" else 1) \
               if kind == "chim" else arg
        print(f"  built {name:<16} feat_dim={fdim:<4} seeds RMSE(logRV)="
              f"[{', '.join(f'{x:.4f}' for x in seed_rmse)}]")

    # ---- evaluation (ensemble predictions) ----
    yT_log, yT_rv = y_logrv[te], y_rv[te]
    har_loss = (preds["HAR-RV"] - yT_log) ** 2
    esn108_loss = (preds["ESN-108"] - yT_log) ** 2
    c1_loss = (preds["CHIMERA-1scale"] - yT_log) ** 2

    print("\n" + "-" * 84)
    print(f"{'Model':<16}{'RMSE(logRV)':>13}{'±seed':>8}{'QLIKE':>10}{'MZ R2':>8}"
          f"{'DMvsHAR':>9}{'p':>7}")
    print("-" * 84)
    loss_dict = {}
    for name in ["HAR-RV", "ESN-108", "ESN-400", "CHIMERA-1scale", "CHIMERA-3scale"]:
        p = preds[name]; var = np.exp(p)
        r = rmse(yT_log, p); q = qlike(yT_rv, var); mz = mz_r2(yT_rv, var)
        sdv = np.std(perseed[name]) if name in perseed else 0.0
        loss = (p - yT_log) ** 2; loss_dict[name] = loss
        if name == "HAR-RV":
            ds, dp = 0.0, 1.0
        else:
            ds, dp = dm_test(loss, har_loss)
        star = "" if (np.isnan(dp) or dp >= 0.05 or ds > 0) else "  *beats HAR"
        print(f"{name:<16}{r:>13.4f}{sdv:>8.4f}{q:>10.4f}{mz:>8.3f}{ds:>9.2f}{dp:>7.3f}{star}")
    print("-" * 84)

    # decisive pairwise DM tests on the ensemble
    s_ce, p_ce = dm_test(c1_loss * 0 + (preds["CHIMERA-3scale"] - yT_log) ** 2, esn108_loss)
    s_cc, p_cc = dm_test((preds["CHIMERA-3scale"] - yT_log) ** 2, c1_loss)
    print("Decisive tests (DM on seed-ensemble, squared-error of log-RV):")
    print(f"  CHIMERA-3scale vs ESN-108 (matched, quantum-vs-classical): DM={s_ce:.2f}  p={p_ce:.3f}"
          f"  {'-> CHIMERA better' if (not np.isnan(p_ce) and s_ce<0 and p_ce<0.05) else '-> n.s.'}")
    print(f"  CHIMERA-3scale vs CHIMERA-1scale (multi vs single, QR2>QR1): DM={s_cc:.2f}  p={p_cc:.3f}"
          f"  {'-> multi-scale better' if (not np.isnan(p_cc) and s_cc<0 and p_cc<0.05) else '-> n.s.'}")

    surv, mp = model_confidence_set(loss_dict)
    print(f"\nModel Confidence Set (95%): {{{', '.join(surv)}}}")
    print("  MCS p-values: " + ", ".join(f"{k}={v:.3f}" for k, v in mp.items()))

    np.save("vol_fair_results.npy",
            {"preds": preds, "perseed": perseed, "mcs": surv, "mcs_p": mp,
             "test_dates": [str(pd.Timestamp(d).date()) for d in dts[te]]},
            allow_pickle=True)
    print("\nsaved vol_fair_results.npy")


if __name__ == "__main__":
    main()
