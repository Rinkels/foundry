import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ImageGenerator:

    def __init__(self, base_output_dir: Path):
        self.base_output_dir = base_output_dir

    IMG_MODEL = "gpt-image-1"
    IMG_SIZE = "1536x1024"
    IMG_QUALITY = "high"

    def generate_page_hero(self, site_slug: str, page_slug: str, page_context: str,
                           usage_obj=None, usage_action: str = "image_hero") -> str:
        """
        Generates a polished, high-resolution hero image and saves it.
        Returns the relative path to the saved image, e.g. 'assets/images/my-page.png'.
        If `usage_obj` (a Site/Page) is given, the image spend is logged to the
        shared AI ledger.
        """

        # (1) Build prompt for a concrete, production-ready visual
        prompt = (
            f"Create a high-resolution, production-ready wide website hero image. "
            f"The internal page slug is '{page_slug}', but do not render that slug, title, or any words in the image. "
            f"Use this context only as the visual brief, not as text to display: '{page_context}'. "
            "Make the image concrete and specific to the topic, using realistic environments, products, tools, "
            "workspaces, materials, or subject-matter details that a visitor would immediately recognize. "
            "Do not include any typography of any kind: no titles, labels, captions, signs, posters, packaging text, "
            "screen text, UI text, numbers, letters, logos, watermarks, QR codes, barcodes, handwriting, or symbols "
            "that resemble readable text. If the scene includes screens, tags, packaging, dashboards, or documents, "
            "keep them blank, blurred, turned away, or represented with non-readable abstract marks only. "
            "Avoid abstract geometric backgrounds, generic gradients, vague digital shapes, and stock-photo clichés. "
            "Compose it as a premium editorial/commercial banner with crisp focus, natural lighting, rich texture, "
            "balanced depth, centered subject matter, and generous safe margins so important visual details are not "
            "cropped when displayed in cards or hero layouts. "
            "Use a modern professional color palette matched to the page context. "
            "The final image should look sharp, detailed, realistic, text-free, and ready for a polished business website."
        )

        # (2) Call OpenAI image generation
        result = client.images.generate(
            model=self.IMG_MODEL,
            prompt=prompt,
            size=self.IMG_SIZE,
            quality=self.IMG_QUALITY,
        )

        # (3) Decode base64 output
        image_bytes = result.data[0].b64_json
        import base64
        image_data = base64.b64decode(image_bytes)

        # (4) Save into output directory
        image_dir = self.base_output_dir / site_slug / "assets" / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{page_slug}.png"
        filepath = image_dir / filename

        with open(filepath, "wb") as f:
            f.write(image_data)

        # (5) Log the image spend to the shared AI ledger (best-effort)
        if usage_obj is not None:
            try:
                from apps.sites_builder.services.usage import record_image_usage
                record_image_usage(
                    obj=usage_obj, action=usage_action, model=self.IMG_MODEL,
                    size=self.IMG_SIZE, quality=self.IMG_QUALITY,
                    meta={"site_slug": site_slug, "page_slug": page_slug},
                )
            except Exception as e:
                print(f"[WARN] Failed to log image usage: {e}")

        # Return relative URL for HTML <img src="...">
        return f"assets/images/{filename}"
