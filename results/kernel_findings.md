# Kernel geometry (quantum kernel distinctness) — committed artifact

*Regenerate exactly: `python3 cli.py run kernel`. Oxford-Man S&P500 RV, N_train_subsample=800,
fixed ridge regularization. This file pins the g-values quoted in `PHASE3_PAPER.md` §3,
`README.md`, and `SKILL.md` so the number traces to a committed source, not inline text.*

## Measured geometric difference g(A ‖ B) — Huang et al. 2021
*(large g ⇒ reservoir A cannot reproduce reservoir B's kernel)*

| pair | g | reading |
|---|---|---|
| g(ESN-108 ‖ CHIMERA) | **63.57** | the name-matched classical ESN cannot reproduce the quantum kernel |
| g(ESN-400 ‖ CHIMERA) | 55.57 | still large against a 4× larger ESN |
| **g(ESN-108 ‖ ESN-108′)** | **3.746** | **classical-vs-classical control** — the reproducibility floor |
| g(CHIMERA ‖ ESN-108) | 171.28 | (reverse direction) |

**Headline pair used in the paper:** g(ESN→CHIMERA) ≈ **64** vs the ≈ **3.7** classical control
— a ~17× separation at this configuration.

## Per-reservoir summary
| reservoir | features | eff. rank | KTA×10³ |
|---|---|---|---|
| CHIMERA-1scale | 36 | 1.80 | 6.874 |
| ESN-108 | 108 | 3.37 | 5.450 |
| ESN-400 | 400 | 3.45 | — |

## Honest scope (unchanged from the paper)
g is measured at **fixed ridge regularization** and is **configuration-dependent**; the claim is
the **qualitative ~15–40× separation** between the quantum kernel and the classical-vs-classical
control, **not** the exact value. Distinctness is **necessary, not sufficient** for a forecasting
advantage — and the decisive test (`axisB_rigorous_findings.md`) shows it does **not** convert to
accuracy at simulable scale. This artifact documents the distinctness property only.
