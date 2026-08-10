"""Customer-facing exposure report — the one-page leave-behind, generated.

Everything on the page comes from the database: the result line from the open
findings, the dismissal table from triaged exposures and the notes an analyst
wrote on them, the footprint section from `WatchProfile.posture`. The only
hardcoded prose is the coverage and method text, which describes the technique
rather than the customer.

Design intent: the report is readable by someone who does not work in security.
It leads with the answer, states plainly what was *not* checked, and shows the
findings that were dismissed rather than hiding them — a report that only shows
what survived triage gives the reader no way to judge the triage.
"""
from __future__ import annotations

from collections import OrderedDict
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..models import Exposure
from . import detect

NAVY = colors.HexColor("#1F3A5F")
SLATE = colors.HexColor("#4A5568")
RULE = colors.HexColor("#C8D1DC")
GREENBG = colors.HexColor("#EAF5EE")
GREENLN = colors.HexColor("#2E7D4F")
AMBERBG = colors.HexColor("#FDF3E7")
AMBERLN = colors.HexColor("#B25E09")
BOXBG = colors.HexColor("#F5F7FA")
INK = colors.HexColor("#1A202C")

COVERAGE_COVERED = [
    "Public repositories in GitHub's code index",
    "The organisations and repositories listed above, and all public GitHub",
    "Current file contents",
]
COVERAGE_NOT_COVERED = [
    "Private repositories, and GitHub gists",
    "<b>Commit history</b> — a credential deleted from a file can remain in the "
    "repository's history",
    "GitLab, Bitbucket, paste sites, container images",
    "Large and binary files, which GitHub does not index",
]
METHOD_TEXT = (
    "<b>Method.</b> Public data only, retrieved through GitHub's official REST API, "
    "read-only. No credential was tested, used or retained — findings are stored as "
    "redacted fingerprints. This is a point-in-time check of one public surface and is "
    "not a security assessment. Raw output available on request."
)


def _style(name, **kw):
    base = dict(name=name, fontName="Helvetica", fontSize=9.1, leading=12.0,
                textColor=INK, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(**base)


S = {
    "title": _style("title", fontName="Helvetica-Bold", fontSize=18, leading=20, textColor=NAVY),
    "sub": _style("sub", fontSize=9.4, leading=12, textColor=SLATE),
    "h2": _style("h2", fontName="Helvetica-Bold", fontSize=10.4, leading=12.5,
                 textColor=NAVY, spaceAfter=3),
    "body": _style("body"),
    "small": _style("small", fontSize=8.4, leading=10.8, textColor=SLATE),
    "resulthead": _style("resulthead", fontName="Helvetica-Bold", fontSize=13.5, leading=16),
    "resultsub": _style("resultsub", fontSize=9.0, leading=11.5, textColor=SLATE),
    "cell": _style("cell", fontSize=8.8, leading=11.2),
    "cellb": _style("cellb", fontSize=8.8, leading=11.2, fontName="Helvetica-Bold"),
}

# Findings at or above this severity are what the result line reports on.
# Keyword mentions are context, not exposure, and would otherwise drown it.
MATERIAL_SEVERITIES = [Exposure.SEV_CRITICAL, Exposure.SEV_HIGH, Exposure.SEV_MEDIUM]


def _joined(items: list[str], sep: str = " &nbsp;·&nbsp; ") -> str:
    return sep.join(items)


def _result_block(profile, run, open_material):
    """The headline. Green when there is nothing to act on, amber when there is."""
    clean = not open_material
    if clean:
        head = "Result: no exposed credentials found."
        bg, line, ink = GREENBG, GREENLN, GREENLN
    else:
        n = len(open_material)
        head = (f"Result: {n} credential exposure{'' if n == 1 else 's'} "
                f"require{'s' if n == 1 else ''} attention.")
        bg, line, ink = AMBERBG, AMBERLN, AMBERLN

    scope_bits = []
    if run:
        scope_bits.append(f"{run.queries_run} targeted searches")
        scope_bits.append(f"{run.files_examined} files examined")
    scopes = profile.org_list + profile.repo_list
    if scopes:
        where = ", ".join(scopes[:3]) + ("…" if len(scopes) > 3 else "")
        scope_bits.append(
            f"{where}{' and the wider public GitHub index' if profile.search_globally else ''}"
        )

    head_style = ParagraphStyle("rh", parent=S["resulthead"], textColor=ink)
    t = Table(
        [[Paragraph(head, head_style)],
         [Paragraph(_joined(scope_bits), S["resultsub"])]],
        colWidths=[7.0 * inch],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, line),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (0, 0), 7),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1),
        ("TOPPADDING", (0, 1), (-1, -1), 0),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
    ]))
    return t


