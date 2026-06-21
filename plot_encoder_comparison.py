"""
plot_encoder_comparison.py - overlay the univariate vs multivariate (H4) scaling
sweeps to show the input-bottleneck reversal: under the univariate 8-lag encoder g(n)
and the regime-transition MZ-gap COLLAPSE as qubits are added, while under the
multivariate realized-measure panel (added qubits carry new information) g(n) GROWS and
the MZ-gap recovers toward HAR parity.

Reads scaling_sweep_results.csv (univariate) and scaling_sweep_results_multivariate.csv.
Team EIGENNEXUS | GIC 2026 - Phase 3.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

u = pd.read_csv("scaling_sweep_results.csv").sort_values("n")
m = pd.read_csv("scaling_sweep_results_multivariate.csv").sort_values("n")

fig, ax = plt.subplots(1, 3, figsize=(14, 4.3))

ax[0].plot(u["n"], u["g"], "o-", lw=2, color="C3", label="univariate 8-lag")
ax[0].plot(m["n"], m["g"], "o-", lw=2, color="C0", label="multivariate panel (H4)")
ax[0].plot(u["n"], u["g_control"], "--", color="gray", alpha=.7, label="classical control")
ax[0].set_xlabel("qubit count n"); ax[0].set_ylabel("geometric difference g(n)")
ax[0].set_title("H0 curve 1: kernel distinctness g(n)\nunivariate collapses, H4 grows")
ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

ax[1].plot(u["n"], u["deff_chimera"], "o-", lw=2, color="C3", label="univariate")
ax[1].plot(m["n"], m["deff_chimera"], "o-", lw=2, color="C0", label="multivariate (H4)")
ax[1].set_xlabel("qubit count n"); ax[1].set_ylabel("kernel effective rank D_eff")
ax[1].set_title("Effective rank D_eff(n)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)

ax[2].axhline(0, color="k", lw=.8)
ax[2].plot(u["n"], u["mz_gap"], "o-", lw=2, color="C3", label="univariate")
ax[2].plot(m["n"], m["mz_gap"], "o-", lw=2, color="C0", label="multivariate (H4)")
ax[2].set_xlabel("qubit count n"); ax[2].set_ylabel("MZ-R²(CHIMERA) − MZ-R²(HAR)")
ax[2].set_title("H0 curve 2: regime-transition gap\nH4 halts the collapse (-0.25 -> -0.02)")
ax[2].legend(fontsize=8); ax[2].grid(alpha=.3)

fig.suptitle("CHIMERA-QRC Phase-3: H4 encoding-density reverses the input bottleneck "
             "(adding qubits that carry NEW information)", fontsize=11)
fig.tight_layout()
fig.savefig("figures/fig_encoder_comparison.png", dpi=130)
print("saved figures/fig_encoder_comparison.png")
print(f"univariate n: {list(u['n'])}  g: {[round(x,1) for x in u['g']]}  "
      f"mz_gap: {[round(x,3) for x in u['mz_gap']]}")
print(f"multivariate n: {list(m['n'])}  g: {[round(x,1) for x in m['g']]}  "
      f"mz_gap: {[round(x,3) for x in m['mz_gap']]}")
