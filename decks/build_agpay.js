const PptxGenJS = require("pptxgenjs");
const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pptx.author = "AgPay";
pptx.title = "AgPay — Investor Deck";

// ---- AgPay brand palette (from the live site) ----
const BG = "07100D", CARD = "0C1913", CARD2 = "0F2018";
const MINT = "87F7C3", LIME = "D8FF79", GOLD = "F4C95D", TEAL = "5DD6C6";
const TEXT = "F3F7EF", MUTED = "9AA3AF", BORDER = "24382E", ONACC = "06100C";
const HF = "Segoe UI Semibold", BF = "Segoe UI";
const W = 13.33, H = 7.5;

function grid(s) {
  for (let x = 0.74; x < W; x += 0.74)
    s.addShape(pptx.ShapeType.line, { x, y: 0, w: 0, h: H, line: { color: "0C1A13", width: 0.5 } });
  for (let y = 0.74; y < H; y += 0.74)
    s.addShape(pptx.ShapeType.line, { x: 0, y, w: W, h: 0, line: { color: "0C1A13", width: 0.5 } });
}
function bg(s) { s.background = { color: BG }; grid(s); }
function mark(s, x, y, d = 0.16, gap = 0.24) {
  [MINT, LIME, GOLD].forEach((c, i) =>
    s.addShape(pptx.ShapeType.ellipse, { x: x + i * gap, y, w: d, h: d, fill: { color: c }, line: { type: "none" } }));
}
function kicker(s, t) {
  s.addText(t.toUpperCase(), { x: 0.7, y: 0.5, w: 11, h: 0.3, fontFace: HF, fontSize: 12, bold: true, color: MINT, charSpacing: 3 });
}
function title(s, t, o = {}) {
  s.addText(t, { x: 0.7, y: o.y || 0.82, w: o.w || 11.9, h: o.h || 1.0, fontFace: HF, fontSize: o.fs || 29, bold: true, color: TEXT, lineSpacingMultiple: 1.0 });
}
function card(s, x, y, w, h, accent) {
  s.addShape(pptx.ShapeType.roundRect, { x, y, w, h, fill: { color: CARD }, line: { color: accent || BORDER, width: accent ? 1.25 : 1 }, rectRadius: 0.09 });
}
function arrow(s, x1, y1, x2, y2, c) {
  const x = Math.min(x1, x2), y = Math.min(y1, y2), w = Math.abs(x2 - x1), h = Math.abs(y2 - y1);
  s.addShape(pptx.ShapeType.line, { x, y, w, h, flipH: x2 < x1, flipV: y2 < y1, line: { color: c || MUTED, width: 2, endArrowType: "triangle" } });
}
function node(s, x, y, w, h, label, sub, accent) {
  s.addShape(pptx.ShapeType.roundRect, { x, y, w, h, fill: { color: CARD }, line: { color: accent, width: 1.25 }, rectRadius: 0.08 });
  s.addText(label, { x: x + 0.06, y: sub ? y + 0.12 : y, w: w - 0.12, h: sub ? h - 0.45 : h, align: "center", valign: "middle", fontFace: HF, fontSize: 13, bold: true, color: TEXT });
  if (sub) s.addText(sub, { x: x + 0.06, y: y + h - 0.42, w: w - 0.12, h: 0.34, align: "center", valign: "middle", fontFace: BF, fontSize: 9.5, color: MUTED });
}
function chips(s, x, y, items, color) {
  let cx = x;
  items.forEach((t) => {
    const w = 0.18 + t.length * 0.082;
    s.addShape(pptx.ShapeType.roundRect, { x: cx, y, w, h: 0.36, fill: { color: CARD2 }, line: { color: BORDER, width: 1 }, rectRadius: 0.18 });
    s.addText(t, { x: cx, y, w, h: 0.36, align: "center", valign: "middle", fontFace: BF, fontSize: 10.5, color: color || MUTED });
    cx += w + 0.16;
  });
}
const bullets = (arr, color, fs) => arr.map((b) => ({ text: b, options: { bullet: { code: "2022", indent: 16 }, color: color || TEXT, paraSpaceAfter: 9, fontSize: fs || 14 } }));

