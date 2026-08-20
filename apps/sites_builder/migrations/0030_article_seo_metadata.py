from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites_builder", "0029_reader_feedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="evergreenarticle",
            name="author_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="author_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="content_updated_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Date of the most recent significant editorial update.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="evergreenarticle",
            name="legacy_slugs",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Previous article slugs that should permanently redirect here.",
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
                    ("neo_cottage", "Neo-Cottage definition page"),
                ],
                default="",
                help_text="Optional curated template variant used by the static builder.",
                max_length=50,
            ),
        ),
    ]
