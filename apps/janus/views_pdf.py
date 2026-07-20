from reportlab.platypus import Image as RLImage, Table
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .services import get_dd_cockpit, get_run_dashboard
from io import BytesIO
from typing import List, Tuple, Optional
import os
import re
from pathlib import Path
from django.conf import settings
from django.http import HttpResponse
from .models import DueDiligenceRun, DDResponse
from django.contrib.contenttypes.models import ContentType
from apps.mnemos.models import FileAttachment
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
    Flowable,
    KeepTogether,
)
from reportlab.platypus import Image as RLImage, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from reportlab.platypus import PageBreak  # add this import


# PDF Helpers
styles = getSampleStyleSheet()
H1 = styles["Heading1"]
H2 = styles["Heading2"]
H3 = styles["Heading3"]
N  = styles["BodyText"]

class ScorePill(Flowable):
    """
    Small rounded 'SCORE  5 !' pill, drawn like your canvas version but as a Flowable.
    """
    def __init__(self, score, nonneg: bool = False):
        super().__init__()
        self.score = "—" if score is None else str(score)
        self.nonneg = nonneg

        # Visual sizing
        self.pad_x = 6
        self.h = 16

        # Measure approx width using ReportLab font metrics at draw time.
        # We'll compute in wrap() so Platypus knows how wide it is.
        self._w = 80  # fallback until wrap()

    def wrap(self, availWidth, availHeight):
        from reportlab.pdfbase.pdfmetrics import stringWidth

        label = "SCORE"
        suffix = "!" if self.nonneg else ""

        label_w = stringWidth(label, "Helvetica-Bold", 8)
        score_w = stringWidth(self.score, "Helvetica-Bold", 10)
        suffix_w = stringWidth(suffix, "Helvetica-Bold", 9) if suffix else 0

        # total width
        w = self.pad_x + label_w + 6 + score_w + (6 + suffix_w if suffix else 0) + self.pad_x
        self._w = min(w, availWidth)
        return (self._w, self.h + 2)

    def draw(self):
        c = self.canv
        x = 0
        y = 0

        w = self._w
        h = self.h
        r = 7

        # border
        c.setLineWidth(0.8)
        c.setStrokeColorRGB(0.65, 0.65, 0.65)
        c.roundRect(x, y, w, h, r, stroke=1, fill=0)

        # label + score + suffix
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + self.pad_x, y + 5.5, "SCORE")

        # score
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + self.pad_x + c.stringWidth("SCORE", "Helvetica-Bold", 8) + 6, y + 3.5, self.score)

        # suffix
        if self.nonneg:
            c.setFont("Helvetica-Bold", 9)
            score_x = x + self.pad_x + c.stringWidth("SCORE", "Helvetica-Bold", 8) + 6 + c.stringWidth(self.score, "Helvetica-Bold", 10) + 6
            c.drawString(score_x, y + 4.2, "!")


def _is_md_table_line(line: str) -> bool:
    s = (line or "").strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _is_md_table_sep(line: str) -> bool:
    """
    Detect the separator row: | --- | ---: | :--- |
    """
    s = (line or "").strip()
    if not _is_md_table_line(s):
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    if not cells:
        return False
    ok = True
    for c in cells:
        c2 = c.replace(":", "").replace("-", "").strip()
        if c2 != "":
            ok = False
            break
        if "-" not in c:
            ok = False
            break
    return ok


def _parse_md_table(lines: List[str], start_idx: int) -> Tuple[Optional[Table], int]:
    """
    Parse a markdown table starting at start_idx. Returns (Table or None, next_idx).
    """
    if start_idx >= len(lines) or not _is_md_table_line(lines[start_idx]):
        return None, start_idx

    header = lines[start_idx].strip()
    if start_idx + 1 >= len(lines) or not _is_md_table_sep(lines[start_idx + 1]):
        return None, start_idx  # not a real table

    # Collect rows
    rows_raw = []
    i = start_idx
    while i < len(lines) and _is_md_table_line(lines[i]):
        rows_raw.append(lines[i].strip())
        i += 1

    def split_row(row: str) -> List[str]:
        return [c.strip() for c in row.strip("|").split("|")]

    header_cells = split_row(rows_raw[0])
    body_rows = [split_row(r) for r in rows_raw[2:]]  # skip header + sep

    data = []
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("md_cell", parent=styles["BodyText"], fontSize=9, leading=11)

    # Header row (bold)
    data.append([Paragraph(f"<b>{_md_inline_to_rl(c)}</b>", cell_style) for c in header_cells])

    # Body rows
    for r in body_rows:
        # pad missing cells
        while len(r) < len(header_cells):
            r.append("")
        data.append([Paragraph(_md_inline_to_rl(c), cell_style) for c in r[:len(header_cells)]])

    # Column widths: distribute evenly (simple and robust)
    num_cols = max(1, len(header_cells))
    # We'll set colWidths later when we know doc width, so keep None here.
    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.98, 0.98, 0.98)]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    # Stash how many cols so we can set widths later
    table._md_num_cols = num_cols  # type: ignore[attr-defined]
    return table, i


