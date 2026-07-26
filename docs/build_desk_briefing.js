#!/usr/bin/env node
/* Builds docs/EIGENNEXUS_desk_briefing.pptx — the customer-facing briefing deck for a first
 * desk conversation about the CHIMERA-QRC audit instrument.
 *
 * Every number on these slides is settled ledger or committed measurement; the sources are
 * results/AUDIT_ECONOMICS.md, results/CREDIT_BUDGET.md and results/qpu_hardware_findings.md.
 * The deck states explicitly that no customer engagements exist. Rebuild: node docs/build_desk_briefing.js
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(__dirname, "EIGENNEXUS_desk_briefing.pptx");

const NAVY = "1B2A4A";      // dominant
const INK = "22314F";       // body text on light
const MUTE = "5A6B8C";      // secondary text
const ICE = "CADCFC";       // secondary tone on dark
const PAPER = "FFFFFF";
const CARD = "F1F5FC";      // light card tint
const AMBER = "D97A1A";     // single accent: caution / scrambled
const TEAL = "1F7A6D";      // verdict green-adjacent (colorblind-safer than pure green)

const HFONT = "Cambria";
const BFONT = "Calibri";
const MFONT = "Courier New";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5

function chip(slide, x, y, text, color, w) {
  slide.addShape("roundRect", { x, y, w: w, h: 0.34, rectRadius: 0.17, fill: { color } });
  slide.addText(text, { x, y, w: w, h: 0.34, align: "center", fontFace: BFONT, fontSize: 10.5,
    bold: true, color: "FFFFFF", margin: 0 });
}

function kicker(slide, text) {
  slide.addText(text, { x: 0.6, y: 0.42, w: 12.1, h: 0.3, fontFace: BFONT, fontSize: 12,
    bold: true, color: MUTE, charSpacing: 2, margin: 0 });
}

function title(slide, text, opts = {}) {
  slide.addText(text, { x: 0.6, y: 0.72, w: 12.1, h: 0.85, fontFace: HFONT, fontSize: 30,
    bold: true, color: opts.color || NAVY, margin: 0 });
}

/* ---------------- Slide 1 — title (dark) ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("EIGENNEXUS  ·  CHIMERA-QRC  ·  GIC 2026 TRACK A  ·  FINANCIAL VOLATILITY", {
    x: 0.7, y: 0.8, w: 12, h: 0.32, fontFace: BFONT, fontSize: 12.5, bold: true, color: ICE,
    charSpacing: 2, margin: 0 });
  s.addText("Is your quantum pilot buying signal — or noise?", {
    x: 0.7, y: 2.05, w: 11.9, h: 1.7, fontFace: HFONT, fontSize: 43, bold: true, color: PAPER,
    margin: 0 });
  s.addText("A procurement-grade audit instrument for QPU claims. Every number in this deck is a settled ledger entry or a committed measurement, re-derivable offline with one command and no API key.", {
    x: 0.7, y: 3.85, w: 10.6, h: 0.95, fontFace: BFONT, fontSize: 16.5, color: ICE, margin: 0 });
  chip(s, 0.7, 5.15, "SIGNAL-BEARING", TEAL, 1.85);
  chip(s, 2.65, 5.15, "SCRAMBLED", AMBER, 1.55);
  s.addText("The two verdicts this instrument issues — each carried at 9.7–23.9σ from committed raw counts.", {
    x: 4.45, y: 5.13, w: 8.0, h: 0.38, fontFace: BFONT, fontSize: 11.5, italic: true, color: ICE,
    margin: 0 });
  s.addText("Prepared as the briefing we would bring to a first desk conversation. No customer engagements exist yet — that status is stated on every slide where it matters.", {
    x: 0.7, y: 6.55, w: 11.9, h: 0.55, fontFace: BFONT, fontSize: 11, italic: true, color: "8FA6CE",
    margin: 0 });
  s.addNotes("Positioning: not a trading model, an audit instrument. The honesty markers (no engagements, re-derivable numbers) are the differentiator, not disclaimers.");
}

/* ---------------- Slide 2 — the silent failure mode ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "THE PROBLEM");
  title(s, "Quantum hardware returns numbers either way");
  s.addText([
    { text: "Desks are being offered quantum volatility pilots today. The failure mode is silent: a QPU job that has lost all input information still returns a complete, numerically plausible feature vector.", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "Nothing in the output format distinguishes signal from noise. The distinction requires a measured reference — per device, per configuration, per problem instance.", options: { breakLine: true, paraSpaceAfter: 10 } },
    { text: "Our test is one inequality: is the mean measured error smaller than the mean signal the features are supposed to carry (SNR > 1)?", options: {} },
  ], { x: 0.6, y: 1.75, w: 5.9, h: 3.6, fontFace: BFONT, fontSize: 15, color: INK, margin: 0 });

  // two comparison cards
  const cardY = 1.85, cardH = 3.3;
  s.addShape("roundRect", { x: 6.9, y: cardY, w: 2.85, h: cardH, rectRadius: 0.12, fill: { color: CARD } });
  s.addText("IonQ Forte-1, n=8", { x: 7.1, y: cardY + 0.25, w: 2.45, h: 0.3, fontFace: BFONT, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  s.addText("0.104", { x: 7.1, y: cardY + 0.62, w: 2.45, h: 0.85, fontFace: HFONT, fontSize: 40, bold: true, color: TEAL, margin: 0 });
  s.addText("mean error vs limit 0.196 — about half the noise ceiling", { x: 7.1, y: cardY + 1.55, w: 2.45, h: 0.75, fontFace: BFONT, fontSize: 11, color: MUTE, margin: 0 });
  chip(s, 7.1, cardY + 2.6, "SIGNAL-BEARING", TEAL, 1.85);

  s.addShape("roundRect", { x: 10.0, y: cardY, w: 2.85, h: cardH, rectRadius: 0.12, fill: { color: CARD } });
  s.addText("IQM Garnet, n=8", { x: 10.2, y: cardY + 0.25, w: 2.45, h: 0.3, fontFace: BFONT, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  s.addText("0.228", { x: 10.2, y: cardY + 0.62, w: 2.45, h: 0.85, fontFace: HFONT, fontSize: 40, bold: true, color: AMBER, margin: 0 });
  s.addText("mean error vs limit 0.196 — beyond the fully-depolarized state", { x: 10.2, y: cardY + 1.55, w: 2.45, h: 0.75, fontFace: BFONT, fontSize: 11, color: MUTE, margin: 0 });
  chip(s, 10.2, cardY + 2.6, "SCRAMBLED", AMBER, 1.55);

  s.addText("Both jobs completed. Both returned 36 features. Both invoices settled. Only the audit tells them apart — the second would have entered a model pipeline as data.", {
    x: 0.6, y: 5.7, w: 12.2, h: 0.75, fontFace: BFONT, fontSize: 14.5, italic: true, color: NAVY, margin: 0 });
  s.addNotes("Numbers: IonQ raw 0.1042 vs seed-0 n=8 limit 0.1958; Garnet anchor raw 0.2284. Sources: results/qpu_hardware_findings.md.");
}

/* ---------------- Slide 3 — the instrument ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "THE INSTRUMENT");
  title(s, "Instance-matched depolarized limits, verdicts in σ");
  const rows = [
    ["1", "Compute the floor", "For the exact circuit and problem instance you run, compute mean |signal| — the error a fully-scrambled device would show. This is the depolarized limit: an instance property, not a device spec."],
    ["2", "Measure against it", "Run the identical circuit on metal with calibration, readout mitigation and ZNE. Score mean measured error against the limit — signal-bearing below it, scrambled at or beyond it."],
    ["3", "Attach confidence", "Bootstrap the verdict from the committed raw shot counts. Across our nine campaigns with committed counts, every verdict sits 9.7–23.9σ from its threshold."],
  ];
  rows.forEach((r, i) => {
    const y = 1.8 + i * 1.05;
    s.addShape("ellipse", { x: 0.6, y: y + 0.03, w: 0.52, h: 0.52, fill: { color: NAVY } });
    s.addText(r[0], { x: 0.6, y: y + 0.03, w: 0.52, h: 0.52, align: "center", fontFace: HFONT, fontSize: 18, bold: true, color: PAPER, margin: 0 });
    s.addText(r[1], { x: 1.35, y: y, w: 3.1, h: 0.55, fontFace: BFONT, fontSize: 15.5, bold: true, color: NAVY, margin: 0 });
    s.addText(r[2], { x: 4.5, y: y - 0.05, w: 8.3, h: 1.0, fontFace: BFONT, fontSize: 12.5, color: INK, margin: 0 });
  });
  s.addImage({ path: path.join(ROOT, "figures", "fig_coherence_wall.png"), x: 0.6, y: 5.2, w: 12.13, h: 1.6 });
  s.addText("The coherence-budget wall across our hardware program: five configurations signal-bearing, two scrambled, each against its own instance-matched limit (black ticks). Figure committed in the Phase-3 paper.", {
    x: 0.6, y: 6.9, w: 12.1, h: 0.4, fontFace: BFONT, fontSize: 10, italic: true, color: MUTE, margin: 0 });
  s.addNotes("The wall figure is Figure 3 of PHASE3_PAPER.pdf, regenerated by make_coherence_wall_fig.py from committed results.");
}

/* ---------------- Slide 4 — evidence ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "EVIDENCE");
  title(s, "Proven on paid metal, against our own predictions");
  const stats = [
    ["13", "provenance-tagged QPU campaigns", "10 org-funded + 3 free-credit, every job ID committed"],
    ["3 / 4", "vendors / devices", "IonQ Forte-1, IQM Garnet & Emerald, Rigetti Cepheus-1"],
    ["9.7–23.9σ", "confidence per regime verdict", "multinomial bootstrap from committed raw counts"],
    ["4", "of our own pre-registered predictions falsified", "committed thresholds first, hardware second, verdicts as measured"],
  ];
  stats.forEach((t, i) => {
    const x = 0.6 + (i % 2) * 6.25, y = 1.85 + Math.floor(i / 2) * 2.15;
    s.addShape("roundRect", { x, y, w: 5.95, h: 1.95, rectRadius: 0.12, fill: { color: CARD } });
    s.addText(t[0], { x: x + 0.3, y: y + 0.18, w: 5.4, h: 0.8, fontFace: HFONT, fontSize: 37, bold: true, color: NAVY, margin: 0 });
    s.addText(t[1], { x: x + 0.3, y: y + 1.0, w: 5.4, h: 0.4, fontFace: BFONT, fontSize: 14, bold: true, color: INK, margin: 0 });
    s.addText(t[2], { x: x + 0.3, y: y + 1.4, w: 5.4, h: 0.45, fontFace: BFONT, fontSize: 11.5, color: MUTE, margin: 0 });
  });
  s.addText("Also in the record: two reproducible platform findings reported upstream, a matched-pair device-outage control, and one mechanism question (H-EMBED) pre-registered, execute-ready and honestly open.", {
    x: 0.6, y: 6.35, w: 12.2, h: 0.6, fontFace: BFONT, fontSize: 12.5, italic: true, color: MUTE, margin: 0 });
  s.addNotes("Falsified: S1, S2, S3b, S7 cross-seed. Sources: results/qpu_hardware_findings.md, results/h_embed_outcome.md.");
}

/* ---------------- Slide 5 — economics ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "THE ECONOMICS — MEASURED, NOT MODELLED");
  title(s, "What the audit costs vs. what it catches");
  // left: cost card
  s.addShape("roundRect", { x: 0.6, y: 1.8, w: 5.95, h: 2.6, rectRadius: 0.12, fill: { color: CARD } });
  s.addText("The audit cost us", { x: 0.9, y: 2.0, w: 5.3, h: 0.35, fontFace: BFONT, fontSize: 13.5, bold: true, color: MUTE, margin: 0 });
  s.addText("≈ $650", { x: 0.9, y: 2.35, w: 5.3, h: 0.85, fontFace: HFONT, fontSize: 44, bold: true, color: NAVY, margin: 0 });
  s.addText("entire 13-campaign, 4-device program (64,048.25 cr settled, at the ≈$14 / 1,380 cr rate we measurably paid). One device: $23–$213. Re-running every verdict offline: $0.", {
    x: 0.9, y: 3.25, w: 5.35, h: 1.0, fontFace: BFONT, fontSize: 12, color: INK, margin: 0 });
  // right: caught card
  s.addShape("roundRect", { x: 6.85, y: 1.8, w: 5.95, h: 2.6, rectRadius: 0.12, fill: { color: CARD } });
  s.addText("It flagged, on our own budget", { x: 7.15, y: 2.0, w: 5.3, h: 0.35, fontFace: BFONT, fontSize: 13.5, bold: true, color: MUTE, margin: 0 });
  s.addText("29.3%", { x: 7.15, y: 2.35, w: 5.3, h: 0.85, fontFace: HFONT, fontSize: 44, bold: true, color: AMBER, margin: 0 });
  s.addText("of settled hardware spend — four campaigns, 18,793.25 cr ≈ $191 — returned plausible-looking features the instrument flagged as scrambled at ≥9.7σ. Five other configurations it certified signal-bearing on the same footing.", {
    x: 7.15, y: 3.25, w: 5.35, h: 1.0, fontFace: BFONT, fontSize: 12, color: INK, margin: 0 });
  // table
  const tbl = [
    [
      { text: "your pilot budget", options: { bold: true, color: PAPER, fill: { color: NAVY } } },
      { text: "full 4-device audit (≈$650)", options: { bold: true, color: PAPER, fill: { color: NAVY } } },
      { text: "single-device audit (≈$69)", options: { bold: true, color: PAPER, fill: { color: NAVY } } },
    ],
    ["$50,000", "1.3%", "0.14%"],
    ["$250,000", "0.26%", "0.028%"],
    ["$1,000,000", "0.065%", "0.007%"],
  ];
  s.addTable(tbl, { x: 0.6, y: 4.75, w: 12.2, colW: [4.0, 4.1, 4.1], fontFace: BFONT, fontSize: 13,
    color: INK, align: "center", valign: "middle", rowH: 0.42,
    border: { type: "solid", color: "D5DEEF", pt: 1 } });
  s.addText("We do not know your pilot budget — this table is division, not a forecast. The asymmetry is the argument: the audit is a rounding error of any serious pilot; the failure it prevents costs the pilot.", {
    x: 0.6, y: 6.7, w: 12.2, h: 0.55, fontFace: BFONT, fontSize: 12, italic: true, color: NAVY, margin: 0 });
  s.addNotes("All figures from results/AUDIT_ECONOMICS.md; ledger reconciles to the cent via cli.py run credit_audit.");
}

/* ---------------- Slide 6 — the pilot offer ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "THE CONVERSATION WE ARE ASKING FOR");
  title(s, "A two-week pilot, unpaid, on your workload");
  const steps = [
    ["Week 1", "Your instance, our floor", "We take one volatility workload from your desk, encode it with the committed protocol, and compute its instance-matched depolarized limits — before any hardware is bought."],
    ["Week 2", "Metal, mitigated, measured", "We execute the audited configurations on the shortlisted QPUs (typical cost per device: $23–$213 at the rates we paid), with calibration, readout mitigation, ZNE and committed abort rules."],
    ["Output", "Three deliverables", "A per-device/config SNR verdict with σ. A to-the-cent cost ledger. A written go/no-go memo you can hand to procurement — whichever way the verdict falls."],
  ];
  steps.forEach((r, i) => {
    const y = 1.85 + i * 1.35;
    s.addShape("roundRect", { x: 0.6, y, w: 1.7, h: 1.1, rectRadius: 0.1, fill: { color: NAVY } });
    s.addText(r[0], { x: 0.6, y, w: 1.7, h: 1.1, align: "center", fontFace: HFONT, fontSize: 16, bold: true, color: PAPER, margin: 0 });
    s.addText(r[1], { x: 2.55, y: y + 0.02, w: 3.6, h: 0.5, fontFace: BFONT, fontSize: 15.5, bold: true, color: NAVY, margin: 0 });
    s.addText(r[2], { x: 6.25, y: y - 0.03, w: 6.55, h: 1.2, fontFace: BFONT, fontSize: 12.5, color: INK, margin: 0 });
  });
  chip(s, 0.6, 6.15, "OPEN OFFER", AMBER, 1.5);
  s.addText("Status, stated plainly: no customer engagements, pilots or LOIs exist today. This slide is the offer, not a track record.", {
    x: 2.25, y: 6.13, w: 10.5, h: 0.4, fontFace: BFONT, fontSize: 12.5, italic: true, color: INK, margin: 0 });
  s.addNotes("The honesty chip is deliberate: the deck must never be quotable as claiming traction that does not exist.");
}

/* ---------------- Slide 7 — what this does not do ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: PAPER };
  kicker(s, "LIMITS — READ THIS SLIDE FIRST IF YOU READ ONLY ONE");
  title(s, "What this instrument does not do");
  const items = [
    ["No alpha claim.", "On our own benchmark the classical HAR-X baseline won: 0 of 30 quantum reservoir instances beat it on crisis and calm windows simultaneously. We report that as headline, not footnote."],
    ["No future-proofing.", "A verdict is per device, per configuration, per instance, per day. It prices today's hardware against your workload; it does not predict next year's."],
    ["No independent replication yet.", "Every audit so far is our own. The verification path is designed for third parties (offline, no key, one command) — but until someone outside the team runs it, that box is unchecked."],
    ["Two platform findings await vendor confirmation.", "Both reported upstream with committed reproduction scripts; both labelled as our observations until confirmed."],
  ];
  items.forEach((r, i) => {
    const y = 1.85 + i * 1.15;
    s.addShape("ellipse", { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fill: { color: AMBER } });
    s.addText("!", { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, align: "center", fontFace: HFONT, fontSize: 16, bold: true, color: PAPER, margin: 0 });
    s.addText([
      { text: r[0] + "  ", options: { bold: true, color: NAVY } },
      { text: r[1], options: { color: INK } },
    ], { x: 1.25, y: y - 0.05, w: 11.5, h: 1.05, fontFace: BFONT, fontSize: 13.5, margin: 0 });
  });
  s.addNotes("Sources: expressivity_vs_accuracy.py (0/30), qpu_hardware_findings.md, platform_feedback_qbraid.md, h_embed_outcome.md.");
}

/* ---------------- Slide 8 — verify (dark) ---------------- */
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("VERIFY IT YOURSELF — NOTHING IN THIS DECK REQUIRES TRUSTING US", {
    x: 0.7, y: 0.6, w: 12, h: 0.35, fontFace: BFONT, fontSize: 13, bold: true, color: ICE, charSpacing: 2, margin: 0 });
  s.addText("Three minutes, offline, no account", {
    x: 0.7, y: 1.15, w: 12, h: 0.8, fontFace: HFONT, fontSize: 33, bold: true, color: PAPER, margin: 0 });
  s.addShape("roundRect", { x: 0.7, y: 2.25, w: 11.9, h: 2.05, rectRadius: 0.1, fill: { color: "10203C" } });
  s.addText([
    { text: "unzip EIGENNEXUS_Challenge_Phase3.zip && cd EIGENNEXUS_Challenge_Phase3", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "python3 cli.py verify     # 24 engine tests + QASM self-test + credit audit", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "                          # + bootstrap CIs + noise fingerprint - all offline", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "python3 build_paper.py    # regenerates the Phase-3 paper byte-for-source", options: {} },
  ], { x: 1.0, y: 2.45, w: 11.3, h: 1.7, fontFace: MFONT, fontSize: 13.5, color: ICE, margin: 0 });
  s.addText([
    { text: "Every job ID, raw count, credit entry and verdict is committed in the repository. The audit run of 2026-07-26 extracted this exact zip into a clean directory with no API key and every check passed.", options: { breakLine: true, paraSpaceAfter: 8 } },
    { text: "Team EIGENNEXUS — GIC 2026 (qBraid · MITRE · JonesTrading), Track A. Repository: github.com/christianmetzl/potomac_dynamicsystemsforecasting", options: {} },
  ], { x: 0.7, y: 4.7, w: 11.9, h: 1.5, fontFace: BFONT, fontSize: 13.5, color: ICE, margin: 0 });
  chip(s, 0.7, 6.45, "SIGNAL-BEARING", TEAL, 1.85);
  s.addText("— the verdict we want this deck to earn.", {
    x: 2.65, y: 6.43, w: 9.9, h: 0.38, fontFace: BFONT, fontSize: 12, italic: true, color: "8FA6CE", margin: 0 });
  s.addNotes("Close on verifiability: the deck's claims are the repo's claims.");
}

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote " + OUT));
