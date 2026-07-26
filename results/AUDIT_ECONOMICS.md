# The audit instrument, in dollars

*One page. Every number below is settled ledger or committed measurement — re-derivable offline
with `python3 cli.py verify` (no API key, no credits). Conversion rate: the only rate we measurably
paid, ≈$14 for ≈1,380 credits on the personal tier (`results/CREDIT_BUDGET.md`); challenge-granted
org credits may be priced differently, so dollar figures are stated at that observed rate.*

## What the instrument is

A QPU run returns numbers whether or not they carry signal. The instrument scores every measured
feature vector against its **instance-matched fully-depolarized limit**: mean measured error below
mean |signal| (SNR > 1) → **signal-bearing**; at or beyond the limit → **scrambled** — statistically
indistinguishable from noise. Verdicts carry multinomial-bootstrap confidence from the committed raw
counts: **9.7–23.9σ** across the nine campaigns with committed counts.

## What the audit cost — measured

| item | settled | ≈ USD |
|---|---:|---:|
| Entire 13-campaign hardware program (3 vendors, 4 devices) | 64,048.25 cr | **≈$650** |
| One device, full protocol (cheapest → dearest: Rigetti / Garnet / Emerald / IonQ) | 2,234.25 – 20,980 cr | **$23 – $213** |
| Re-running the verdicts from committed counts (`cli.py verify`) | 0 | **$0, offline** |

## What it caught — measured, on our own budget

- **29.3% of settled hardware spend — 18,793.25 cr ≈ $191 across four campaigns** (Garnet n=8
  Campaign A, anchor, pair; Rigetti replicate) — returned numerically plausible feature vectors that
  the instrument flagged as **beyond the depolarized limit** (scrambled), at ≥9.7σ. Without the
  gate, those features enter a model pipeline as data. That is the wrong go-decision in miniature,
  measured on our own ledger.
- The gate is not a nay-machine: **five configurations were certified signal-bearing** on the same
  σ footing (IonQ n=8, Emerald n=8, Garnet n=10/n=12, Garnet n=8 seed-1).
- The committed abort rules did the same job at submission time: the H-EMBED attempt stopped after
  ~0.5 OQ credits of probes rather than submitting a ~40-credit campaign into a device that was
  silently swallowing jobs (`results/h_embed_outcome.md`).

## The go/no-go arithmetic

We do not know your pilot budget, so the table is division, not a forecast:

| your pilot budget | full 4-device audit (≈$650) | single-device audit (≈$69) |
|---:|---:|---:|
| $50,000 | 1.3% | 0.14% |
| $250,000 | 0.26% | 0.028% |
| $1,000,000 | 0.065% | 0.007% |

The asymmetry is the argument: the audit costs a rounding error of any serious pilot, and the
failure mode it prevents — building on scrambled features that look like data — costs the pilot.

## Status, stated plainly

**No customer engagements, pilots, or LOIs exist.** The offer we would bring to a desk: a two-week
unpaid pilot — your volatility workload, our instrument, three deliverables (per-device/config
SNR verdict with σ, a to-the-cent cost ledger, a written go/no-go memo). The harness, protocol,
abort rules, and verification path in this repository are the pilot kit, unchanged.