def _grouped_table(exposures, *, show_location: bool) -> Table:
    """Collapse exposures into 'N × Detector — explanation' rows.

    Nine copies of one Amazon affiliate parameter is one fact, not nine.
    """
    groups: OrderedDict[tuple[str, str], list] = OrderedDict()
    for ex in exposures:
        key = (ex.detector_label or ex.detector, (ex.triage_note or ex.note).strip())
        groups.setdefault(key, []).append(ex)

    rows = []
    for (label, explanation), items in groups.items():
        left = f"{len(items)} &times; {label}"
        right = explanation or "No explanation recorded."
        if show_location:
            where = sorted({e.repo_full_name for e in items})
            shown = ", ".join(where[:2]) + ("…" if len(where) > 2 else "")
            right = f"<b>{shown}</b><br/>{right}"
        rows.append([Paragraph(left, S["cellb"]), Paragraph(right, S["cell"])])

    t = Table(rows, colWidths=[1.55 * inch, 5.45 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BOXBG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.6, colors.white),
    ]))
    return t


def _posture_bullets(profile) -> list[str]:
    """Turn the posture snapshot into sentences a non-engineer can act on."""
    posture = profile.posture or {}
    out: list[str] = []
    for org, s in (posture.get("orgs") or {}).items():
        if not s or s.get("error"):
            continue
        total, unowned = s.get("total", 0), s.get("unowned", 0)
        if total:
            out.append(
                f"<b>{total} public repositories</b> under <i>{org}</i>. "
                f"{s.get('stale', 0)} have had no commit in over {s.get('stale_years', 5)} "
                f"years and only {s.get('archived', 0)} are archived — leaving {unowned} "
                f"that appear current, are publicly attributed, and have no evident owner."
            )
        if s.get("forks"):
            out.append(
                f"<b>{s['forks']} of the {total} are forks</b> of upstream projects — "
                "worth confirming which carry local modifications."
            )
        prefixed = [p for p in s.get("prefixed", []) if not p["archived"]]
        if prefixed:
            names = ", ".join(p["name"] for p in prefixed[:4])
            out.append(
                f"<b>{len(prefixed)} internally-named libraries are published publicly</b> "
                f"({names}{'…' if len(prefixed) > 4 else ''}), several still actively "
                "maintained. Deliberate policy, or historical drift?"
            )
        oldest = s.get("oldest", [])
        if len(oldest) >= 3:
            names = ", ".join(o["name"] for o in oldest[:4])
            out.append(
                f"<b>The oldest repositories document historical architecture</b> — "
                f"{names}. Individually harmless; collectively a map of the estate."
            )
        if s.get("top_language") and total:
            out.append(
                f"<b>{s['top_language_count']} of {total} repositories are "
                f"{s['top_language']}</b>, which indicates where modernisation effort "
                "would concentrate."
            )
    return out