def markdown_to_flowables(md_text: str, content_width: float) -> List:
    """
    Markdown -> Platypus flowables.
    Supports:
      - #, ##, ### headings
      - bullet lists (- item)
      - paragraphs (blank-line separated)
      - markdown tables
      - horizontal rules --- (as Spacer)
    """
    md_text = (md_text or "").replace("\r\n", "\n")
    lines = md_text.split("\n")

    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]
    H2 = styles["Heading2"]
    H3 = styles["Heading3"]
    BODY = ParagraphStyle("md_body", parent=styles["BodyText"], fontSize=10, leading=12)
    BUL = ParagraphStyle("md_bul", parent=styles["BodyText"], fontSize=10, leading=12)

    story: List = []
    para_buf: List[str] = []
    bullets: List[str] = []

    def flush_paragraph():
        nonlocal para_buf
        text = "\n".join(para_buf).strip()
        if text:
            story.append(Paragraph(_md_inline_to_rl(text), BODY))
            story.append(Spacer(1, 6))
        para_buf = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            items = [ListItem(Paragraph(_md_inline_to_rl(b), BUL), leftIndent=12) for b in bullets]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            story.append(Spacer(1, 6))
        bullets = []

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")

        # Table block?
        if _is_md_table_line(line):
            flush_bullets()
            flush_paragraph()
            table, next_i = _parse_md_table(lines, i)
            if table is not None:
                # set widths evenly
                num_cols = getattr(table, "_md_num_cols", 1)
                col_w = max(40, content_width / num_cols)
                table._argW = [col_w] * num_cols  # type: ignore[attr-defined]
                story.append(table)
                story.append(Spacer(1, 8))
                i = next_i
                continue

        # Blank line
        if not line.strip():
            flush_bullets()
            flush_paragraph()
            i += 1
            continue

        # HR
        if line.strip() in ("---", "___", "***"):
            flush_bullets()
            flush_paragraph()
            story.append(Spacer(1, 10))
            i += 1
            continue

        # Headings
        if line.startswith("### "):
            flush_bullets()
            flush_paragraph()
            story.append(Paragraph(_md_inline_to_rl(line[4:].strip()), H3))
            story.append(Spacer(1, 6))
            i += 1
            continue
        if line.startswith("## "):
            flush_bullets()
            flush_paragraph()
            story.append(Paragraph(_md_inline_to_rl(line[3:].strip()), H2))
            story.append(Spacer(1, 6))
            i += 1
            continue
        if line.startswith("# "):
            flush_bullets()
            flush_paragraph()
            story.append(Paragraph(_md_inline_to_rl(line[2:].strip()), H1))
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Bullets
        if line.lstrip().startswith("- "):
            flush_paragraph()
            bullets.append(line.lstrip()[2:].strip())
            i += 1
            continue

        # Otherwise paragraph text
        flush_bullets()
        para_buf.append(line)
        i += 1

    flush_bullets()
    flush_paragraph()
    return story

def _md_inline_to_rl(text: str) -> str:
    """
    Convert a tiny subset of markdown inline formatting to ReportLab Paragraph markup.
    """
    text = text or ""
    # Escape bare ampersands to avoid RL markup issues
    text = text.replace("&", "&amp;")
    # bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text

def make_top_header_block(logo_path: str, title: str, meta: str, filters: str, content_width: float, H1, N, SMALL):
    """
    Header: text on the left, logo on the top-right.
    Logo scales to fit a max box (wide logos stay wide, not squished).
    """
    elems = []

    # Left-hand text block
    lhs = [
        Paragraph(title, H1),
        Paragraph(_md_inline_to_rl(meta), N),
        Paragraph(_md_inline_to_rl(filters), SMALL),
    ]

    if logo_path and os.path.exists(logo_path):
        img = RLImage(logo_path)

        # Allow wide logos: give it more horizontal room on the right
        max_logo_w = 2.2 * inch  # tweak: 1.8–2.6in depending on your branding
        max_logo_h = 0.60 * inch  # keeps it in the header band

        # Preserve aspect ratio by scaling to fit the bounding box
        iw, ih = img.imageWidth, img.imageHeight
        if iw and ih:
            scale = min(max_logo_w / iw, max_logo_h / ih)
            img.drawWidth = iw * scale
            img.drawHeight = ih * scale
        else:
            # fallback size if image dims unavailable
            img.drawWidth = max_logo_w
            img.drawHeight = max_logo_h

        # Keep the logo anchored right
        t = Table(
            [[lhs, img]],
            colWidths=[content_width - max_logo_w, max_logo_w],
        )
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),  # right-align logo cell
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elems.append(t)
    else:
        elems.extend(lhs)

    elems.append(Spacer(1, 12))
    return elems

