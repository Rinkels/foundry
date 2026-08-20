from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from .models import Developer, EvergreenArticle, Page, Site, SiteTopNavItem
from .services.generator import SiteGenerator
from .services.reader_feedback import build_reader_feedback_context
from .services.reading_time import estimate_reading_minutes
from .services.static_builder import StaticBuilder, THEME_CSS_MAP, THEME_FAVICON_MAP
from .views import _build_page_tree, _site_content_digest


class SitesBuilderTestCase(TestCase):
    def setUp(self):
        self.developer = Developer.objects.create(name="Test Developer")
        self.site = Site.objects.create(
            owner=self.developer,
            name="Test Site",
            slug="test-site",
            description="A test site.",
        )


class SiteModelTests(SitesBuilderTestCase):
    def test_base_url_adds_default_scheme_and_removes_path(self):
        self.site.domain = "example.com/a/path"

        self.assertEqual(self.site.base_url, "https://example.com")

    def test_page_generates_a_unique_slug_within_site(self):
        Page.objects.create(site=self.site, title="About")

        second = Page.objects.create(site=self.site, title="About")

        self.assertEqual(second.slug, "about-2")

    def test_builder_credit_is_visible_by_default_and_can_be_hidden(self):
        template = "sites_builder/sites/default/partials/footer.html"

        visible = render_to_string(template, {"site": self.site, "rel_root": ""})
        self.site.hide_builder_credit = True
        hidden = render_to_string(template, {"site": self.site, "rel_root": ""})

        self.assertIn("Built by", visible)
        self.assertNotIn("Built by", hidden)

    def test_every_selectable_theme_has_a_builder_mapping(self):
        choices = dict(Site._meta.get_field("theme_css").choices)

        self.assertEqual(set(choices), set(THEME_CSS_MAP))
        self.assertEqual(THEME_CSS_MAP["bauhaus"], "bauhaus.css")
        self.assertEqual(THEME_FAVICON_MAP["mindsgate"], "mindsgate-favicon.svg")

    def test_article_editorial_labels_are_general_and_series_aware(self):
        normal = EvergreenArticle(site=self.site)
        humainx = EvergreenArticle(
            site=self.site,
            series="HumainX",
            series_number=1,
        )

        self.assertEqual(normal.editorial_label, "INSIGHT")
        self.assertEqual(humainx.editorial_label, "HUMAINX / 01")

    def test_reading_time_counts_only_article_text(self):
        body = "<nav>" + " ".join(["word"] * 225) + "</nav><script>ignored()</script> plus"

        self.assertEqual(estimate_reading_minutes(body), 2)
        self.assertEqual(estimate_reading_minutes(""), 1)


class ViewHelperTests(SitesBuilderTestCase):
    def test_page_tree_nests_children_under_their_parent(self):
        root = Page.objects.create(site=self.site, title="Home", is_root=True)
        child = Page.objects.create(site=self.site, title="About", parent=root, depth=1)

        tree = _build_page_tree([root, child])

        self.assertEqual([node["page"] for node in tree], [root])
        self.assertEqual(tree[0]["children"][0]["page"], child)

    def test_site_content_digest_uses_page_body_html(self):
        Page.objects.create(
            site=self.site,
            title="Services",
            body_html="<p>Useful implementation details.</p>",
        )

        digest = _site_content_digest(self.site)

        self.assertIn("Useful implementation details", digest)


class GeneratorTests(SitesBuilderTestCase):
    def test_ia_planning_reuses_a_same_title_page_and_applies_planned_slug(self):
        root = Page.objects.create(site=self.site, title="Home", is_root=True)
        existing = Page.objects.create(
            site=self.site,
            title="Services",
            slug="old-services",
            parent=root,
            depth=1,
        )
        gpt = Mock()
        gpt.generate_site_ia.return_value = {
            "nav": [{"title": "Services", "slug": "services", "children": []}],
            "pages": [],
        }

        SiteGenerator(gpt=gpt)._ensure_site_ia(self.site)

        existing.refresh_from_db()
        self.assertEqual(existing.slug, "services")
        self.assertEqual(self.site.pages.count(), 2)


