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
from .services.reading_time import estimate_reading_minutes
from .services.static_builder import StaticBuilder, THEME_CSS_MAP
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
        self.site.save(update_fields=["newsletter_config"])
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
        self.assertIn("Before the factory", article.body_md)
        self.assertEqual(
            self.site.newsletter_config["form_action"],
            "https://buttondown.com/api/emails/embed-subscribe/HumainX",
        )
        self.assertEqual(self.site.newsletter_config["analytics_label"], "keep-me")
