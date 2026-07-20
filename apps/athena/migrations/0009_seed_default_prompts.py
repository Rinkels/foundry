# apps/athena/migrations/0009_seed_default_prompts.py
from django.db import migrations


def _backfill_roles(apps):
    """Assign roles to pre-existing prompts using the old key/name heuristic."""
    PromptTemplate = apps.get_model("athena", "PromptTemplate")
    for tpl in PromptTemplate.objects.filter(role="none"):
        k = (tpl.key or "").lower()
        n = (tpl.name or "").lower()
        if "impl" in k or "implementation" in n:
            role = "impl_generator"
        elif "feature-designer" in k or "feature designer" in n:
            role = "feature_designer"
        elif "app-builder" in k or "django-app-builder" in k or "app builder" in n:
            role = "app_builder"
        else:
            continue
        tpl.role = role
        tpl.save(update_fields=["role"])


def forwards(apps, schema_editor):
    from apps.athena.services.seeds import ensure_default_prompts

    PromptTemplate = apps.get_model("athena", "PromptTemplate")
    PromptVersion = apps.get_model("athena", "PromptVersion")

    _backfill_roles(apps)
    ensure_default_prompts(PromptTemplate, PromptVersion)


def backwards(apps, schema_editor):
    # Remove only the seeded canonical prompt; leave user prompts/roles untouched.
    PromptTemplate = apps.get_model("athena", "PromptTemplate")
    PromptTemplate.objects.filter(key="athena-impl-generator").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("athena", "0008_prompttemplate_role_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