def build(profile, *, run=None, generated_by: str = "") -> bytes:
    """Render the one-page report. Returns PDF bytes."""
    run = run or profile.runs.first()

    open_qs = profile.exposures.filter(
        status__in=[Exposure.STATUS_NEW, Exposure.STATUS_TRIAGED]
    )
    open_material = list(open_qs.filter(severity__in=MATERIAL_SEVERITIES))
    dismissed = list(profile.exposures.filter(status=Exposure.STATUS_FALSE_POSITIVE))
    mentions = open_qs.filter(severity=Exposure.SEV_INFO).count()

    story = []

    story.append(Paragraph("Public Exposure Check", S["title"]))
    # Built by hand rather than strftime: "%-d" is glibc-only and blows up on Windows.
    stamp = timezone.localtime(run.started_at if run else timezone.now())
    when = f"{stamp.day} {stamp:%B %Y}"
    story.append(Paragraph(f"{profile.name} &nbsp;·&nbsp; {when}", S["sub"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=8))

    story.append(_result_block(profile, run, open_material))
    story.append(Spacer(1, 9))

    # -- what was checked ---------------------------------------------------
    story.append(Paragraph("What was checked", S["h2"]))
    labels = sorted({d.label for d in detect.DETECTORS})
    story.append(Paragraph(
        f"<b>Credential classes ({len(detect.DETECTORS)}):</b> {_joined(labels)}.",
        S["body"]))
    story.append(Spacer(1, 2.5))
    identifiers = profile.keyword_list
    if identifiers:
        story.append(Paragraph(
            f"<b>Identifiers:</b> {_joined(identifiers)}. Searches pair an identifier "
            "with a credential marker, so a match means a file contains both.",
            S["body"]))
        story.append(Spacer(1, 8))

    # -- open findings, when there are any ----------------------------------
    if open_material:
        story.append(Paragraph("Findings requiring attention", S["h2"]))
        story.append(_grouped_table(open_material, show_location=True))
        story.append(Spacer(1, 8))

    # -- dismissed ----------------------------------------------------------
    if dismissed:
        story.append(Paragraph(
            f"Flagged by the scanner, then dismissed ({len(dismissed)})", S["h2"]))
        story.append(_grouped_table(dismissed, show_location=False))
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            "Any tool that pattern-matches on credential formats reports these. "
            "Establishing that they are nothing is the substance of the check.",
            S["small"]))
        story.append(Spacer(1, 8))

    # -- coverage -----------------------------------------------------------
    story.append(Paragraph("Coverage", S["h2"]))
    cov = Table(
        [[Paragraph("<b>Covered</b>", S["cell"]), Paragraph("<b>Not covered</b>", S["cell"])],
         [Paragraph("<br/>".join(COVERAGE_COVERED), S["cell"]),
          Paragraph("<br/>".join(COVERAGE_NOT_COVERED), S["cell"])]],
        colWidths=[2.55 * inch, 4.45 * inch],
    )
    cov.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE),
    ]))
    story.append(cov)
    story.append(Spacer(1, 8))

    # -- footprint observations --------------------------------------------
    bullets = _posture_bullets(profile)
    if bullets:
        story.append(Paragraph("Observations on the public footprint", S["h2"]))
        story.append(Paragraph(
            "These are not vulnerabilities. They are governance questions worth a "
            "decision:", S["small"]))
        story.append(Spacer(1, 3))
        for line in bullets:
            story.append(Paragraph(f"•&nbsp;&nbsp;{line}", S["body"]))
            story.append(Spacer(1, 2.5))
        story.append(Spacer(1, 4))

    if mentions:
        story.append(Paragraph(
            f"{mentions} public mentions of the tracked identifiers were also recorded. "
            "These are references to the organisation in third-party code and "
            "documentation, not exposures.", S["small"]))
        story.append(Spacer(1, 4))

    story.append(HRFlowable(width="100%", thickness=0.6, color=RULE, spaceAfter=6))
    story.append(Paragraph(METHOD_TEXT, S["small"]))
    if generated_by:
        story.append(Spacer(1, 5))
        story.append(Paragraph(generated_by, S["small"]))

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.6 * inch, bottomMargin=0.55 * inch,
        title=f"Public Exposure Check — {profile.name}",
        author=generated_by or "Aegis",
    )
    doc.build(story)
    return buf.getvalue()


def filename_for(profile, run=None) -> str:
    run = run or profile.runs.first()
    when = (run.started_at if run else timezone.now()).strftime("%Y-%m-%d")
    return f"{profile.slug}-exposure-check-{when}.pdf"
