# apps/common/models_ai.py
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class AiUsageEvent(models.Model):
    # Generic link to “the thing this run was for” (Task, Objective, PromptVersion, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    action = models.CharField(max_length=80)          # "analyze_attachments", "athena_prompt", "scan_project"
    model = models.CharField(max_length=80, blank=True)

    # Token usage
    input_tokens = models.IntegerField(default=0)
    cached_input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    reasoning_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    # Costs
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    tool_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)  # non-token fees (optional)
    other_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0) # future-proof

    meta = models.JSONField(default=dict, blank=True)  # file_count, prompt_hash, response_id, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost_usd(self):
        return (self.cost_usd or 0) + (self.tool_cost_usd or 0) + (self.other_cost_usd or 0)