def markdown_to_story(md_text: str):
    """
    Very small markdown renderer (v1):
    - #, ##, ### headings
    - - bullet lists
    - --- horizontal rule (as extra space)
    - paragraphs separated by blank lines
    """
    md_text = (md_text or "").replace("\r\n", "\n")
    lines = md_text.split("\n")

    story = []
    buf = []
    bullets = []

    def flush_paragraph():
        nonlocal buf
        text = "\n".join(buf).strip()
        if text:
            # Convert **bold** and *italic* to ReportLab's <b>/<i>
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
            story.append(Paragraph(text, N))
            story.append(Spacer(1, 6))
        buf = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            items = [ListItem(Paragraph(b, N), leftIndent=12) for b in bullets]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            story.append(Spacer(1, 6))
        bullets = []

    for raw in lines:
        line = raw.rstrip()

        # blank line => flush buffers
        if not line.strip():
            flush_bullets()
            flush_paragraph()
            continue

        # horizontal rule
        if line.strip() in ("---", "___", "***"):
            flush_bullets()
            flush_paragraph()
            story.append(Spacer(1, 10))
            continue

        # headings
        if line.startswith("### "):
            flush_bullets()
            flush_paragraph()
            story.append(Paragraph(line[4:].strip(), H3))
            story.append(Spacer(1, 6))
            continue
        if line.startswith("## "):
            flush_bullets()
            flush_paragraph()
            story.append(Paragraph(line[3:].strip(), H2))
            story.append(Spacer(1, 6))
            continue
        if line.startswith("# "):
            flush_bullets()
            flush_paragraph()
            story.append(Paragraph(line[2:].strip(), H1))
            story.append(Spacer(1, 6))
            continue

        # bullets
        if line.lstrip().startswith("- "):
            flush_paragraph()
            bullets.append(line.lstrip()[2:].strip())
            continue

        # normal text line
        flush_bullets()
        buf.append(line)

    flush_bullets()
    flush_paragraph()
    return story
def get_logo_path_from_target(target_obj) -> str:
    """
    Uses TargetCompany.logo_file (relative path under MEDIA_ROOT).
    SVG -> PNG/JPG fallback for PDFs.
    """
    if not target_obj:
        return ""

    rel = (getattr(target_obj, "logo_file", "") or "").strip().lstrip("/\\")
    if not rel:
        return ""

    base = Path(settings.MEDIA_ROOT)
    path = base / rel

    # If SVG, prefer a PNG/JPG with same name
    if path.suffix.lower() == ".svg":
        for ext in (".png", ".jpg", ".jpeg"):
            alt = path.with_suffix(ext)
            if alt.exists():
                return str(alt)
        return ""

    return str(path) if path.exists() else ""

def get_logo_path(target_obj) -> str:
    """
    Try common patterns:
      - target_obj.logo (ImageField)
      - target_obj.company_logo (ImageField)
      - target_obj.brand_logo (ImageField)
      - target_obj.organization.logo etc. (extend if needed)
    Returns an absolute filesystem path, or "".
    """
    if not target_obj:
        return ""

    for attr in ("logo", "company_logo", "brand_logo"):
        f = getattr(target_obj, attr, None)
        if f and hasattr(f, "path"):
            try:
                return f.path
            except Exception:
                pass

    # If you store a relative path string like "logos/acme.png"
    for attr in ("logo_path", "logo_file", "logo_filename"):
        v = getattr(target_obj, attr, None)
        if v:
            p = str(v)
            if os.path.isabs(p) and os.path.exists(p):
                return p
            # try MEDIA_ROOT join
            if getattr(settings, "MEDIA_ROOT", None):
                candidate = os.path.join(settings.MEDIA_ROOT, p.lstrip("/\\"))
                if os.path.exists(candidate):
                    return candidate

    return ""
