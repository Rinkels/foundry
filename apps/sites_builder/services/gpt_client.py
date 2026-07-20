import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class GPTSiteClient:
    """
    Thin wrapper around ChatGPT for SEO-focused static site generation.

    Upgrades:
    - IA planning (menu + page briefs) via generate_site_ia()
    - Optional "editor pass" refinement via refine_page_content()
    - Stronger prompting toward fewer, deeper "pillar" pages
    - Internal links should use internal://<slug> placeholders (post-processed later)
    """

    def __init__(self, model: str = "gpt-4.1-mini"):
        self.model = model
        self.last_usage = {}
        self._bill_obj = None
        self._bill_action = "llm"

    def set_billing(self, obj, action: str = "llm"):
        """Set the object + action that subsequent _chat() calls bill their token
        usage against (logged to the shared AI ledger). Call once per flow."""
        self._bill_obj = obj
        self._bill_action = action

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        u = getattr(resp, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(u, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(u, "completion_tokens", 0) or 0,
            "total_tokens": getattr(u, "total_tokens", 0) or 0,
        }
        if self._bill_obj is not None:
            try:
                from .usage import record_text_usage
                record_text_usage(obj=self._bill_obj, action=self._bill_action,
                                  model=self.model, **self.last_usage)
            except Exception as e:  # noqa: BLE001
                print(f"[WARN] Failed to log text usage: {e}")
        return resp.choices[0].message.content

    def generate_site_ia(
        self,
        site_description: str,
        target_page_count: int = 8,
        max_depth: int = 2,
        top_nav_items: int = 5,
    ) -> Dict[str, Any]:
        """
        Returns an IA plan (menu + page briefs) that we can materialize into Page skeletons.

        JSON shape:
        {
          "nav": [
            {"title":"Services","slug":"services","children":[{"title":"...","slug":"..."}]}
          ],
          "pages": [
            {
              "title":"Services",
              "slug":"services",
              "purpose":"pillar",
              "primary_keyword":"...",
              "key_sections":["...","..."],
              "internal_links":["internal://about-us","internal://contact-us"]
            }
          ]
        }
        """
        system = {
            "role": "system",
            "content": (
                "You are an expert information architect and SEO strategist for marketing websites. "
                "You design lean site structures with fewer pages and deeper, more expert content. "
                "Always respond with valid JSON only."
            ),
        }

        user = {
            "role": "user",
            "content": (
                "Create a lean site Information Architecture (IA) plan from this business description:\n"
                f"{site_description}\n\n"
                "Goals:\n"
                f"- Target total pages: {target_page_count} (fewer pages, higher quality)\n"
                f"- Max depth: {max_depth}\n"
                f"- Top navigation items (not counting Home/Contact): about {top_nav_items}\n\n"
                "Rules:\n"
                "- Prefer 'pillar' pages with multiple sections over creating many small pages.\n"
                "- Only create supporting pages when they represent a distinct search intent "
                "  (e.g., pricing, case studies, FAQ, compliance, industries).\n"
                "- Use slugs that are simple and stable (kebab-case). Avoid inventing many variants.\n"
                "- Ensure nav slugs correspond to pages.\n\n"
                "Return JSON with keys:\n"
                "- nav: a tree list where each item has title, slug, optional children\n"
                "- pages: a flat list of page briefs with title, slug, purpose ('pillar' or 'support'), "
                "  primary_keyword, key_sections (6-10 items), internal_links (as internal://<slug>)\n"
            ),
        }

        raw = self._chat([system, user])
        return json.loads(raw)

    def refine_page_content(
        self,
        site_context: Dict[str, Any],
        page: Dict[str, Any],
        draft: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Second pass "senior editor" refinement.
        Input: draft JSON (meta_title/meta_description/focus_keyword/body_html)
        Output: same keys, improved depth, specificity, structure, and correct internal:// links.
        """
        system = {
            "role": "system",
            "content": (
                "You are a senior editor and subject-matter marketing strategist. "
                "You improve technical accuracy, specificity, and clarity. "
                "You remove fluff and add practical detail (steps, checklists, pitfalls, FAQs). "
                "Always respond with valid JSON only."
            ),
        }

        user = {
            "role": "user",
            "content": (
                "Refine this page draft for a static marketing site.\n\n"
                "SITE CONTEXT:\n"
                f"{site_context}\n\n"
                "PAGE:\n"
                f"{page}\n\n"
                "DRAFT JSON:\n"
                f"{draft}\n\n"
                "Refinement requirements:\n"
                "- Keep exactly ONE <h1>.\n"
                "- Ensure at least 6 strong <h2> sections when the page is a pillar page.\n"
                "- Add practical, expert details: implementation steps, deliverables, pitfalls, "
                "  'what good looks like', and 3-6 FAQs.\n"
                "- Improve scannability with lists and short subsections.\n"
                "- Internal links must use placeholders in this format: internal://<slug>\n"
                "- Do NOT include any domain in links. Do NOT invent slugs not present in context.\n\n"
                "Return ONLY JSON with keys: meta_title, meta_description, focus_keyword, body_html."
            ),
        }

        raw = self._chat([system, user])
        return json.loads(raw)

    def generate_root_page(self, site_description: str) -> Dict[str, Any]:
        """
        Returns JSON with fields:
        {
          "title": "...",
          "meta_title": "...",
          "meta_description": "...",
          "focus_keyword": "...",
          "body_html": "<h1>...</h1> ...",
          "children": [
            {"title": "...", "short_description": "..."},
            ...
          ]
        }
        """
        system = {
            "role": "system",
            "content": (
                "You are an expert SEO web copywriter. "
                "You generate semantic, accessibility-friendly HTML for static websites. "
                "Always respond with valid JSON only."
            ),
        }
        user = {
            "role": "user",
            "content": (
                "Create the root/landing page for a marketing website based on this description:\n"
                f"{site_description}\n\n"
                "Critical strategy:\n"
                "- Prefer fewer pages with deeper content. Make the home page strong and section-rich.\n"
                "- When you include internal links, use placeholders: internal://<slug>\n"
                "  Example: internal://services\n\n"
                "Requirements:\n"
                "- Provide a JSON object with keys: title, meta_title, meta_description, "
                "focus_keyword, body_html, children.\n"
                "- body_html must contain a single <h1> and use <h2>/<h3> "
                "for sections. Use semantic HTML (sections, lists, etc.).\n"
                "- children is an array of up to 3 child pages, each with title and short_description.\n"
                "- Optimize for SEO and clarity. Include concrete specifics: processes, deliverables, "
                "and common pitfalls.\n"
            ),
        }
        raw = self._chat([system, user])
        return json.loads(raw)

    def generate_children_for_page(
        self,
        site_context: Dict[str, Any],
        parent_page: Dict[str, Any],
        remaining_slots: int,
    ) -> Dict[str, Any]:
        """
        Returns JSON:
        {
          "children": [
            {
              "title": "...",
              "meta_title": "...",
              "meta_description": "...",
              "focus_keyword": "...",
              "body_html": "<h1>...</h1> ..."
            },
            ...
          ]
        }
        """
        system = {
            "role": "system",
            "content": (
                "You are an expert SEO web copywriter generating subpages "
                "for a static site. Always return JSON only."
            ),
        }

        # Build an explicit slug allowlist for link safety
        allowed_slugs = []
        try:
            allowed_slugs = [p.get("slug") for p in (site_context.get("pages") or []) if p.get("slug")]
        except Exception:
            allowed_slugs = []

        user = {
            "role": "user",
            "content": (
                "You are expanding a static marketing site.\n\n"
                "SITE CONTEXT:\n"
                f"{site_context}\n\n"
                "PARENT PAGE:\n"
                f"{parent_page}\n\n"
                f"Create up to {remaining_slots} child pages.\n\n"
                "Rules:\n"
                "- Prefer creating fewer child pages. Only create a child page if it represents a distinct intent.\n"
                "- Each page should feel expert and useful, not generic.\n"
                "- Internal links must use placeholders: internal://<slug>\n"
                "- Only link to existing slugs from this allowlist:\n"
                f"{allowed_slugs}\n\n"
                "For each child, return: title, meta_title, meta_description, focus_keyword, body_html.\n"
                "body_html should:\n"
                "- have a single <h1>\n"
                "- include at least 6 <h2> sections for pillar-like pages\n"
                "- include practical details (steps, checklists, pitfalls, FAQs)\n"
                "- include a clear CTA.\n\n"
                "Return JSON: { \"children\": [ ... ] }."
            ),
        }
        raw = self._chat([system, user])
        return json.loads(raw)

    def regenerate_page_content(
        self,
        site_context: Dict[str, Any],
        page: Dict[str, Any],
        parent_page: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Regenerate ONE page's content.
        Returns JSON with keys:
          meta_title, meta_description, focus_keyword, body_html
        """
        system = {
            "role": "system",
            "content": (
                "You are an expert SEO web copywriter. "
                "You generate semantic, accessibility-friendly HTML for static websites. "
                "Always respond with valid JSON only."
            ),
        }

        allowed_slugs = []
        try:
            allowed_slugs = [p.get("slug") for p in (site_context.get("pages") or []) if p.get("slug")]
        except Exception:
            allowed_slugs = []

        user = {
            "role": "user",
            "content": (
                "Regenerate the content for this page in a static marketing site.\n\n"
                "SITE CONTEXT:\n"
                f"{site_context}\n\n"
                "PAGE:\n"
                f"{page}\n\n"
                "PARENT PAGE:\n"
                f"{parent_page}\n\n"
                "Requirements:\n"
                "- Return ONLY a JSON object with keys: meta_title, meta_description, focus_keyword, body_html.\n"
                "- body_html must contain exactly ONE <h1> and use <h2>/<h3> for sections.\n"
                "- Use semantic HTML (sections, lists, etc.) and include a clear CTA.\n"
                "- Add expert specifics: steps, deliverables, pitfalls, FAQs.\n"
                "- Internal links must use placeholders: internal://<slug>\n"
                "- Only link to existing slugs from this allowlist:\n"
                f"{allowed_slugs}\n"
            ),
        }

        raw = self._chat([system, user])
        return json.loads(raw)

    def generate_landing_sections(
        self,
        site_description: str,
        page_title: str = "Home",
    ) -> List[Dict[str, Any]]:
        """
        Generate a marketing landing page as an ordered list of section blocks
        (assigned to Page.landing_sections). Returns a list.

        Block schema (each item has a "type"):
          hero     {eyebrow, headline, subhead, primary_cta:{label,href}, secondary_cta:{label,href}}
          stats    {items:[{value,label}]}
          features {heading, subhead?, items:[{title,text}]}
          cards    {heading, items:[{title,text,href?}]}
          cta      {heading, text, button:{label,href}}
        """
        system = {
            "role": "system",
            "content": (
                "You are a senior web designer and conversion copywriter. You output the JSON "
                "for a marketing landing page as an ordered list of section blocks. "
                'Respond with ONLY valid JSON: {"sections": [ ... ]}. '
                "Allowed block types: hero, stats, features, cards, cta. "
                "Start with exactly one hero. Use 3-4 stats, 3-6 features, 3 cards, one closing cta. "
                "Copy must be concise and benefit-led. "
                "All internal hrefs MUST use internal://<slug> placeholders for real pages, "
                "for example internal://contact or internal://services. Never invent a .html filename. "
                "Use section anchors only when the section exists in this JSON and has a matching id. "
                "Never use absolute URLs or external domains. Do NOT include or invent image paths/URLs. "
                "Sections may include an 'eyebrow' kicker. For card badges, badge_color must be "
                "one of: green, blue, amber, pink, accent. "
                "The hero MUST include 'headline_accent': a 1-3 word phrase that appears VERBATIM "
                "inside 'headline' (it gets a gradient highlight). "
                "Card items: add an emoji 'icon' for concept/capability cards; OMIT 'icon' on "
                "showcase/portfolio cards (those automatically receive a generated image)."
            ),
        }
        example = (
            '{"sections":['
            '{"type":"hero","eyebrow":"SHORT BRAND TAG","headline":"Big benefit-led headline",'
            '"headline_accent":"benefit-led",'
            '"subhead":"One or two supporting sentences.","primary_cta":{"label":"Get started","href":"internal://contact"},'
            '"secondary_cta":{"label":"Learn more","href":"internal://services"}},'
            '{"type":"stats","items":[{"value":"500+","label":"Customers","sublabel":"Across 30 countries"},{"value":"24h","label":"Turnaround","sublabel":"Order to delivery"}]},'
            '{"type":"features","eyebrow":"CAPABILITIES","heading":"What we offer","subhead":"Optional intro line.",'
            '"items":[{"title":"Feature name","text":"What it does for the customer."}]},'
            '{"type":"cards","eyebrow":"OUR WORK","heading":"Our work",'
            '"items":[{"title":"Card title","badge":"Status","badge_color":"green","text":"Short blurb.","href":"internal://services","link_label":"Learn more"}]},'
            '{"type":"cta","heading":"Ready to start?","text":"Closing line.","button":{"label":"Contact us","href":"internal://contact"}}'
            ']}'
        )
        user = {
            "role": "user",
            "content": (
                f"Business / site description:\n{site_description}\n\n"
                f"Page: {page_title} (the site home page).\n\n"
                "Use EXACTLY these keys (copy the structure, replace the values):\n"
                f"{example}\n\n"
                "Generate the landing sections JSON now."
            ),
        }
        raw = self._chat([system, user])
        data = json.loads(raw)
        sections = data.get("sections") or data.get("landing_sections") or []
        return sections if isinstance(sections, list) else []
