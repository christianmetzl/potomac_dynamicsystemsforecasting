"""
make_coherence_wall_fig.py — render figures/fig_coherence_wall.png:
the cross-platform coherence-budget wall, one picture. Each bar is the measured mean raw
feature error on hardware; the black tick is that run's **instance-matched** fully-depolarized
limit (mean|F_exact| for that seeded reservoir — a property of the instance, not of n alone; the
seed-1 S7 bar therefore carries its own 0.1806 tick, not seed-0's 0.196).
Green = below the tick (device retains circuit signal); red = above (scrambled).
The adjacent Garnet n=8 seed-1 (S7, 0.159) vs seed-0 (0.228) pair refutes a size law — the n=8
scrambling is specific to the seed-0 instance. Rigetti bar = 0.223 (the 4k-shot replicate; the 2k
run was 0.261). All numbers trace to results/qpu_hardware_findings.md.
Colors/ticks are interpreted in the figure caption. All numbers trace to
results/qpu_hardware_findings.md. Regenerate: python3 make_coherence_wall_fig.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# (label, raw error, size-matched limit, signal_bearing)
bars = [
    ("IonQ Forte-1\nn=8 · ion",     0.104, 0.196, True),
    ("IQM Emerald\nn=8 · new gen",  0.169, 0.196, True),
    ("IQM Garnet\nn=10",            0.159, 0.179, True),
    ("IQM Garnet\nn=12",            0.190, 0.214, True),
    ("Garnet n=8\nseed-1 (S7)",     0.159, 0.1806, True),   # instance-matched limit (seed-1)
    ("Garnet n=8\nseed-0",          0.228, 0.196, False),
    ("Rigetti Cep-1\nn=8",          0.223, 0.196, False),
]
GREEN, RED, INK, GREY = "#2e8b57", "#c0392b", "#222222", "#888888"

fig, ax = plt.subplots(figsize=(10.6, 1.50))
for i, (lab, raw, lim, sig) in enumerate(bars):
    ax.bar(i, raw, width=0.66, color=(GREEN if sig else RED), alpha=0.9, zorder=3)
    ax.plot([i - 0.36, i + 0.36], [lim, lim], color=INK, lw=2.6, zorder=5)   # limit tick
    ax.text(i, raw - 0.012, f"{raw:.3f}", ha="center", va="top",
            fontsize=9.5, color="white", fontweight="bold", zorder=6)

ax.axvline(4.5, color=GREY, ls=":", lw=1.3, zorder=1)                        # regime divider
ax.text(2.0, 0.268, "signal-bearing", ha="center", fontsize=11, color=GREEN, fontweight="bold")
ax.text(5.5, 0.268, "scrambled", ha="center", fontsize=11, color=RED, fontweight="bold")

ax.set_xticks(range(len(bars)))
ax.set_xticklabels([b[0] for b in bars], fontsize=9)
ax.set_ylabel("raw feature error", fontsize=11)
ax.set_ylim(0, 0.29)
ax.set_yticks([0.0, 0.1, 0.196, 0.29])
ax.set_title("Cross-platform coherence-budget wall — hardware raw feature error vs the "
             "instance-matched depolarized limit (black tick)", fontsize=10.5)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.22, zorder=0)
plt.tight_layout()
plt.savefig("figures/fig_coherence_wall.png", dpi=150, bbox_inches="tight")
print("wrote figures/fig_coherence_wall.png")