// ============ 1 — Cover ============
let s = pptx.addSlide(); bg(s);
mark(s, 0.72, 2.15, 0.2, 0.3);
s.addText("AgPay", { x: 0.66, y: 2.4, w: 9, h: 1.1, fontFace: HF, fontSize: 60, bold: true, color: MINT });
s.addText("Payment infrastructure for agriculture.", { x: 0.72, y: 3.6, w: 11.5, h: 0.7, fontFace: HF, fontSize: 27, bold: true, color: TEXT });
s.addText("A vertical fintech platform for agri-commerce: checkout, escrow, settlement, ledger, contract financing, and trusted payment workflows.",
  { x: 0.72, y: 4.4, w: 10.5, h: 0.8, fontFace: BF, fontSize: 14.5, color: MUTED, lineSpacingMultiple: 1.15 });
s.addText("APPLICATION WEDGES", { x: 0.72, y: 5.55, w: 6, h: 0.3, fontFace: HF, fontSize: 11, bold: true, color: GOLD, charSpacing: 2 });
node(s, 0.72, 5.9, 3.0, 0.7, "MeatLovers.ca", "consumer commerce", LIME);
node(s, 3.95, 5.9, 3.0, 0.7, "DealerMaster", "B2B livestock", GOLD);
s.addText("Investor Deck  ·  agpay.ca", { x: 0.72, y: 6.95, w: 8, h: 0.3, fontFace: BF, fontSize: 11, color: MUTED });

// ============ 2 — Investor Thesis ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "Investor thesis");
title(s, "Agriculture needs payment rails that understand real-world conditions.");
const thesis = [
  [MINT, "High-value transactions", "Cattle lots and bulk produce — five and six figures per deal."],
  [LIME, "Multi-party settlement", "Producer, processor, dealer, marketplace, lender — all paid correctly."],
  [GOLD, "Variable final pricing", "Final weights, grades and shrink change the number after the sale."],
  [TEAL, "Embedded credit & contract terms", "Finance contracts, interest, staged payments baked into the deal."],
  [MINT, "Trust, inspection & delivery", "Money should move on weights, grades, inspection and delivery — not blind checkout."],
];
thesis.forEach((t, i) => {
  const y = 2.25 + i * 0.95;
  s.addShape(pptx.ShapeType.ellipse, { x: 0.8, y: y + 0.12, w: 0.16, h: 0.16, fill: { color: t[0] }, line: { type: "none" } });
  s.addText(t[1], { x: 1.15, y, w: 4.4, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: t[0] });
  s.addText(t[2], { x: 5.7, y: y + 0.02, w: 7.0, h: 0.5, fontFace: BF, fontSize: 13, color: MUTED });
});

// ============ 3 — The Problem ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "The problem");
title(s, "The pain is not payments alone. It is payment + proof + settlement.");
const flow3 = ["Order", "Hold", "Validate", "Settle"];
const fw = 2.4, fy = 2.65, fh = 1.0; let fx = 1.1; const step3 = 2.95;
flow3.forEach((n, i) => {
  node(s, fx, fy, fw, fh, n, null, [MINT, GOLD, TEAL, LIME][i]);
  if (i < 3) arrow(s, fx + fw, fy + fh / 2, fx + step3, fy + fh / 2, MUTED);
  fx += step3;
});
s.addText("Today, sellers stitch the rest together by hand:", { x: 1.1, y: 4.4, w: 11, h: 0.4, fontFace: HF, fontSize: 15, bold: true, color: TEXT });
chips(s, 1.1, 5.0, ["Invoices", "E-transfers", "Cheques", "Spreadsheets", "Phone calls", "Manual reconciliation"], MUTED);
s.addText("AgPay collapses order → hold → validate → settle into one workflow with a built-in ledger.",
  { x: 1.1, y: 5.9, w: 11, h: 0.4, fontFace: BF, fontSize: 13.5, italic: true, color: MINT });

