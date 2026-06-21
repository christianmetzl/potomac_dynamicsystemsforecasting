"""
plot_encoder_comparison.py - overlay the univariate vs multivariate (H4) scaling
sweeps to show the input-bottleneck reversal: under the univariate 8-lag encoder g(n)
and the regime-transition MZ-gap COLLAPSE as qubits are added, while under the
multivariate realized-measure panel (added qubits carry new information) g(n) GROWS and
the MZ-gap recovers toward HAR parity.

Reads scaling_sweep_results.csv (univariate) and scaling_sweep_results_multivariate.csv.
Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

u = pd.read_csv("scaling_sweep_results.csv").sort_values("n")
m = pd.read_csv("scaling_sweep_results_multivariate.csv").sort_values("n")
RU = "scaling_sweep_results_multivariate_reupload.csv"
r = pd.read_csv(RU).sort_values("n") if os.path.exists(RU) else None

def add(ax, df, col, color, label, marker="o-"):
    if df is not None:
        ax.plot(df["n"], df[col], marker, lw=2, color=color, label=label)

fig, ax = plt.subplots(1, 3, figsize=(14, 4.3))

add(ax[0], u, "g", "C3", "univariate 8-lag")
add(ax[0], m, "g", "C0", "multivariate R=1 (H4)")
add(ax[0], r, "g", "C2", "multivariate R=2 (re-upload)")
ax[0].plot(u["n"], u["g_control"], "--", color="gray", alpha=.7, label="classical control")
ax[0].set_xlabel("qubit count n"); ax[0].set_ylabel("geometric difference g(n)")
ax[0].set_title("H0 curve 1: kernel distinctness g(n)\nnew info (width/depth) lifts g; univariate collapses")
ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

add(ax[1], u, "deff_chimera", "C3", "univariate")
add(ax[1], m, "deff_chimera", "C0", "multivariate R=1")
add(ax[1], r, "deff_chimera", "C2", "multivariate R=2")
ax[1].set_xlabel("qubit count n"); ax[1].set_ylabel("kernel effective rank D_eff")
ax[1].set_title("Effective rank D_eff(n)\nre-uploading ~doubles D_eff"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

ax[2].axhline(0, color="k", lw=.8)
add(ax[2], u, "mz_gap", "C3", "univariate")
add(ax[2], m, "mz_gap", "C0", "multivariate R=1")
add(ax[2], r, "mz_gap", "C2", "multivariate R=2")
ax[2].set_xlabel("qubit count n"); ax[2].set_ylabel("MZ-R²(CHIMERA) − MZ-R²(HAR)")
ax[2].set_title("H0 curve 2: regime-transition gap\nstill the hard, unsolved objective (<=0)")
ax[2].legend(fontsize=8); ax[2].grid(alpha=.3)

fig.suptitle("CHIMERA-QRC Phase-3 H4: encoding density (width + re-uploading depth) controls "
             "distinctness; the regime-transition gap remains the open scale question", fontsize=10)
fig.tight_layout()
fig.savefig("figures/fig_encoder_comparison.png", dpi=130)
print("saved figures/fig_encoder_comparison.png")
print(f"univariate n: {list(u['n'])}  g: {[round(x,1) for x in u['g']]}  "
      f"mz_gap: {[round(x,3) for x in u['mz_gap']]}")
print(f"multivariate n: {list(m['n'])}  g: {[round(x,1) for x in m['g']]}  "
      f"mz_gap: {[round(x,3) for x in m['mz_gap']]}")
