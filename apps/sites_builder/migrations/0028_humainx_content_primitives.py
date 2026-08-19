from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites_builder", "0027_site_hide_builder_credit_alter_site_theme_css"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="newsletter_config",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Public newsletter-form configuration. Expected keys include enabled, "
                    "provider, username, form_action, button_label, and success_url."
                ),
            ),
        ),
        migrations.AddField(
            model_name="page",
            name="template_variant",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Default for page type"),
                    ("humainx", "HumainX landing page"),
                ],
                default="",
                help_text="Optional curated template variant used by the static builder.",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="series",
            field=models.CharField(
                blank=True,
                help_text="Optional editorial series, for example HumainX.",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="series_number",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Optional sequence number within the editorial series.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="hypothesis",
            field=models.CharField(
                blank=True,
                help_text="Optional hypothesis identifier, for example H1.",
                max_length=20,
            ),
        ),
    ]
