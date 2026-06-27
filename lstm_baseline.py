"""
lstm_baseline.py - LSTM baseline for Track A (the one brief-named baseline the repo
was missing; we already have ESN, GARCH(1,1)/GJR-GARCH, AR(3), persistence, HAR).

A compact, dependency-light LSTM implemented in pure NumPy (manual BPTT + Adam), in
keeping with the repo's pure-NumPy doctrine - no torch/tensorflow. It forecasts
one-step-ahead S&P 500 log realized variance from a window of past log-RV values,
evaluated on the SAME crisis split and target dates as CHIMERA/ESN/HAR so the
Diebold-Mariano comparison is apples-to-apples.

The point of this file is completeness and fairness: the challenge explicitly lists
LSTM as a Track-A baseline. On daily 5-min RV, a plain LSTM is not expected to beat
HAR (HAR's linear long-memory form is near-optimal there); reporting that honestly
is exactly what the rubric rewards.

Usage:
  python3 lstm_baseline.py            # crisis split, 3-seed ensemble
  python3 lstm_baseline.py --quick    # smaller/faster

Team EIGENNEXUS | GIC 2026 - Phase 3 (Track A baselines)
"""
import argparse
import time
import numpy as np
import pandas as pd

import volatility_data as vd
from vol_fair_benchmark import rmse, qlike, mz_r2, dm_test, ridge_readout

WINDOW = 22                  # one trading month of daily log-RV history
CRISIS_TRAIN_END = pd.Timestamp("2007-01-01")
CRISIS_TEST_END = pd.Timestamp("2013-01-01")


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


class NumpyLSTM:
    """Single-layer LSTM with a linear head on the last hidden state.
    Batch-first convention; manual BPTT; Adam optimizer."""

    def __init__(self, n_in=1, n_hidden=16, seed=0):
        rng = np.random.RandomState(seed)
        H = n_hidden
        s = 1.0 / np.sqrt(H)
        # gate order in the 4H block: [input, forget, cell, output]
        self.Wx = rng.uniform(-s, s, (n_in, 4 * H))
        self.Wh = rng.uniform(-s, s, (H, 4 * H))
        self.b = np.zeros(4 * H)
        self.b[H:2 * H] = 1.0           # forget-gate bias = 1 (standard, helps memory)
        self.Wo = rng.uniform(-s, s, (H, 1))
        self.bo = np.zeros(1)
        self.H = H
        self._init_adam()

    def _init_adam(self):
        self._m = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._v = {k: np.zeros_like(v) for k, v in self._params().items()}
        self._t = 0

    def _params(self):
        return dict(Wx=self.Wx, Wh=self.Wh, b=self.b, Wo=self.Wo, bo=self.bo)

    def _forward(self, X):
        """X: (B, T, n_in). Returns y_pred (B,) and a cache for BPTT."""
        B, T, _ = X.shape
        H = self.H
        h = np.zeros((B, H)); c = np.zeros((B, H))
        cache = []
        for t in range(T):
            xt = X[:, t, :]
            z = xt @ self.Wx + h @ self.Wh + self.b      # (B,4H)
            i = _sigmoid(z[:, :H]); f = _sigmoid(z[:, H:2 * H])
            g = np.tanh(z[:, 2 * H:3 * H]); o = _sigmoid(z[:, 3 * H:])
            c_new = f * c + i * g
            tc = np.tanh(c_new)
            h_new = o * tc
            cache.append((xt, h, c, i, f, g, o, c_new, tc))
            h, c = h_new, c_new
        y = (h @ self.Wo + self.bo).ravel()              # (B,)
        return y, (cache, h)

    def _backward(self, X, y_pred, y_true, cache_pack):
        cache, h_last = cache_pack
        B, T, _ = X.shape
        H = self.H
        grads = {k: np.zeros_like(v) for k, v in self._params().items()}
        dy = (2.0 / B) * (y_pred - y_true)               # (B,)
        grads["Wo"] += h_last.T @ dy[:, None]
        grads["bo"] += dy.sum(0, keepdims=True).ravel()
        dh = dy[:, None] @ self.Wo.T                     # (B,H)
        dc = np.zeros((B, H))
        for t in reversed(range(T)):
            xt, h_prev, c_prev, i, f, g, o, c_new, tc = cache[t]
            do = dh * tc
            dc = dc + dh * o * (1 - tc ** 2)
            di = dc * g; dg = dc * i; df = dc * c_prev
            dc_prev = dc * f
            dz_i = di * i * (1 - i)
            dz_f = df * f * (1 - f)
            dz_g = dg * (1 - g ** 2)
            dz_o = do * o * (1 - o)
            dz = np.concatenate([dz_i, dz_f, dz_g, dz_o], axis=1)   # (B,4H)
            grads["Wx"] += xt.T @ dz
            grads["Wh"] += h_prev.T @ dz
            grads["b"] += dz.sum(0)
            dh = dz @ self.Wh.T
            dc = dc_prev
        return grads

    def _adam_step(self, grads, lr=5e-3, b1=0.9, b2=0.999, eps=1e-8, clip=5.0):
        self._t += 1
        p = self._params()
        for k in p:
            g = grads[k]
            gn = np.linalg.norm(g)
            if gn > clip:
                g = g * (clip / (gn + 1e-12))
            self._m[k] = b1 * self._m[k] + (1 - b1) * g
            self._v[k] = b2 * self._v[k] + (1 - b2) * (g * g)
            mhat = self._m[k] / (1 - b1 ** self._t)
            vhat = self._v[k] / (1 - b2 ** self._t)
            p[k] -= lr * mhat / (np.sqrt(vhat) + eps)

    def fit(self, X, y, Xval, yval, epochs=60, batch=128, lr=5e-3, patience=8, seed=0):
        rng = np.random.RandomState(seed + 1)
        n = len(X)
        best = np.inf; best_params = None; wait = 0
        for ep in range(epochs):
            idx = rng.permutation(n)
            for s in range(0, n, batch):
                bi = idx[s:s + batch]
                yp, cache = self._forward(X[bi])
                grads = self._backward(X[bi], yp, y[bi], cache)
                self._adam_step(grads, lr=lr)
            vp, _ = self._forward(Xval)
            vloss = float(np.mean((vp - yval) ** 2))
            if vloss < best - 1e-6:
                best = vloss; wait = 0
                best_params = {k: v.copy() for k, v in self._params().items()}
            else:
                wait += 1
                if wait >= patience:
                    break
        if best_params is not None:
            for k, v in self._params().items():
                v[...] = best_params[k]
        return best

    def predict(self, X):
        y, _ = self._forward(X)
        return y


