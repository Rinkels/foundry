from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites_builder", "0028_humainx_content_primitives"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="reader_feedback_config",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Public reader-feedback configuration. Expected keys include "
                    "enabled, provider, form_url, and button_label. No API "
                    "credentials are required."
                ),
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="feedback_identifier",
            field=models.CharField(
                blank=True,
                help_text="Stable public feedback identifier, for example HX01.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="reader_question",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Optional reader-response question displayed at the end of "
                    "the article."
                ),
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="reader_answer_options",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Optional ordered list of display-only reader answer options."
                ),
            ),
        ),
    ]
