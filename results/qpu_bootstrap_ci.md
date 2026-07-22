# Shot-noise bootstrap CIs for the hardware campaigns

*Multinomial bootstrap (B=1000) from the committed per-window counts of each
campaign - a pure re-analysis of platform-verifiable data, zero new hardware.
The CI quantifies shot noise only; day-scale drift (~0.04, measured by
replication) is the separate, larger uncertainty for cross-day point values.
The original Rigetti run predates the checkpoint system (counts not committed)
and is excluded; its 4k-shot replication is covered. Engine self-check: the
size-matched depolarized limit equals mean|F_exact| recomputed per n (asserted).*

| campaign | n | shots | raw | 95% CI | limit | claimed side | margin (sigma) |
|---|---|---|---|---|---|---|---|
| IonQ Forte-1 (native) | 8 | 500 | 0.1042 | [0.1010, 0.1208] | 0.1958 | below | +0.0916 (18.0sigma) |
| IQM Emerald | 8 | 4000 | 0.1793 | [0.1762, 0.1830] | 0.1958 | below | +0.0165 (9.7sigma) |
| IQM Emerald (same-window) | 8 | 4000 | 0.1690 | [0.1660, 0.1725] | 0.1958 | below | +0.0268 (15.6sigma) |
| IQM Garnet n=10 | 10 | 4000 | 0.1590 | [0.1565, 0.1620] | 0.1790 | below | +0.0200 (14.0sigma) |
| IQM Garnet n=12 | 12 | 4000 | 0.1897 | [0.1876, 0.1923] | 0.2140 | below | +0.0243 (20.4sigma) |
| IQM Garnet (Campaign A) | 8 | 4000 | 0.2301 | [0.2272, 0.2334] | 0.1958 | above | +0.0343 (22.0sigma) |
| IQM Garnet (anchor) | 8 | 4000 | 0.2216 | [0.2190, 0.2247] | 0.1958 | above | +0.0258 (18.0sigma) |
| IQM Garnet (same-window) | 8 | 4000 | 0.2307 | [0.2279, 0.2337] | 0.1958 | above | +0.0349 (23.9sigma) |
| Rigetti Cepheus-1 (4k rep) | 8 | 4000 | 0.2226 | [0.2196, 0.2260] | 0.1958 | above | +0.0268 (16.2sigma) |

**Verdict: every regime claim in the paper's cross-platform table holds far
beyond shot noise** - the smallest margin across all nine campaigns is listed
above; no claim is within its 95% interval of the limit.