class StaticBuilderTests(SitesBuilderTestCase):
    def test_mindsgate_favicon_is_injected_with_depth_aware_path(self):
        builder = StaticBuilder()
        html = "<html><head><title>Test</title></head><body></body></html>"

        root = builder._inject_theme_favicon(html, "mindsgate")
        nested = builder._inject_theme_favicon(html, "mindsgate", rel_root="../")

        self.assertIn('href="assets/images/favicon.svg"', root)
        self.assertIn('href="../assets/images/favicon.svg"', nested)
        self.assertEqual(
            builder._inject_theme_favicon(root, "mindsgate").count('rel="icon"'),
            1,
        )

    def test_mindsgate_favicon_is_copied_to_generated_assets(self):
        with TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir) / self.site.slug

            StaticBuilder(Path(temp_dir))._copy_theme_favicon(site_dir, "mindsgate")

            favicon = site_dir / "assets" / "images" / "favicon.svg"
            favicon_jpg = site_dir / "assets" / "images" / "favicon.jpg"
            self.assertTrue(favicon.is_file())
            self.assertIn("HumainX", favicon.read_text(encoding="utf-8"))
            self.assertTrue(favicon_jpg.is_file())
            self.assertTrue(favicon_jpg.read_bytes().startswith(b"\xff\xd8\xff"))

    def test_article_wrapper_uses_valid_body_and_main_attributes(self):
        article = EvergreenArticle.objects.create(
            site=self.site,
            title="A useful article",
            slug="useful-article",
            status=EvergreenArticle.STATUS_PUBLISHED,
            body_md="Article body.",
        )

        html = StaticBuilder()._render_article_html(self.site, article, "test-build")

        self.assertIn('<body class="theme-neon_glass article-page">', html)
        self.assertIn('<main id="article-main" class="container" style="flex:1 0 auto;', html)
        self.assertIn("INSIGHT &middot; 1 min read", html)

    def test_curated_html_article_body_is_not_rewritten_as_markdown(self):
        article = EvergreenArticle.objects.create(
            site=self.site,
            title="Curated",
            status=EvergreenArticle.STATUS_PUBLISHED,
            body_md='<div class="editorial-component"><span>Exact</span></div>',
        )

        html = StaticBuilder()._render_article_html(self.site, article, "test-build")

        self.assertIn(
            '<div class="editorial-component"><span>Exact</span></div>', html
        )

    def test_article_local_image_paths_are_relative_to_insights_directory(self):
        self.site.domain = "example.com"
        self.site.save()
        article = EvergreenArticle.objects.create(
            site=self.site,
            title="Illustrated",
            status=EvergreenArticle.STATUS_PUBLISHED,
            hero_image_url="assets/images/insights.png",
        )

        with TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / self.site.slug / "assets" / "images" / "insights.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"test image")
            html = StaticBuilder(Path(temp_dir))._render_article_html(
                self.site, article, "test-build"
            )

        self.assertIn('src="../assets/images/insights.png"', html)
        self.assertIn(
            'property="og:image" content="https://example.com/assets/images/insights.png"',
            html,
        )

    def test_humainx_landing_uses_native_configured_newsletter_form(self):
        self.site.newsletter_config = {
            "enabled": True,
            "provider": "buttondown",
            "form_action": "https://buttondown.com/example",
            "button_label": "Follow HumainX",
        }
        self.site.save()
        page = Page.objects.create(
            site=self.site,
            title="HumainX",
            slug="humainx",
            template_variant=Page.TEMPLATE_HUMAINX,
        )

        html = render_to_string(
            "sites_builder/sites/default/humainx.html",
            {"site": self.site, "page": page, "theme": "mindsgate", "rel_root": ""},
        )

        self.assertIn("What happens when intelligence is", html)
        self.assertIn('action="https://buttondown.com/example"', html)
        self.assertIn('name="email"', html)
        self.assertIn("Follow HumainX", html)

    def test_humainx_article_gets_feedback_and_newsletter_components(self):
        self.site.newsletter_config = {
            "enabled": True,
            "provider": "buttondown",
            "form_action": "https://buttondown.com/example",
            "button_label": "Follow HumainX",
            "series": "HumainX",
            "article_anchor": "follow-humainx",
            "article_link_label": "Follow HumainX",
            "section_description": "Follow the evidence toward 2036.",
        }
        self.site.reader_feedback_config = {
            "enabled": True,
            "provider": "tally",
            "form_url": "https://tally.so/r/example?ref=mindsgate",
            "button_label": "Share your reasoning →",
        }
        self.site.save()
        article = EvergreenArticle.objects.create(
            site=self.site,
            title="A HumainX argument",
            status=EvergreenArticle.STATUS_PUBLISHED,
            series="HumainX",
            series_number=1,
            hypothesis="H1",
            feedback_identifier="HX01",
            reader_question="What happens next?",
            reader_answer_options=["Option one", "Option two"],
            body_md=(
                "<p>Argument.</p><!-- reader-response -->"
                '<h2 class="humainx-sources-title">Sources</h2>'
            ),
        )

        html = StaticBuilder()._render_article_html(self.site, article, "test-build")

        self.assertIn('href="#follow-humainx">Follow HumainX</a>', html)
        self.assertIn('id="follow-humainx"', html)
        self.assertIn('action="https://buttondown.com/example"', html)
        self.assertIn("What happens next?", html)
        self.assertIn("Option one", html)
        self.assertIn("Share your reasoning →", html)
        self.assertIn("article=HX01", html)
        self.assertIn("series=HumainX", html)
        self.assertIn("hypothesis=H1", html)
        self.assertLess(html.index("What happens next?"), html.index('id="follow-humainx"'))
        self.assertLess(html.index('id="follow-humainx"'), html.index("Sources"))

    def test_feedback_cta_remains_visible_until_tally_url_is_configured(self):
        self.site.newsletter_config = {
            "enabled": True,
            "provider": "buttondown",
            "form_action": "https://buttondown.com/example",
            "series": "HumainX",
        }
        self.site.reader_feedback_config = {
            "enabled": False,
            "provider": "tally",
            "form_url": "",
            "button_label": "Share your reasoning →",
        }
        self.site.save()
        article = EvergreenArticle.objects.create(
            site=self.site,
            title="Pending feedback form",
            status=EvergreenArticle.STATUS_PUBLISHED,
            series="HumainX",
            reader_question="What do you think?",
        )

        html = StaticBuilder()._render_article_html(self.site, article, "test-build")

        self.assertIn("Share your reasoning →", html)
        self.assertIn('aria-disabled="true"', html)