// ============ 4 — AgPay Platform ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "The platform");
title(s, "Start with checkout. Add workflows as complexity grows.");
// hub
s.addShape(pptx.ShapeType.roundRect, { x: 5.67, y: 3.05, w: 2.0, h: 1.2, fill: { color: MINT }, line: { type: "none" }, rectRadius: 0.1 });
s.addText("AgPay", { x: 5.67, y: 3.05, w: 2.0, h: 1.2, align: "center", valign: "middle", fontFace: HF, fontSize: 18, bold: true, color: ONACC });
const mods = [
  ["Checkout", 1.0, 2.2, MINT], ["Escrow", 1.0, 3.45, LIME], ["Settlements", 1.0, 4.7, GOLD],
  ["Ledger", 9.3, 2.2, TEAL], ["Financing", 9.3, 3.45, MINT], ["Verify", 9.3, 4.7, LIME],
];
mods.forEach(([label, x, y, c]) => {
  node(s, x, y, 3.0, 0.85, label, null, c);
  const fromX = x < 5 ? x + 3.0 : x;
  const toX = x < 5 ? 5.67 : 7.67;
  arrow(s, fromX, y + 0.42, toX, 3.65, BORDER);
});
s.addText("Merchants adopt checkout first, then layer on escrow, settlement, ledger, financing and verification.",
  { x: 0.7, y: 6.2, w: 11.9, h: 0.4, align: "center", fontFace: BF, fontSize: 13.5, color: MUTED });

// ============ 5 — MeatLovers Use Case ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "Application wedge · consumer commerce");
title(s, "MeatLovers.ca — a freezer-box checkout becomes a live AgPay environment.");
const ml = [["Local meat boxes", LIME], ["Deposits & pre-orders", MINT], ["Batch allocation", GOLD],
["Processor timing", TEAL], ["Producer relationships", LIME], ["Customer trust", MINT]];
ml.forEach((m, i) => {
  const col = i % 3, row = Math.floor(i / 3);
  const x = 0.7 + col * 4.05, y = 2.35 + row * 1.5;
  card(s, x, y, 3.78, 1.3, m[1]);
  s.addText(m[0], { x: x + 0.3, y: y + 0.45, w: 3.2, h: 0.5, fontFace: HF, fontSize: 16, bold: true, color: m[1] });
});
s.addText("A simple consumer checkout already exercises deposits, escrow, final-weight reconciliation, and split settlement.",
  { x: 0.7, y: 5.7, w: 11.9, h: 0.4, fontFace: BF, fontSize: 14, italic: true, color: MINT });

// ============ 6 — MeatLovers Money Flow ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "MeatLovers · money flow");
title(s, "Customer → AgPay → MeatLovers → Processor → Producer.");
const f6 = [["Customer", MINT], ["AgPay", LIME], ["MeatLovers", GOLD], ["Processor", TEAL], ["Producer", MINT]];
const nw = 2.0, ny = 2.8, nh = 1.0; let nx = 0.55; const step6 = 2.555;
f6.forEach((n, i) => {
  node(s, nx, ny, nw, nh, n[0], null, n[1]);
  if (i < 4) arrow(s, nx + nw, ny + nh / 2, nx + step6, ny + nh / 2, MUTED);
  nx += step6;
});
s.addText("AgPay sits in the middle and applies the right rule at each hop:", { x: 0.7, y: 4.3, w: 11, h: 0.4, fontFace: HF, fontSize: 14, bold: true, color: TEXT });
chips(s, 0.7, 4.9, ["Deposit", "Escrow option", "Final-weight reconciliation", "Split settlement", "Platform fee"], LIME);

// ============ 7 — DealerMaster Use Case ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "Application wedge · B2B / livestock");
title(s, "DealerMaster already models the money. AgPay moves it.");
// two flows
const drawFlow = (y, parts, color) => {
  let x = 0.9; const w2 = 2.5, h2 = 0.75, st = 3.1;
  parts.forEach((p, i) => {
    node(s, x, y, w2, h2, p, null, color);
    if (i < parts.length - 1) arrow(s, x + w2, y + h2 / 2, x + st, y + h2 / 2, MUTED);
    x += st;
  });
};
drawFlow(2.45, ["Buy cattle", "AP", "Pay vendor"], GOLD);
drawFlow(3.65, ["Sell cattle", "AR", "Receive payment"], MINT);
s.addText("What AgPay adds:", { x: 0.9, y: 4.75, w: 11, h: 0.35, fontFace: HF, fontSize: 14, bold: true, color: TEXT });
s.addText(bullets([
  "Payment links for invoices  ·  Vendor payouts / cheque replacement",
  "Escrow for cattle transactions  ·  Contract-receivable collections",
  "Financing-partner integration",
], TEXT, 13.5), { x: 1.0, y: 5.15, w: 11.5, h: 1.5, fontFace: BF });

