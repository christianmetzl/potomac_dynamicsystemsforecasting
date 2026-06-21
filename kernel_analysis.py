"""
kernel_analysis.py - quantify whether the quantum reservoir feature map is
distinct from / more efficient than the matched classical (ESN) reservoir,
on the real Oxford-Man S&P 500 realized-variance data (train window).

Metrics (Huang et al. 2021 framework + standard kernel diagnostics):
  * effective dimension D_eff = (sum lambda)^2 / sum lambda^2  (participation ratio)
  * kernel-target alignment KTA (centered) to the log-RV target
  * geometric difference g(K_A || K_B) = sqrt( ||K_B^{1/2} (K_A+reg I)^{-1} K_B^{1/2}|| )
       large g(classical || quantum) => classical kernel cannot reproduce quantum geometry
  * ESN-vs-ESN (different seed) control to calibrate what "large" means
"""
import numpy as np, time
from numpy.linalg import eigh, inv, norm
import volatility_data as vd
from vol_fair_benchmark import chimera_features, esn_features, LAGS

t0 = time.time()
rng_seed = 0

df = vd.load_spx_rv()
data = vd.build_supervised(df, horizon=1, lags=LAGS)
Xlag = data["X_lags"]; y = data["y_logrv"]
tr, te = vd.make_splits(len(y), train_frac=0.70)
lo, hi = Xlag[tr].min(0), Xlag[tr].max(0); rngd = np.where((hi - lo) == 0, 1, hi - lo)
Q = np.clip((Xlag - lo) / rngd, 0.0, 1.0)

# subsample train for stable, fast kernel ops (evenly spaced)
N = 800
idx = np.linspace(0, len(tr) - 1, N).astype(int)
trk = np.array(tr)[idx]
ytr = y[trk]; yc = ytr - ytr.mean()

def standardize(F):
    mu, sd = F.mean(0), F.std(0); sd = np.where(sd < 1e-8, 1.0, sd); return (F - mu) / sd

def lin_kernel(F):
    F = standardize(F); K = F @ F.T
    return K * (K.shape[0] / np.trace(K))   # trace-normalize to N

def eff_dim(K):
    w = np.clip(eigh(K)[0], 0, None); return (w.sum() ** 2) / ((w ** 2).sum() + 1e-12)

def num_rank(K, tol=1e-6):
    w = np.clip(eigh(K)[0], 0, None); return int((w > tol * w.max()).sum())

def kta(K, yv):
    n = K.shape[0]; H = np.eye(n) - np.ones((n, n)) / n
    Kc = H @ K @ H; Y = np.outer(yv, yv)
    return float((Kc * Y).sum() / (norm(Kc) * norm(Y) + 1e-12))

def geom_diff(KA, KB, reg=1e-3):
    n = KA.shape[0]
    wB, VB = eigh(KB); wB = np.clip(wB, 0, None); KBh = (VB * np.sqrt(wB)) @ VB.T
    M = KBh @ inv(KA + reg * np.eye(n)) @ KBh
    return float(np.sqrt(np.clip(eigh(M)[0], 0, None).max()))

# feature maps on the SAME inputs
FQ   = chimera_features(Q[trk], (2.0,), rng_seed)        # quantum, 36 features
F108 = esn_features(Q[trk], 108, rng_seed)               # classical, matched
F400 = esn_features(Q[trk], 400, rng_seed)               # classical, 4x
F108b= esn_features(Q[trk], 108, rng_seed + 1)           # ESN control (other seed)

KQ, K108, K400, K108b = map(lin_kernel, [FQ, F108, F400, F108b])

print("=" * 70)
print(f"Kernel geometry on Oxford-Man S&P500 RV  (N_train_subsample={N})")
print("=" * 70)
print(f"{'feature map':16s}{'#feat':>7}{'D_eff':>9}{'rank':>7}{'KTA(logRV)':>12}")
for nm, K, F in [("CHIMERA-1scale", KQ, FQ), ("ESN-108", K108, F108), ("ESN-400", K400, F400)]:
    print(f"{nm:16s}{F.shape[1]:>7}{eff_dim(K):>9.2f}{num_rank(K):>7}{kta(K, yc):>12.4f}")

print("\ngeometric difference  g(A || B)  [large => A cannot reproduce B]")
print(f"  g(ESN-108 || CHIMERA) = {geom_diff(K108, KQ):.3f}")
print(f"  g(ESN-400 || CHIMERA) = {geom_diff(K400, KQ):.3f}")
print(f"  g(ESN-108 || ESN-108') = {geom_diff(K108, K108b):.3f}   <- classical-vs-classical CONTROL")
print(f"  g(CHIMERA || ESN-108) = {geom_diff(KQ, K108):.3f}")
print(f"\nKTA-per-feature (efficiency): "
      f"CHIMERA {kta(KQ,yc)/FQ.shape[1]*1000:.3f}  vs  ESN-108 {kta(K108,yc)/108*1000:.3f}  "
      f"(x1e-3)")
print(f"[done in {time.time()-t0:.1f}s]")
