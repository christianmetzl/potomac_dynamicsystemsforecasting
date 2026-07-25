# Noise fingerprint: coherent vs biased-incoherent error in the scrambled regime

*Readout-corrected re-analysis of the committed counts (no new hardware). Answers
whether the beyond-limit superconducting error is coherent (routing/unitary) or
biased-incoherent (amplitude damping / T1). Method and caveats in the module header.*

| campaign | regime | ground-state bias b | contraction a | affine R² | coherent-residual share |
|---|---|---|---|---|---|
| Rigetti (4k rep) | scrambled | -0.046 | 0.571 | 0.02 | 99% |
| Garnet (Camp. A) | scrambled | +0.156 | 0.228 | 0.01 | 87% |
| Garnet (anchor) | scrambled | +0.162 | 0.108 | 0.00 | 77% |
| Garnet (pair) | scrambled | +0.239 | 0.558 | 0.08 | 95% |
| IonQ Forte-1 | signal-bearing | -0.031 | 0.789 | 0.61 | 90% |
| Emerald | signal-bearing | +0.106 | 0.339 | 0.09 | 72% |
| Garnet n=10 | signal-bearing | +0.210 | -0.264 | 0.07 | 36% |

**Scrambled-regime summary:** mean ground-state bias b = +0.128, mean coherent-residual share = 90%.

**Reading.** A large positive `b` with high affine R² would mean amplitude damping /
readout bias (an *incoherent* channel) explains the beyond-limit error — in which case
'coherent scrambling' would be the wrong label. A `b` near zero with a large
coherent-residual share means no scalar shrink-and-bias reproduces the measured pattern:
the error is structured, consistent with coherent routing error. The measured values
above place each scrambled campaign on that spectrum; the paper's wording is set to
match what they show, and no headline verdict (which side of the limit) depends on this
attribution — that is fixed by the threshold test and hardened to 9.7–23.9σ by the
bootstrap (`results/qpu_bootstrap_ci.md`).