def build_risk_matrix(risks: list[dict]) -> dict:
    """
    Build a 5x5 risk matrix payload.
    risks is list of dicts with keys: id,title,severity,likelihood,risk_score,blocking,status
    Returns:
      {
        "cells": {(s,l): [risk_dicts...]},  # s,l in 1..5
        "row_labels": [5..1],
        "col_labels": [1..5],
      }
    """
    cells = {(s, l): [] for s in range(1, 6) for l in range(1, 6)}
    for r in risks:
        s = int(r.get("severity") or 1)
        l = int(r.get("likelihood") or 1)
        s = max(1, min(5, s))
        l = max(1, min(5, l))
        cells[(s, l)].append(r)

    # Sort each cell: blocking first, then score desc
    for key in cells:
        cells[key] = sorted(cells[key], key=lambda x: (not bool(x.get("blocking")), -(x.get("risk_score") or 0)))

    return {"cells": cells, "row_labels": [5, 4, 3, 2, 1], "col_labels": [1, 2, 3, 4, 5]}

@login_required
def dd_run_qna_pdf(request, run_id: int):
    run = get_object_or_404(DueDiligenceRun, id=run_id)

    qs = (
        DDResponse.objects
        .filter(run=run)
        .select_related("criterion", "criterion__section", "assessed_by")
        .order_by("criterion__section__order_index", "criterion__order_index", "criterion__id")
    )

    only_unknown = request.GET.get("unknown") == "1"
    only_nonneg = request.GET.get("nonneg") == "1"

    if only_unknown:
        qs = qs.filter(Q(score_value=0) & (Q(commentary="") | Q(commentary__isnull=True)))
    if only_nonneg:
        qs = qs.filter(criterion__non_negotiable=True)

    # Attachments bulk-load
    ddresponse_ct = ContentType.objects.get_for_model(DDResponse)
    response_ids = list(qs.values_list("id", flat=True))
    attachments_map = {}
    if response_ids:
        atts = (
            FileAttachment.objects
            .select_related("file_asset")
            .filter(content_type=ddresponse_ct, object_id__in=response_ids)
            .order_by("object_id", "-created_at")
        )
        for a in atts:
            attachments_map.setdefault(a.object_id, []).append(a)

    def get_target_obj(run):
        return getattr(run, "target_company", None) or getattr(run, "target", None)


    def file_label(file_asset) -> str:
        for attr in ("original_name", "filename", "name", "title"):
            v = getattr(file_asset, attr, None)
            if v:
                return str(v)
        return "Attachment"

    def file_url(file_asset) -> str:
        f = getattr(file_asset, "file", None)
        if f is not None and hasattr(f, "url") and f.url:
            return str(f.url)
        for attr in ("url", "download_url"):
            v = getattr(file_asset, attr, None)
            if v:
                return str(v)
        return ""

    def filter_summary() -> str:
        bits = []
        if only_unknown:
            bits.append("Unknown only")
        if only_nonneg:
            bits.append("Non-negotiables only")
        return "Filters: " + (", ".join(bits) if bits else "None")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Due Diligence Q&A",
    )

    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]
    H2 = styles["Heading2"]
    N = ParagraphStyle("qna_normal", parent=styles["BodyText"], fontSize=10, leading=12)
    SMALL = ParagraphStyle("qna_small", parent=styles["BodyText"], fontSize=9, leading=11)

    content_width = doc.width

    title_bits = []
    if hasattr(run, "target") and getattr(run.target, "name", None):
        title_bits.append(run.target.name)
    elif hasattr(run, "target_company") and getattr(run.target_company, "name", None):
        title_bits.append(run.target_company.name)
    if hasattr(run, "template") and run.template:
        title_bits.append(str(run.template))
    if hasattr(run, "round_number") and run.round_number:
        title_bits.append(f"Round {run.round_number}")
    meta = "  •  ".join(title_bits) or f"Run #{run.id}"

    story: List = []

    target_obj = get_target_obj(run)
    logo_path = get_logo_path(target_obj)

    story.extend(
        make_top_header_block(
            logo_path=logo_path,
            title="Due Diligence Q&A",
            meta=meta,
            filters=filter_summary(),
            content_width=content_width,
            H1=H1, N=N, SMALL=SMALL,
        )
    )

    current_section = None
    q_num = 0

    for r in qs:
        section_obj = getattr(r.criterion, "section", None)
        section_title = getattr(section_obj, "title", None) or getattr(section_obj, "name", None) or "Section"
        question = getattr(r.criterion, "title", None) or getattr(r.criterion, "question", None) or "Question"

        commentary = (getattr(r, "commentary", None) or "").strip()
        score = getattr(r, "score_value", None)
        nonneg = bool(getattr(r.criterion, "non_negotiable", False))
        is_unknown = (score == 0) and (commentary == "")

        # -------------------------
        # Section header + page break
        # -------------------------
        if section_title != current_section:
            # New section gets a fresh page, except the very first section
            if current_section is not None:
                story.append(PageBreak())

            current_section = section_title
            story.append(Paragraph(_md_inline_to_rl(current_section), H2))
            story.append(Spacer(1, 10))  # more breathing room under section title

        q_num += 1

        # -------------------------
        # Build a SMALL header group and KeepTogether ONLY that
        # (prevents the "section title alone on a page" issue)
        # -------------------------
        header_block: List = []

        header_block.append(Paragraph(f"<b>{q_num}. {_md_inline_to_rl(question)}</b>", N))
        header_block.append(Spacer(1, 6))

        if is_unknown:
            header_block.append(Paragraph("<b>⚠ Unknown</b> (score=0 and no commentary)", SMALL))
            header_block.append(Spacer(1, 6))

        pill_row = Table(
            [[ScorePill(score, nonneg=nonneg), Paragraph("Non-negotiable" if nonneg else "", N)]],
            colWidths=[100, content_width - 100],
        )
        pill_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        header_block.append(pill_row)
        header_block.append(Spacer(1, 10))

        # Keep only the header bits together (safe)
        story.append(KeepTogether(header_block))

        # -------------------------
        # The rest flows normally (NO KeepTogether)
        # -------------------------
        assessor = getattr(getattr(r, "assessed_by", None), "get_full_name", None)
        assessor_name = assessor() if callable(assessor) else (
            str(getattr(r, "assessed_by", "")) if getattr(r, "assessed_by", None) else ""
        )
        if assessor_name:
            story.append(Paragraph(f"Assessed by: {_md_inline_to_rl(assessor_name)}", SMALL))
            story.append(Spacer(1, 6))

        if commentary:
            story.append(Paragraph("<b>Commentary</b>", SMALL))
            story.append(Spacer(1, 4))
            # Let markdown content break across pages naturally
            story.extend(markdown_to_flowables(commentary, content_width))
        else:
            story.append(Paragraph("<b>Commentary</b>: —", SMALL))
            story.append(Spacer(1, 6))

        resp_atts = attachments_map.get(r.id, [])
        if resp_atts:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Evidence</b>", SMALL))
            items = []
            for a in resp_atts[:10]:
                fa = getattr(a, "file_asset", None)
                label = file_label(fa) if fa else "Attachment"
                url = file_url(fa) if fa else ""
                txt = f"{label}" + (f" ({url})" if url else "")
                items.append(ListItem(Paragraph(_md_inline_to_rl(txt), SMALL), leftIndent=12))
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
            if len(resp_atts) > 10:
                story.append(Paragraph(f"…and {len(resp_atts) - 10} more", SMALL))

        story.append(Spacer(1, 14))

    doc.build(story)

    pdf = buf.getvalue()
    buf.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="dd-qna-run-{run.id}.pdf"'
    return resp

