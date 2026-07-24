# Recency robustness — the honest negative holds on data through mid-2026

*Addresses the obvious "your RV sample ends Feb-2020" objection. The paper's 5-min RV headline
is Oxford-Man (ends 2020, library discontinued); here we apply the **pre-registered decisive-test
methodology** (adversarial fair baselines HAR-X-cross / recurrent-ESN / RFF, HAC-corrected
Diebold–Mariano, Holm across targets) to a **daily-proxy** cross-asset panel running to
**2026-06-01**. Honest scope: this is a daily-proxy robustness check, not 5-min RV; the
methodology was pre-registered, the recent-window outcome was not — it is reported as a
confirmatory robustness result. Reproduce:
`python3 v2_research/v2_cross_asset.py --panel cross_asset_panel_massive_etf.npz --train-end 2024-06-01`.*

## Result (panel 2021-06-28 … 2026-06-01, train through 2024-06-01)

| target | HAR-X-cross RMSE (best) | CHIMERA RMSE | CHIMERA vs HAR-X-cross (DM, Holm p) |
|---|---|---|---|
| SPY | **0.8311** | 0.8517 | +2.42, Holm p=0.022 → **significantly worse** |
| QQQ | **0.8132** | 0.8434 | +3.53, Holm p=0.001 → **significantly worse** |
| TLT | **0.6798** | 0.7029 | +2.56, Holm p=0.022 → **significantly worse** |

**Verdict: HAR-X-cross (classical, linear) is best on every target through mid-2026; the quantum
reservoir is significantly worse (Holm-adjusted), not better.** The recurrent ESN and RFF are
also beaten by HAR-X-cross. The negative documented on 2000–2020 5-min RV in the paper is
**not an artifact of a stale sample** — it reproduces on out-of-sample daily data spanning the
2022 rate-hike selloff and the 2024–25 regimes.

This strengthens, rather than changes, the paper's conclusion: at simulable scale, across
assets, metrics, architectures, **and now recent periods**, the decision-useful lever remains a
simple classical RV forecast, not the quantum reservoir. (Full multi-period supporting studies:
`v2_research/V2_README.md`; the same-negative daily-proxy panels also cover 2006–2022 incl. COVID.)