class ReaderFeedbackTests(SitesBuilderTestCase):
    def test_tally_hidden_fields_are_appended_without_discarding_existing_query(self):
        article = EvergreenArticle(
            site=self.site,
            series="HumainX",
            hypothesis="H1",
            feedback_identifier="HX01",
        )

        feedback = build_reader_feedback_context(
            article,
            {
                "enabled": True,
                "provider": "tally",
                "form_url": "https://tally.so/r/example?ref=mindsgate",
                "button_label": "Share your reasoning →",
            },
        )

        self.assertTrue(feedback["enabled"])
        self.assertEqual(
            feedback["url"],
            "https://tally.so/r/example?ref=mindsgate&article=HX01&series=HumainX&hypothesis=H1",
        )

    def test_feedback_link_requires_enabled_tally_https_configuration(self):
        article = EvergreenArticle(site=self.site, feedback_identifier="HX01")

        disabled = build_reader_feedback_context(
            article,
            {"enabled": False, "provider": "tally", "form_url": "https://tally.so/r/x"},
        )
        invalid = build_reader_feedback_context(
            article,
            {"enabled": True, "provider": "tally", "form_url": "javascript:alert(1)"},
        )

        self.assertFalse(disabled["enabled"])
        self.assertFalse(invalid["enabled"])