// ============ 8 — Contract Financing ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "DealerMaster · contract financing");
title(s, "Financed cattle sales become a serviceable receivable.");
s.addText(bullets([
  "Customer buys on a finance contract instead of paying up front.",
  "Invoice routes to a Contract Sales receivable (not regular AR).",
  "A contract ledger tracks PURCHASE, PAYMENT and INTEREST.",
], TEXT, 14.5), { x: 0.8, y: 2.35, w: 5.7, h: 2.6, fontFace: BF });
// journal entry callout
card(s, 0.8, 4.6, 5.7, 1.5, GOLD);
s.addText("Monthly interest — journal entry", { x: 1.05, y: 4.78, w: 5.2, h: 0.35, fontFace: HF, fontSize: 13, bold: true, color: GOLD });
s.addText([{ text: "Dr  Contract Sales receivable\n", options: { color: TEXT } }, { text: "Cr  Interest Income", options: { color: TEXT } }],
  { x: 1.05, y: 5.18, w: 5.2, h: 0.8, fontFace: "Consolas", fontSize: 13, lineSpacingMultiple: 1.1 });
// worked example
card(s, 6.85, 2.35, 5.75, 3.75, MINT);
s.addText("Worked example", { x: 7.15, y: 2.55, w: 5, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: MINT });
const ex = [["Financed sale", "$100,000"], ["Less payment", "– $1,000"], ["Balance", "$99,000"],
["Annual rate", "7.45%  (6.95% prime + 0.5%)"], ["Monthly interest", "$99,000 × 7.45% ÷ 12 = $614.62"], ["New balance", "$99,614.62"]];
ex.forEach(([k, v], i) => {
  const y = 3.15 + i * 0.47;
  s.addText(k, { x: 7.15, y, w: 2.3, h: 0.4, fontFace: BF, fontSize: 13, color: MUTED });
  s.addText(v, { x: 9.4, y, w: 3.1, h: 0.4, fontFace: HF, fontSize: 13.5, bold: i === 5, color: i === 5 ? LIME : TEXT });
});

// ============ 9 — Journal Entries ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "DealerMaster · double-entry ledger");
title(s, "Balance-enforced postings become AgPay triggers.");
const th = (t) => ({ text: t, options: { bold: true, color: ONACC, fill: { color: MINT }, fontFace: HF, fontSize: 12 } });
const td = (t, c) => ({ text: t, options: { color: c || TEXT, fontFace: "Consolas", fontSize: 11.5, fill: { color: CARD } } });
const rows = [
  [th("Event"), th("Debit"), th("Credit")],
  [td("AP purchase", MINT), td("Inventory · GST/HST Receivable"), td("Accounts Payable")],
  [td("Payment made", MINT), td("Accounts Payable"), td("Cash / Bank")],
  [td("AR sale", LIME), td("Accounts Receivable"), td("Sales · GST/HST Collected")],
  [td("Payment received", LIME), td("Cash / Bank"), td("Accounts Receivable")],
  [td("Monthly interest", GOLD), td("Contract Sales receivable"), td("Interest Income")],
];
s.addTable(rows, { x: 0.7, y: 2.2, w: 11.9, colW: [2.6, 4.65, 4.65], rowH: 0.5, border: { type: "solid", color: BORDER, pt: 1 }, valign: "middle", margin: 6 });
s.addText("Every posting is balance-enforced. AgPay uses these financial events to trigger collection, payout, escrow release, reconciliation and lender reporting.",
  { x: 0.7, y: 5.6, w: 11.9, h: 0.6, fontFace: BF, fontSize: 13.5, italic: true, color: MINT, lineSpacingMultiple: 1.1 });

// ============ 10 — Product Architecture ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "Product architecture");
title(s, "Domain apps stay focused. AgPay standardizes the money.");
// apps row
const apps = [["MeatLovers.ca", LIME], ["DealerMaster", GOLD], ["Agri marketplaces", TEAL]];
apps.forEach(([t, c], i) => node(s, 1.4 + i * 3.6, 2.2, 3.0, 0.85, t, null, c));
// agpay band
s.addShape(pptx.ShapeType.roundRect, { x: 1.4, y: 3.65, w: 10.5, h: 0.95, fill: { color: MINT }, line: { type: "none" }, rectRadius: 0.1 });
s.addText("AgPay — money movement · payment status · reconciliation · settlement · financing", { x: 1.4, y: 3.65, w: 10.5, h: 0.95, align: "center", valign: "middle", fontFace: HF, fontSize: 15, bold: true, color: ONACC });
// rails row
const rails = [["Stripe / bank rails", MINT], ["AgPay ledger", LIME], ["Financing partners", GOLD]];
rails.forEach(([t, c], i) => node(s, 1.4 + i * 3.6, 5.05, 3.0, 0.85, t, null, c));
[2.9, 6.5, 10.1].forEach((x) => { arrow(s, x, 3.05, x, 3.65, BORDER); arrow(s, x, 4.6, x, 5.05, BORDER); });

