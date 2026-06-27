"""
har_garch_baselines.py - classical realized-volatility baselines for CHIMERA-QRC Track A.

Baselines (all one-step-ahead, evaluated on the same held-out test window):
  - Persistence / random walk        RV_hat_t = RV_{t-1}
  - AR(3) on log-RV                   (OLS)
  - HAR-RV (Corsi 2009)              log-RV on daily/weekly/monthly components (OLS, HAC)
  - GARCH(1,1)                        on returns (arch), leakage-free fixed-param recursion
  - GJR-GARCH(1,1)                    asymmetric (leverage) variant

Metrics:
  - RMSE on log-RV   (the modeled quantity; matches Li et al. PRR 2026 MSE-on-log-RV)
  - QLIKE on variance level (Patton 2011: robust to RV proxy noise, penalizes
    under-prediction of risk more heavily)
  - Mincer-Zarnowitz R^2 + joint test of (alpha,beta)=(0,1)  [forecast efficiency]
  - Diebold-Mariano test vs HAR (HLN small-sample correction)

The HAR baseline is the decisive bar: on proper daily 5-min RV it is notoriously
hard to beat out-of-sample, so matching/beating it is a strong, credible claim -
unlike the anchor paper's weak monthly HAR (their HAR MSE 0.148 vs best 0.103).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import t as student_t
from arch import arch_model

import volatility_data as vd

PCT2_TO_DEC2 = 1.0 / 1e4  # returns are in %, so GARCH variance (%^2) -> decimal^2


# ----------------------------- metrics -----------------------------
def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def qlike(rv_true, var_pred):
    """Patton QLIKE on variance level: mean( log(var) + RV/var ). Lower is better."""
    rv_true = np.asarray(rv_true, float)
    var_pred = np.clip(np.asarray(var_pred, float), 1e-12, None)
    return float(np.mean(np.log(var_pred) + rv_true / var_pred))


def mincer_zarnowitz(rv_true, var_pred):
    """Regress RV_true = a + b*var_pred. Return (R2, F-stat & p for (a,b)=(0,1))."""
    rv_true = np.asarray(rv_true, float)
    X = sm.add_constant(np.asarray(var_pred, float))
    res = sm.OLS(rv_true, X).fit()
    R2 = res.rsquared
    Ft = res.f_test(np.array([[1, 0], [0, 1]]) @ np.eye(2) - 0,  # placeholder, set below
                    ) if False else None
    # joint test (a,b) = (0,1)
    ftest = res.f_test((np.eye(2), np.array([0.0, 1.0])))
    return float(R2), float(ftest.fvalue), float(ftest.pvalue)


def diebold_mariano(loss_model, loss_ref, h=1):
    """HLN-corrected DM test on loss differential d = loss_model - loss_ref.
    Returns (DM stat, two-sided p). Negative & significant => model beats ref."""
    d = np.asarray(loss_model, float) - np.asarray(loss_ref, float)
    T = len(d)
    dbar = d.mean()
    gamma0 = np.mean((d - dbar) ** 2)
    lrv = gamma0
    for k in range(1, h):
        cov = np.mean((d[k:] - dbar) * (d[:-k] - dbar))
        lrv += 2.0 * (1.0 - k / h) * cov
    dm = dbar / np.sqrt(lrv / T)
    corr = np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    dm_hln = dm * corr
    p = 2.0 * (1.0 - student_t.cdf(abs(dm_hln), df=T - 1))
    return float(dm_hln), float(p)


# ----------------------------- models -----------------------------
def fit_predict_ols(Xtr, ytr, Xall):
    """OLS with HAC (Newey-West) covariance; returns predictions over Xall."""
    Xtr_c = sm.add_constant(Xtr)
    res = sm.OLS(ytr, Xtr_c).fit(cov_type="HAC", cov_kwds={"maxlags": 10})
    return res.predict(sm.add_constant(Xall, has_constant="add")), res


def garch_recursive_forecast(ret, train_idx, model="garch"):
    """Leakage-free one-step variance forecasts (decimal^2) for the whole series.
    Fit (omega,alpha,gamma,beta,mu) on TRAIN returns only, then roll the GARCH
    recursion forward through all dates using realized returns. Forecast for day t
    (made at t-1) is sigma^2_t. Returns array len(ret) of decimal^2 variances."""
    ret = np.asarray(ret, float)
    r_train = ret[train_idx]
    vol = "GARCH"
    o = 1 if model == "gjr" else 0
    am = arch_model(r_train, mean="Constant", vol=vol, p=1, o=o, q=1, dist="normal")
    fit = am.fit(disp="off")
    pr = fit.params
    mu = pr.get("mu", 0.0)
    omega = pr["omega"]; alpha = pr["alpha[1]"]; beta = pr["beta[1]"]
    gamma = pr.get("gamma[1]", 0.0)
    denom = max(1e-8, 1.0 - alpha - 0.5 * gamma - beta)
    uncond = omega / denom
    eps = ret - mu
    sig2 = np.empty(len(ret)); sig2[0] = uncond
    for tt in range(1, len(ret)):
        lev = gamma * eps[tt - 1] ** 2 * (eps[tt - 1] < 0)
        sig2[tt] = omega + alpha * eps[tt - 1] ** 2 + lev + beta * sig2[tt - 1]
    return sig2 * PCT2_TO_DEC2, fit


# ----------------------------- run -----------------------------
def run_baselines(horizon=1, train_frac=0.70):
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=horizon)
    y_logrv, y_rv, ret = data["y_logrv"], data["y_rv"], data["ret"]
    Xlag, Xhar = data["X_lags"], data["X_har"]
    tr, te = vd.make_splits(len(y_logrv), train_frac)
    dts = pd.to_datetime(data["dates"])

    results = {}

    # 1) Persistence: predict log-RV_t = lag1 log-RV ; var = exp(that)
    persist_logrv = Xlag[:, 0]  # lag1 is first column
    results["Persistence"] = (persist_logrv, np.exp(persist_logrv))

    # 2) AR(3) on log-RV (use lags 1,2,3 -> first three lag columns are lags 1,2,3)
    ar_pred, _ = fit_predict_ols(Xlag[np.ix_(tr, [0, 1, 2])], y_logrv[tr], Xlag[:, [0, 1, 2]])
    results["AR(3)"] = (ar_pred, np.exp(ar_pred))

    # 3) HAR-RV (Corsi): log-RV on log daily/weekly/monthly components
    har_pred, har_res = fit_predict_ols(Xhar[tr], y_logrv[tr], Xhar)
    results["HAR-RV"] = (har_pred, np.exp(har_pred))

    # 4) GARCH(1,1)
    g_var, g_fit = garch_recursive_forecast(ret, tr, "garch")
    results["GARCH(1,1)"] = (np.log(np.clip(g_var, 1e-12, None)), g_var)

    # 5) GJR-GARCH(1,1)
    gjr_var, gjr_fit = garch_recursive_forecast(ret, tr, "gjr")
    results["GJR-GARCH"] = (np.log(np.clip(gjr_var, 1e-12, None)), gjr_var)

    # ---- evaluate on test window ----
    print(f"\n{'='*78}")
    print(f"S&P 500 realized-volatility one-step-ahead baselines  (Oxford-Man rv5)")
    print(f"test window: {dts[te[0]].date()} .. {dts[te[-1]].date()}  (N_test={len(te)})")
    print(f"{'='*78}")
    print(f"{'Model':<14}{'RMSE(logRV)':>12}{'QLIKE':>10}{'MZ R^2':>9}"
          f"{'DM vs HAR':>11}{'p':>8}")
    print("-" * 78)

    har_loss = (results["HAR-RV"][0][te] - y_logrv[te]) ** 2
    rows = {}
    for name, (logp, varp) in results.items():
        r = rmse(y_logrv[te], logp[te])
        q = qlike(y_rv[te], varp[te])
        r2, _, _ = mincer_zarnowitz(y_rv[te], varp[te])
        if name == "HAR-RV":
            dm_s, dm_p = 0.0, 1.0
        else:
            loss = (logp[te] - y_logrv[te]) ** 2
            dm_s, dm_p = diebold_mariano(loss, har_loss, h=horizon)
        rows[name] = dict(rmse=r, qlike=q, mz=r2, dm=dm_s, p=dm_p)
        tag = "" if name != "HAR-RV" else "  <- benchmark"
        print(f"{name:<14}{r:>12.4f}{q:>10.4f}{r2:>9.3f}{dm_s:>11.2f}{dm_p:>8.3f}{tag}")
    print("-" * 78)
    print("DM sign: negative => model beats HAR; |p|<0.05 => significant.")
    print(f"GARCH(1,1) params: omega={g_fit.params['omega']:.4f} "
          f"alpha={g_fit.params['alpha[1]']:.3f} beta={g_fit.params['beta[1]']:.3f} "
          f"(persistence a+b={g_fit.params['alpha[1]']+g_fit.params['beta[1]']:.3f})")
    return results, rows, data, (tr, te)


if __name__ == "__main__":
    run_baselines()
