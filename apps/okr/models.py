# apps/okr/models.py
from django.utils.text import slugify
from django.conf import settings
from django.db import models
class Entity(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def progress(self):
        if self.target_value:
            return (self.current_value / self.target_value) * 100
        return 0
# models.py

class Strategy(models.Model):
    entity = models.ForeignKey(
        'Entity',
        on_delete=models.CASCADE,
        related_name='strategies',
        null=True,  # Optional for backwards compatibility
        blank=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    theme = models.CharField(
        max_length=50,
        choices=[
            ('green', 'Green'),
            ('blue', 'Blue'),
            ('orange', 'Orange'),
            ('purple', 'Purple'),
            ('red', 'Red'),
            ('gray', 'Gray'),
        ],
        default='gray'
    )

    def __str__(self):
        return self.name


# Then update your existing Objective model:
class Objective(models.Model):
    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name='objectives',
        null=True,  # Initially allow null to prevent migration issues
        blank=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    completed = models.BooleanField(default=False)


class KeyResult(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_value = models.FloatField()
    current_value = models.FloatField(default=0)
    unit = models.CharField(max_length=20)
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name='key_results'
    )

    @property
    def progress(self):
        if self.target_value:
            return (self.current_value / self.target_value) * 100
        return 0

    @property
    def execution_progress(self):
        total_tasks = 0
        done_tasks = 0
        print("Key Result Progress:")
        for epic in self.epics.prefetch_related("stories__tasks").all():
            for story in epic.stories.all():
                for task in story.tasks.all():
                    total_tasks += 1
                    if task.status == "Done":
                        done_tasks += 1

        if total_tasks == 0:
            return 0

        return (done_tasks / total_tasks) * 100

class ProgressUpdate(models.Model):
    key_result = models.ForeignKey(KeyResult, related_name='updates', on_delete=models.CASCADE)
    update_date = models.DateField(auto_now_add=True)
    note = models.TextField()
    progress_value = models.FloatField()

    def __str__(self):
        return f"Update on {self.update_date} for {self.key_result.name}"

class Epic(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    key_result = models.ForeignKey(KeyResult, on_delete=models.CASCADE, related_name="epics")    # no null=True, no blank=True
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Story(models.Model):
    epic = models.ForeignKey(Epic, on_delete=models.CASCADE, related_name='stories')
    title = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    goal = models.TextField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Done', 'Done'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    assigned_to = models.CharField(max_length=255, blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    assigned_to = models.CharField(max_length=255, blank=True, null=True)  # keep for now
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="okr_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class MetricDimension(models.Model):
    """
    A flexible catalog of scorecard dimensions (e.g. availability, latency, security, docs, adoption, etc).
    Not restrictive: you can add new dimensions any time in admin.
    """
    key = models.SlugField(max_length=80, unique=True, help_text="Stable machine key, e.g. 'availability', 'latency'")
    name = models.CharField(max_length=120, help_text="Display name, e.g. 'Availability'")
    description = models.TextField(blank=True)

    # Optional grouping, useful for reporting
    category = models.CharField(max_length=120, blank=True, help_text="e.g. 'Reliability', 'Security', 'Adoption'")

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.key and self.name:
            self.key = slugify(self.name)[:80]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class KeyResultMetric(models.Model):
    """
    Per-KeyResult measurement for a single Dimension.
    Example: KR=API Reliability, Dimension=Availability, target=99.95, current=99.91, unit='%'
    """
    POLARITY_CHOICES = [
        ("higher_is_better", "Higher is better"),
        ("lower_is_better", "Lower is better"),
        ("target_is_best", "Target is best"),
    ]

    VALUE_TYPE_CHOICES = [
        ("number", "Number"),
        ("percent", "Percent"),
        ("currency", "Currency"),
        ("count", "Count"),
        ("boolean", "Pass/Fail"),
        ("score", "Score"),
        ("text", "Text"),
    ]

    key_result = models.ForeignKey("KeyResult", on_delete=models.CASCADE, related_name="metrics")
    dimension = models.ForeignKey(MetricDimension, on_delete=models.PROTECT, related_name="kr_metrics")

    # measurement
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default="number")
    unit = models.CharField(max_length=30, blank=True, help_text="e.g. ms, %, tickets, integrations")

    target_value = models.FloatField(null=True, blank=True)
    current_value = models.FloatField(null=True, blank=True)

    # optional R/Y/G thresholds for status evaluation
    threshold_green = models.FloatField(null=True, blank=True)
    threshold_yellow = models.FloatField(null=True, blank=True)
    threshold_red = models.FloatField(null=True, blank=True)

    polarity = models.CharField(max_length=20, choices=POLARITY_CHOICES, default="higher_is_better")

    # display/reporting
    weight = models.FloatField(default=1.0, help_text="Optional weight for rollups")
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("key_result", "dimension")
        ordering = ["dimension__sort_order", "dimension__name"]

    def __str__(self):
        return f"{self.key_result.name} · {self.dimension.name}"

    def progress_ratio(self):
        """
        Generic progress ratio, used for charts/rollups.
        Returns a 0..1 float when numeric target/current exist, else None.
        """
        if self.target_value in (None, 0) or self.current_value is None:
            return None
        return max(0.0, min(1.0, float(self.current_value) / float(self.target_value)))

    def status_rag(self):
        """
        Optional R/Y/G. Only applies when thresholds + current exist.
        Polarity aware for higher/lower is better.
        """
        cv = self.current_value
        if cv is None:
            return "gray"

        g, y, r = self.threshold_green, self.threshold_yellow, self.threshold_red
        if g is None and y is None and r is None:
            return "gray"

        if self.polarity == "lower_is_better":
            # lower is better: green if <= green threshold, red if > red threshold
            if g is not None and cv <= g:
                return "green"
            if r is not None and cv > r:
                return "red"
            if y is not None and cv <= y:
                return "yellow"
            return "gray"

        # default higher is better
        if g is not None and cv >= g:
            return "green"
        if r is not None and cv < r:
            return "red"
        if y is not None and cv >= y:
            return "yellow"
        return "gray"