// ============ 11 — Business Model ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "Business model");
title(s, "Workflow-specific financial infrastructure — not a commodity processor.");
const rev = [
  ["Take rate", "On checkout & settlement volume", MINT],
  ["Merchant SaaS", "Fees for merchant tools & dashboards", LIME],
  ["Escrow fees", "Conditional / staged release", GOLD],
  ["Financing", "Contract servicing & revenue share", TEAL],
  ["Trust network", "Verification fees", MINT],
  ["Integrations", "Vertical apps & agri ERPs", LIME],
];
rev.forEach((r, i) => {
  const col = i % 3, row = Math.floor(i / 3);
  const x = 0.7 + col * 4.05, y = 2.3 + row * 1.7;
  card(s, x, y, 3.78, 1.5, r[2]);
  s.addText(r[0], { x: x + 0.3, y: y + 0.25, w: 3.2, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: r[2] });
  s.addText(r[1], { x: x + 0.3, y: y + 0.75, w: 3.2, h: 0.6, fontFace: BF, fontSize: 12.5, color: MUTED });
});
s.addText("Pricing scales with the value and complexity of the money moved — not just transaction count.",
  { x: 0.7, y: 5.95, w: 11.9, h: 0.4, fontFace: BF, fontSize: 13.5, italic: true, color: MINT });

// ============ 12 — Roadmap & Ask ============
s = pptx.addSlide(); bg(s); mark(s, 12.1, 0.55);
kicker(s, "Roadmap & investor ask");
title(s, "From checkout to a finance network.");
const stages = [
  ["Now", "Launch checkout", "MeatLovers deposits · merchant order records · Stripe-backed checkout", MINT],
  ["Next", "Integrate DealerMaster", "Invoice payment links · AR collection · AP payouts · contract servicing", LIME],
  ["Then", "Escrow + settlement", "Conditional release for livestock, meat batches & marketplaces", GOLD],
  ["Scale", "Finance network", "Contract receivable servicing · financing partners · risk data · marketplace rails", TEAL],
];
stages.forEach((st, i) => {
  const x = 0.7 + i * 3.05;
  card(s, x, 2.25, 2.85, 2.7, st[3]);
  s.addText(st[0].toUpperCase(), { x: x + 0.25, y: 2.45, w: 2.4, h: 0.3, fontFace: HF, fontSize: 12, bold: true, color: st[3], charSpacing: 2 });
  s.addText(st[1], { x: x + 0.25, y: 2.8, w: 2.4, h: 0.7, fontFace: HF, fontSize: 16, bold: true, color: TEXT });
  s.addText(st[2], { x: x + 0.25, y: 3.6, w: 2.4, h: 1.2, fontFace: BF, fontSize: 12, color: MUTED, lineSpacingMultiple: 1.05 });
  if (i < 3) arrow(s, x + 2.85, 3.6, x + 3.05, 3.6, st[3]);
});
s.addShape(pptx.ShapeType.roundRect, { x: 0.7, y: 5.35, w: 11.9, h: 1.4, fill: { color: "0F2018" }, line: { color: MINT, width: 1.25 }, rectRadius: 0.1 });
s.addText("The ask", { x: 1.0, y: 5.55, w: 5, h: 0.35, fontFace: HF, fontSize: 13, bold: true, color: MINT });
s.addText("Back the buildout of AgPay from checkout into escrow, settlement, contract finance, and vertical agri integrations.",
  { x: 1.0, y: 5.95, w: 11.3, h: 0.7, fontFace: HF, fontSize: 18, bold: true, color: TEXT, lineSpacingMultiple: 1.05 });

pptx.writeFile({ fileName: "C:/Projects/foundry/decks/AgPay.pptx" }).then((f) => console.log("wrote", f));
