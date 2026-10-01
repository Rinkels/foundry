from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites_builder", "0030_article_seo_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="theme_css",
            field=models.CharField(
                choices=[
                    ("neon_glass", "Neon Glass"),
                    ("startup", "Startup Modern"),
                    ("aurora", "Aurora"),
                    ("verdant", "Verdant"),
                    ("bauhaus", "Bauhaus"),
                    ("editorial", "Editorial"),
                    ("mindsgate", "Mindsgate (dark premium)"),
                    ("humainx", "HumainX (research publication)"),
                ],
                default="neon_glass",
                help_text="Select the source theme stylesheet to copy into assets/css/site.css",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="page",
            name="template_variant",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Default for page type"),
                    ("humainx", "HumainX landing page"),
                    ("humainx_home", "HumainX standalone home page"),
                    ("neo_cottage", "Neo-Cottage definition page"),
                ],
                default="",
                help_text="Optional curated template variant used by the static builder.",
                max_length=50,
            ),
        ),
    ]
