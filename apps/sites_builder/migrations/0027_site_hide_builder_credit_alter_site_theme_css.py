from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sites_builder", "0026_deploymenttarget_cf_project_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="hide_builder_credit",
            field=models.BooleanField(
                default=False,
                help_text="Hide the Mindsgate builder credit in the generated site footer.",
            ),
        ),
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
                ],
                default="neon_glass",
                help_text="Select the source theme stylesheet to copy into assets/css/site.css",
                max_length=50,
            ),
        ),
    ]
