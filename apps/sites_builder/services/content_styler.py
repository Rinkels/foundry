from __future__ import annotations

import re
from bs4 import BeautifulSoup


def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text or "section"


def _mark_long_lists(sec):
    for ul in sec.find_all("ul"):
        items = ul.find_all("li", recursive=False)
        if len(items) >= 6:
            ul["class"] = list(set((ul.get("class") or []) + ["list-cols-2"]))


def _dl_pairs(dl):
    """Return ordered (dt, dd) pairs from a <dl>."""
    pairs = []
    current_dt = None
    for child in dl.find_all(["dt", "dd"], recursive=False):
        if child.name == "dt":
            current_dt = child
        elif child.name == "dd" and current_dt is not None:
            pairs.append((current_dt, child))
            current_dt = None
    return pairs


def _convert_single_dl_to_accordion(soup: BeautifulSoup, dl, accordion_id: str, open_first: bool = True) -> None:
    pairs = _dl_pairs(dl)
    if not pairs:
        return

    accordion = soup.new_tag("div")
    accordion["class"] = ["accordion", "accordion-flush", "faq-accordion"]
    accordion["id"] = accordion_id

    for idx, (dt, dd) in enumerate(pairs, start=1):
        q_text = dt.get_text(" ", strip=True)
        item_id = f"{accordion_id}-item-{idx}"
        heading_id = f"{item_id}-heading"
        collapse_id = f"{item_id}-collapse"

        is_first = open_first and idx == 1

        item = soup.new_tag("div")
        item["class"] = ["accordion-item"]

        h2 = soup.new_tag("h2")
        h2["class"] = ["accordion-header"]
        h2["id"] = heading_id

        btn = soup.new_tag("button")
        btn["class"] = ["accordion-button"] + ([] if is_first else ["collapsed"])
        btn["type"] = "button"
        btn["data-bs-toggle"] = "collapse"
        btn["data-bs-target"] = f"#{collapse_id}"
        btn["aria-expanded"] = "true" if is_first else "false"
        btn["aria-controls"] = collapse_id
        btn.string = q_text

        h2.append(btn)

        collapse = soup.new_tag("div")
        collapse["id"] = collapse_id
        collapse["class"] = ["accordion-collapse", "collapse"] + (["show"] if is_first else [])
        collapse["aria-labelledby"] = heading_id
        collapse["data-bs-parent"] = f"#{accordion_id}"

        body = soup.new_tag("div")
        body["class"] = ["accordion-body"]

        # Move dd contents into the accordion body (preserves links etc.)
        for node in list(dd.contents):
            body.append(node.extract())

        collapse.append(body)

        item.append(h2)
        item.append(collapse)
        accordion.append(item)

    dl.replace_with(accordion)


def _convert_all_dls_in_container(soup: BeautifulSoup, container, page_key: str) -> None:
    """
    Convert all <dl> found inside container into accordions.
    Each <dl> becomes its own accordion with unique IDs.
    """
    dls = container.find_all("dl")
    if not dls:
        return

    for i, dl in enumerate(dls, start=1):
        # Idempotency: skip if it's already been converted
        if dl.find_parent(class_="faq-accordion") is not None:
            continue

        accordion_id = f"dl-{page_key}-{i}"
        _convert_single_dl_to_accordion(soup, dl, accordion_id=accordion_id, open_first=True)


def cardify_subsections(full_html: str) -> str:
    """
    Universal post-processor:
      - Wrap direct child <section> blocks under the main content section into cards
      - Mark long <ul> as 2-column on desktop
      - Convert ALL <dl> into Bootstrap accordions
    """
    soup = BeautifulSoup(full_html, "html.parser")

    # Best-effort unique key for IDs
    title = soup.title.string if soup.title and soup.title.string else "page"
    page_key = _slugify(title)[:50] or "page"

    article = soup.select_one("main article.neon-glass-card")
    if not article:
        return full_html

    # Convert ALL dl in the main article (not just FAQ sections)
    _convert_all_dls_in_container(soup, article, page_key)

    # Cardify subsections if the structure matches your generator
    outer = article.find("section", recursive=False)
    if not outer:
        return str(soup)

    subsections = [c for c in outer.find_all("section", recursive=False)]
    if not subsections:
        return str(soup)

    for sec in subsections:
        # Skip if already wrapped by a section-card (prevents nesting on repeated builds)
        if sec.parent and getattr(sec.parent, "get", None):
            parent_classes = sec.parent.get("class") or []
            if "section-card" in parent_classes:
                continue

        wrapper = soup.new_tag("div")
        wrapper["class"] = ["section-card", "neon-glass-card", "content-card"]
        sec.wrap(wrapper)

        _mark_long_lists(sec)

    return str(soup)