@login_required
def dd_run_detail_pdf(request, run_id: int):
    payload = get_run_dashboard(run_id)
    payload["risk_matrix"] = build_risk_matrix(payload.get("risks", []))

    run = payload.get("run")
    snapshot = payload.get("snapshot")
    completion = payload.get("completion")
    blockers = payload.get("blockers")
    section_scores = payload.get("section_scores", [])
    risks = payload.get("risks", [])
    conditions = payload.get("conditions", [])
    nonneg = payload.get("nonneg", [])
    nonneg_fail = payload.get("nonneg_fail", 0)
    nonneg_unknown = payload.get("nonneg_unknown", 0)
    participants = payload.get("participants", [])
    evidence = payload.get("evidence", [])
    risk_matrix = payload.get("risk_matrix")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Due Diligence Run Summary",
    )

    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]
    H2 = styles["Heading2"]
    N = styles["Normal"]
    BODY = styles["BodyText"]

    # Slightly tighter base body
    BODY.fontSize = 9
    BODY.leading = 11

    # A compact style for table cells
    CELL = ParagraphStyle(
        "CELL",
        parent=BODY,
        fontSize=9,
        leading=11,
        spaceBefore=0,
        spaceAfter=0,
    )

    def p(text, style=CELL):
        return Paragraph(str(text or "—"), style)

    def safe(getter, default="—"):
        try:
            v = getter()
            return default if v in (None, "", []) else v
        except Exception:
            return default

    # Header meta
    target = (
        safe(lambda: getattr(getattr(run, "target_company", None), "name", None), None)
        or safe(lambda: getattr(getattr(run, "target", None), "name", None), None)
        or f"Run #{getattr(run, 'id', run_id)}"
    )
    template = safe(lambda: str(getattr(run, "template", "")), "")
    rnd = safe(lambda: getattr(run, "round_number", ""), "")
    status = safe(lambda: getattr(run, "status", ""), "")

    meta_bits = [target]
    if template:
        meta_bits.append(template)
    if rnd:
        meta_bits.append(f"Round {rnd}")
    if status:
        meta_bits.append(f"Status: {status}")

    story = []

    # Define SMALL (so header helper works)
    SMALL = ParagraphStyle("detail_small", parent=styles["BodyText"], fontSize=9, leading=11)

    # Target object + logo
    target_obj = getattr(run, "target_company", None) or getattr(run, "target", None)
    logo_path = get_logo_path_from_target(target_obj)

    # Third line under meta (pick what you want to show)
    bits = []
    if completion:
        bits.append(f"Responses: {completion.get('completed')}/{completion.get('total')} ({completion.get('pct')}%)")
    if blockers is not None:
        bits.append(f"Blockers: {blockers}")
    filters_line = " • ".join(bits) if bits else ""

    # Header with logo on the RIGHT
    story.extend(
        make_top_header_block(
            logo_path=logo_path,
            title="Due Diligence Run Summary",
            meta=" • ".join(meta_bits),
            filters=filters_line,  # now defined ✅
            content_width=doc.width,
            H1=H1, N=N, SMALL=SMALL,  # if you updated helper signature
        )
    )

    if completion:
        story.append(Paragraph(
            f"Responses: {completion.get('completed')}/{completion.get('total')} ({completion.get('pct')}%)",
            N
        ))
    if blockers is not None:
        story.append(Paragraph(f"Blockers: {blockers}", N))

    story.append(Spacer(1, 12))

    def keep_if_fits(flowables, max_height_in=6.0):
        """
        Wrap in KeepTogether for better pagination, but avoid trapping
        very tall content that could cause big blank gaps.
        max_height_in is a rough safety threshold in inches.
        """
        try:
            # crude guard: if there's a table in here, use its row count to estimate height
            for f in flowables:
                if isinstance(f, Table):
                    # estimate row height ~ 16px-ish => ~0.22in per row (depends on your styles)
                    rows = len(getattr(f, "_cellvalues", []) or [])
                    est_h = 0.22 * rows
                    if est_h > max_height_in:
                        return flowables  # too tall, don't keep together
            return [KeepTogether(flowables)]
        except Exception:
            return flowables

    def make_table(data, col_widths, header_bg=colors.whitesmoke):
        """
        data must already include a header row at data[0]
        """
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.98, 0.98, 0.98)]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # -------------------------
    # Company Narrative (Long Description)
    # -------------------------
    story.append(Paragraph("Company Narrative", H2))

    # Try to find the target company object
    target_obj = getattr(run, "target_company", None) or getattr(run, "target", None)

    long_desc = ""
    if target_obj is not None:
        long_desc = (getattr(target_obj, "long_description", None) or "").strip()

    if long_desc:
        story.extend(markdown_to_flowables(long_desc, doc.width))
    else:
        story.append(Paragraph("No long description captured yet.", N))

    story.append(Spacer(1, 10))

    # -------------------------
    # Deal Snapshot
    # -------------------------
    story.append(Paragraph("Deal Snapshot", H2))
    if snapshot:
        getv = (lambda k: snapshot.get(k)) if isinstance(snapshot, dict) else (lambda k: getattr(snapshot, k, None))

        snap_lines = [
            f"As-of: {getv('metrics_as_of_date') or '—'}    Confidence: {getv('confidence') or '—'}",
            f"Customers: {getv('total_customers') or '—'} (Active: {getv('active_customers') or '—'})    Top3 rev%: {getv('top_3_customer_pct_revenue') or '—'}",
            f"ARR: {getv('arr') or '—'}    MRR: {getv('mrr') or '—'}    Rev TTM: {getv('revenue_ttm') or '—'}",
            f"GM%: {getv('gross_margin_pct') or '—'}    NRR%: {getv('net_revenue_retention_pct') or '—'}    Churn%: {getv('churn_rate_pct') or '—'}    ACV: {getv('avg_contract_value') or '—'}",
            f"Burn/mo: {getv('burn_rate_monthly') or '—'}    Runway (mo): {getv('runway_months') or '—'}    Op Inc TTM: {getv('operating_income_ttm') or '—'}",
        ]
        for ln in snap_lines:
            story.append(Paragraph(ln, N))
        if getv("source_notes"):
            story.append(Paragraph(f"Source: {getv('source_notes')}", styles["Italic"]))
    else:
        story.append(Paragraph("No snapshot captured yet.", N))
    story.append(Spacer(1, 10))

    # -------------------------
    # Section Performance (table)
    # -------------------------
    section_block = [Paragraph("Section Performance", H2)]
    if section_scores:
        data = [[p("<b>Section</b>"), p("<b>Weight</b>"), p("<b>Responses</b>"), p("<b>Score</b>")]]
        for s in section_scores:
            data.append([
                p(s.get("section_title")),
                p(s.get("section_weight")),
                p(f"{s.get('responded')}/{s.get('total_criteria')}"),
                p(s.get("section_score_0_100")),
            ])
        section_block.append(make_table(data, col_widths=[280, 70, 90, 70]))
    else:
        section_block.append(Paragraph("No section scoring available yet.", N))

    section_block.append(Spacer(1, 10))
    story.extend(keep_if_fits(section_block, max_height_in=5.5))

    # -------------------------
    # Risks (table)
    # -------------------------
    story.append(Paragraph("Risks", H2))
    if risks:
        data = [[p("<b>Title</b>"), p("<b>Category</b>"), p("<b>S/L</b>"), p("<b>Score</b>"), p("<b>Status</b>"), p("<b>Block</b>")]]
        for r in risks:
            if isinstance(r, dict):
                title = r.get("title")
                cat = r.get("category")
                sl = f"S{r.get('severity')} L{r.get('likelihood')}"
                score = r.get("risk_score")
                st = r.get("status")
                blk = "Yes" if r.get("blocking") else "No"
            else:
                title = getattr(r, "title", "")
                cat = getattr(r, "category", "")
                sl = f"S{getattr(r,'severity','')} L{getattr(r,'likelihood','')}"
                score = getattr(r, "risk_score", "")
                st = getattr(r, "status", "")
                blk = "Yes" if getattr(r, "blocking", False) else "No"

            data.append([p(title), p(cat), p(sl), p(score), p(st), p(blk)])

        story.append(make_table(data, col_widths=[235, 95, 55, 55, 70, 40]))
    else:
        story.append(Paragraph("No risks captured yet.", N))
    story.append(Spacer(1, 10))

    # -------------------------
    # Conditions (table)
    # -------------------------
    story.append(Paragraph("Conditions to Proceed", H2))
    if conditions:
        data = [[p("<b>Title</b>"), p("<b>Must Complete Before</b>"), p("<b>Due</b>"), p("<b>Status</b>")]]
        for cc in conditions:
            if isinstance(cc, dict):
                title = cc.get("title")
                mcb = cc.get("must_complete_before")
                due = cc.get("due_by") or "—"
                st = cc.get("status")
            else:
                title = getattr(cc, "title", "")
                mcb = getattr(cc, "must_complete_before", "")
                due = getattr(cc, "due_by", None) or "—"
                st = getattr(cc, "status", "")

            data.append([p(title), p(mcb), p(due), p(st)])

        story.append(make_table(data, col_widths=[255, 165, 70, 60]))
    else:
        story.append(Paragraph("No conditions captured yet.", N))
    story.append(Spacer(1, 10))

    # -------------------------
    # Non-negotiables (TABLE ✅)
    # -------------------------
    story.append(Paragraph(f"Non-negotiables (Fail: {nonneg_fail} • Unknown: {nonneg_unknown})", H2))
    if nonneg:
        data = [[p("<b>Section</b>"), p("<b>Criterion</b>"), p("<b>Score</b>"), p("<b>Threshold</b>"), p("<b>Status</b>")]]
        for n in nonneg:
            data.append([
                p(n.get("section_title")),
                p(n.get("title")),
                p(n.get("score_value")),
                p(n.get("threshold")),
                p(n.get("status")),
            ])
        story.append(make_table(data, col_widths=[110, 270, 45, 60, 55]))
    else:
        story.append(Paragraph("No non-negotiables configured in template.", N))
    story.append(Spacer(1, 10))

    # -------------------------
    # Risk Matrix (kept simple for now)
    # -------------------------
    story.append(Paragraph("Risk Matrix", H2))
    if risk_matrix:
        if isinstance(risk_matrix, dict):
            for k, v in risk_matrix.items():
                story.append(Paragraph(f"{k}: {v}", N))
        else:
            story.append(Paragraph("Risk matrix computed.", N))
    else:
        story.append(Paragraph("No risk matrix available.", N))
    story.append(Spacer(1, 10))

    # -------------------------
    # Participants (table)
    # -------------------------
    story.append(Paragraph("Participants", H2))
    if participants:
        data = [[p("<b>User</b>"), p("<b>Role</b>"), p("<b>Permission</b>")]]
        for p_row in participants:
            data.append([p(p_row.get("user")), p(p_row.get("role")), p(p_row.get("permission"))])
        story.append(make_table(data, col_widths=[230, 180, 170]))
    else:
        story.append(Paragraph("No participants assigned.", N))
    story.append(Spacer(1, 10))

    # -------------------------
    # Recent Evidence (table)
    # -------------------------
    story.append(Paragraph("Recent Evidence", H2))
    if evidence:
        data = [[p("<b>Title</b>"), p("<b>Type</b>"), p("<b>Sensitivity</b>"), p("<b>Created</b>")]]
        for e in evidence:
            if isinstance(e, dict):
                data.append([p(e.get("title")), p(e.get("evidence_type")), p(e.get("sensitivity")), p(e.get("created_at"))])
            else:
                data.append([p(getattr(e, "title", "")), p(getattr(e, "evidence_type", "")), p(getattr(e, "sensitivity", "")), p(getattr(e, "created_at", ""))])

        story.append(make_table(data, col_widths=[280, 110, 90, 100]))
    else:
        story.append(Paragraph("No evidence uploaded yet.", N))

    doc.build(story)

    pdf = buf.getvalue()
    buf.close()

    filename = f"dd-run-detail-{getattr(run,'id',run_id)}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp

@login_required
def dd_run_questions_pdf(request, run_id: int):
    run = get_object_or_404(DueDiligenceRun, id=run_id)

    qs = (
        DDResponse.objects
        .filter(run=run)
        .select_related("criterion", "criterion__section")
        .order_by("criterion__section__order_index", "criterion__order_index", "criterion__id")
    )

    # Same filters as dd_run_responses
    only_unknown = request.GET.get("unknown") == "1"
    only_nonneg = request.GET.get("nonneg") == "1"

    if only_unknown:
        qs = qs.filter(Q(score_value=0) & (Q(commentary="") | Q(commentary__isnull=True)))

    if only_nonneg:
        qs = qs.filter(criterion__non_negotiable=True)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    left = 0.75 * inch
    right = 0.75 * inch
    top = height - 0.75 * inch
    bottom = 0.75 * inch

    def header():
        y = top
        c.setFont("Helvetica-Bold", 16)
        c.drawString(left, y, "Due Diligence Questions")
        y -= 18

        c.setFont("Helvetica", 10)
        title_bits = []
        # Be defensive: these fields might vary
        if hasattr(run, "target") and getattr(run.target, "name", None):
            title_bits.append(run.target.name)
        elif hasattr(run, "target_company") and getattr(run.target_company, "name", None):
            title_bits.append(run.target_company.name)

        if hasattr(run, "template") and run.template:
            title_bits.append(str(run.template))

        if hasattr(run, "round_number") and run.round_number:
            title_bits.append(f"Round {run.round_number}")

        meta = "  •  ".join(title_bits) or f"Run #{run.id}"
        c.drawString(left, y, meta)
        y -= 12

        c.setStrokeColorRGB(0.75, 0.75, 0.75)
        c.line(left, y, width - right, y)
        y -= 18
        return y

    y = header()
    current_section = None
    q_num = 0
    max_width = width - left - right

    for r in qs:
        section_obj = getattr(r.criterion, "section", None)
        section_title = getattr(section_obj, "title", None) or getattr(section_obj, "name", None) or "Section"
        question = getattr(r.criterion, "title", None) or getattr(r.criterion, "question", None) or "Question"

        # Section heading
        if section_title != current_section:
            current_section = section_title

            if y < bottom + 40:
                c.showPage()
                y = header()

            c.setFont("Helvetica-Bold", 12)
            c.drawString(left, y, section_title)
            y -= 16

        q_num += 1
        c.setFont("Helvetica", 11)

        # Simple word-wrap
        text = f"{q_num}. {question}"
        words = text.split()
        line = ""
        lines = []
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", 11) <= max_width:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)

        for ln in lines:
            if y < bottom + 20:
                c.showPage()
                y = header()
                c.setFont("Helvetica-Bold", 12)
                c.drawString(left, y, current_section)
                y -= 16
                c.setFont("Helvetica", 11)

            c.drawString(left, y, ln)
            y -= 14

        y -= 4  # spacer

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(width - right, bottom - 10, "Generated by Janus • Questions only")
    c.showPage()
    c.save()

    pdf = buf.getvalue()
    buf.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="dd-questions-run-{run.id}.pdf"'
    return resp