class SiteViewTests(SitesBuilderTestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username="builder-user",
            password="test-password",
        )
        self.client.force_login(self.user)

    @patch("apps.sites_builder.views.SiteGenerator")
    def test_expand_uses_requested_page_limit(self, generator_class):
        generator_class.return_value.expand_site.return_value = 2

        response = self.client.post(
            reverse("sites_builder:site_expand", args=[self.site.pk]),
            {"max_new_pages": "3"},
        )

        self.assertEqual(response.status_code, 302)
        args, kwargs = generator_class.return_value.expand_site.call_args
        self.assertEqual(args[0].pk, self.site.pk)
        self.assertEqual(kwargs, {"max_new_pages": 3})


class ManagementCommandTests(SitesBuilderTestCase):
    @patch("apps.sites_builder.management.commands.expand_site.SiteGenerator")
    def test_expand_command_uses_requested_page_limit(self, generator_class):
        generator_class.return_value.expand_site.return_value = 2

        call_command(
            "expand_site",
            self.site.slug,
            max_new_pages=4,
            stdout=StringIO(),
        )

        args, kwargs = generator_class.return_value.expand_site.call_args
        self.assertEqual(args[0].pk, self.site.pk)
        self.assertEqual(kwargs, {"max_new_pages": 4})

    @patch("apps.sites_builder.management.commands.init_site.SiteGenerator")
    def test_init_site_command_has_all_required_dependencies(self, generator_class):
        generator_class.return_value.ensure_root_page.return_value = Mock(title="Home")

        call_command(
            "init_site",
            "New Developer",
            "New Site",
            "A new site.",
            stdout=StringIO(),
        )

        created = Site.objects.get(slug="new-site")
        self.assertEqual(created.owner.name, "New Developer")
        generator_class.return_value.ensure_root_page.assert_called_once()

    @patch("apps.sites_builder.management.commands.backfill_hero_images.ImageGenerator")
    def test_backfill_command_imports_and_runs_without_pages(self, image_generator):
        call_command(
            "backfill_hero_images",
            self.site.slug,
            stdout=StringIO(),
        )

        image_generator.assert_called_once()

    def test_setup_humainx_is_idempotent_and_populates_foundry_content(self):
        self.site.newsletter_config = {"analytics_label": "keep-me"}
        self.site.reader_feedback_config = {"tracking_label": "keep-feedback"}
        self.site.save(
            update_fields=["newsletter_config", "reader_feedback_config"]
        )
        Page.objects.create(
            site=self.site,
            title="Home",
            slug="home",
            is_root=True,
        )

        for _ in range(2):
            call_command(
                "setup_humainx",
                site_slug=self.site.slug,
                no_build=True,
                stdout=StringIO(),
            )

        self.site.refresh_from_db()
        page = self.site.pages.get(slug="humainx")
        article = self.site.evergreen_articles.get(
            slug="the-second-cottage-revolution"
        )
        nav = SiteTopNavItem.objects.get(site=self.site, label="HumainX")

        self.assertEqual(self.site.pages.filter(slug="humainx").count(), 1)
        self.assertEqual(
            self.site.evergreen_articles.filter(slug=article.slug).count(), 1
        )
        self.assertEqual(page.template_variant, Page.TEMPLATE_HUMAINX)
        self.assertEqual(nav.url, "humainx.html")
        self.assertEqual(article.editorial_label, "HUMAINX / 01")
        self.assertEqual(article.hypothesis, "H1")
        self.assertEqual(article.feedback_identifier, "HX01")
        self.assertEqual(len(article.reader_answer_options), 5)
        self.assertIn("single employer", article.reader_question)
        self.assertIn("Before the factory", article.body_md)
        self.assertIn("<!-- reader-response -->", article.body_md)
        self.assertEqual(
            self.site.newsletter_config["form_action"],
            "https://buttondown.com/api/emails/embed-subscribe/HumainX",
        )
        self.assertEqual(self.site.newsletter_config["analytics_label"], "keep-me")
        self.assertEqual(self.site.reader_feedback_config["provider"], "tally")
        self.assertEqual(
            self.site.reader_feedback_config["tracking_label"], "keep-feedback"
        )
        self.assertTrue(self.site.reader_feedback_config["enabled"])
        self.assertEqual(
            self.site.reader_feedback_config["form_url"],
            "https://tally.so/r/kd8gJZ",
        )
