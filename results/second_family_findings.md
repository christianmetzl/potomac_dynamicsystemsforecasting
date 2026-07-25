# Second reservoir family — the negative is not Ising-specific

*Regenerate: `python3 second_family_robustness.py` (≈60 s, offline). Addresses the referee
question "is the no-advantage result a property of the transverse-field **Ising** reservoir, or
of the QRC approach at this scale?" We swap the reservoir Hamiltonian to **Heisenberg (XXZ)** —
`H = Σ J_ij (X_iX_j + Y_iY_j + Δ Z_iZ_j) + h Σ Z_i`, a genuinely different entangling dynamics —
and re-run the SAME decisive test (nested HAR-X readout, 8 seeds) and the SAME kernel diagnostic
on the SAME Oxford-Man S&P 500 RV data. Everything else identical to the headline pipeline.*

## Decisive forecasting test (RMSE log-RV, nested HAR-X readout, 8 seeds)

| model | RMSE(log-RV) | vs HAR-X |
|---|---|---|
| HAR (linear, HAR only) | 0.6454 | — |
| **HAR-X** (linear, lags+HAR) — the control to beat | **0.6417** | — |
| CHIMERA-**Ising** (nested) | 0.6548 ± 0.0051 | **+0.0131 — does not beat HAR-X** |
| CHIMERA-**Heisenberg** (nested) | 0.6500 ± 0.0099 | **+0.0084 — does not beat HAR-X** |

## Kernel distinctness (Huang et al. 2021 geometric difference g)

| reservoir | g(ESN-108 ‖ ·) | KTA/feature (×10⁻³) |
|---|---|---|
| classical-vs-classical control | 3.75 | — |
| CHIMERA-**Ising** | 63.6 | 6.87 vs ESN 5.45 |
| CHIMERA-**Heisenberg** | 55.4 | 7.06 vs ESN 5.45 |

## Verdict
Both families are **kernel-distinct** from a matched classical reservoir (g ≈ 55–64, ~15× the
classical control), yet **neither beats HAR-X** on the decisive forecasting test. A genuinely
different entangling Hamiltonian reproduces the headline pattern exactly: *distinct but not more
accurate*. **The no-advantage negative is therefore a property of the unitary-QRC approach at
simulable scale, not of the specific transverse-field Ising reservoir** — closing the "you just
picked a weak Hamiltonian" objection. (Heisenberg is marginally closer to HAR-X than Ising but
still loses and still shows no significant edge; reported as measured.)
