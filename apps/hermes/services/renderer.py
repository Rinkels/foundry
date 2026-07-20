from dataclasses import dataclass
from datetime import datetime
import markdown


@dataclass
class RenderedIssue:
    html_body: str


def render_issue_markdown(md_text: str) -> RenderedIssue:
    html = markdown.markdown(
        md_text or "",
        extensions=[
            "extra",
            "tables",
            "toc",
            "fenced_code",
            "codehilite",
        ],
    )
    return RenderedIssue(html_body=html)