# ---------------------------------------------------------------------------
# Data: contiguous log-RV windows aligned to build_supervised target dates
# ---------------------------------------------------------------------------
def build_lstm_data(window=WINDOW):
    df = vd.load_spx_rv()
    data = vd.build_supervised(df, horizon=1)
    y_logrv, y_rv = data["y_logrv"], data["y_rv"]
    Xhar = data["X_har"]
    dts = pd.to_datetime(data["dates"])

    logrv_raw = df["logrv"]
    pos = {d: k for k, d in enumerate(logrv_raw.index)}
    raw = logrv_raw.values

    seqs, keep = [], []
    for i, d in enumerate(dts):
        p = pos.get(d)
        if p is None or p < window:
            continue
        seqs.append(raw[p - window:p])
        keep.append(i)
    keep = np.array(keep)
    X = np.array(seqs)[:, :, None]            # (N, window, 1)
    return X, y_logrv[keep], y_rv[keep], Xhar[keep], dts[keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    seeds = (0,) if args.quick else (0, 1, 2)
    epochs = 25 if args.quick else 60
    hidden = 12 if args.quick else 16

    t0 = time.time()
    X, y_logrv, y_rv, Xhar, dts = build_lstm_data()
    tr = np.where(dts < CRISIS_TRAIN_END)[0]
    te = np.where((dts >= CRISIS_TRAIN_END) & (dts < CRISIS_TEST_END))[0]

    # standardize inputs & target on TRAIN only (no leakage)
    mu, sd = X[tr].mean(), X[tr].std() or 1.0
    Xs = (X - mu) / sd
    ym, ys = y_logrv[tr].mean(), y_logrv[tr].std() or 1.0
    yz = (y_logrv - ym) / ys

    # validation tail of train for early stopping
    nval = int(0.2 * len(tr)); fit_idx, val_idx = tr[:-nval], tr[-nval:]

    print("=" * 78)
    print("LSTM baseline (pure NumPy) - S&P 500 log-RV, crisis split (GFC in test)")
    print(f"train {dts[tr[0]].date()}..{dts[tr[-1]].date()} (n={len(tr)}) | "
          f"test {dts[te[0]].date()}..{dts[te[-1]].date()} (n={len(te)}) | window={WINDOW}")
    print("=" * 78)

    seed_preds = []
    for sd_ in seeds:
        net = NumpyLSTM(n_in=1, n_hidden=hidden, seed=sd_)
        vloss = net.fit(Xs[fit_idx], yz[fit_idx], Xs[val_idx], yz[val_idx],
                        epochs=epochs, seed=sd_)
        pr = net.predict(Xs[te]) * ys + ym
        seed_preds.append(pr)
        print(f"  seed {sd_}: val_mse(std)={vloss:.4f}  test RMSE(logRV)={rmse(y_logrv[te], pr):.4f}")
    lstm_pred = np.mean(seed_preds, axis=0)

    # HAR on identical dates for a fair DM comparison
    har_pred, _ = ridge_readout(Xhar[tr], y_logrv[tr], Xhar[te])

    yT_log, yT_rv = y_logrv[te], y_rv[te]
    print("\n" + "-" * 78)
    print(f"{'Model':<14}{'RMSE(logRV)':>13}{'QLIKE':>10}{'MZ R2':>8}{'DM vs HAR':>11}{'p':>7}")
    print("-" * 78)
    har_loss = (har_pred - yT_log) ** 2
    for name, pr in [("HAR-RV", har_pred), ("LSTM", lstm_pred)]:
        r = rmse(yT_log, pr); q = qlike(yT_rv, np.exp(pr)); mz = mz_r2(yT_rv, np.exp(pr))
        if name == "HAR-RV":
            ds, dp = 0.0, 1.0
        else:
            ds, dp = dm_test((pr - yT_log) ** 2, har_loss)
        tag = "  *beats HAR" if (not np.isnan(dp) and ds < 0 and dp < 0.05) else ""
        print(f"{name:<14}{r:>13.4f}{q:>10.4f}{mz:>8.3f}{ds:>11.2f}{dp:>7.3f}{tag}")
    print("-" * 78)
    print("(DM<0 & p<0.05 => model beats HAR. On daily 5-min RV, HAR is a very strong bar.)")

    np.save("lstm_results.npy",
            dict(lstm=lstm_pred, har=har_pred, test_dates=[str(d.date()) for d in dts[te]]),
            allow_pickle=True)
    print(f"\nsaved lstm_results.npy   [{time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
