# apps/okr/admin.py
from django.contrib import admin
from .models import Objective, KeyResult, ProgressUpdate, Strategy
#admin.site.register(Objective)
#admin.site.register(KeyResult)
#admin.site.register(ProgressUpdate)
#admin.site.register(Strategy)
from django.contrib import admin
from .models import (
    Entity, Strategy, Objective, KeyResult,
    Epic, Story, Task,
    MetricDimension, KeyResultMetric
)


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

class TaskInline(admin.TabularInline):  # or StackedInline for more detail
    model = Task
    extra = 1  # number of empty task forms shown
    fields = ('title', 'completed', 'assigned_to', 'due_date')
    show_change_link = True

class StoryInline(admin.StackedInline):
    model = Story
    extra = 1
    fields = ('title', 'role', 'goal', 'reason')
    show_change_link = True
    inlines = [TaskInline]  # Not supported — see note below

# Note: You can't nest inlines more than one level deep in standard Django admin.
# So we manage Tasks from within the Story admin instead.

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "story", "status", "due_date", "assigned_to", "completed")
    list_filter = ("status", "completed")
    search_fields = ("title", "notes", "assigned_to", "story__title")

class TaskInlineForStory(admin.TabularInline):
    model = Task
    extra = 1

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("title", "epic", "created_at", "updated_at")
    search_fields = ("title", "role", "goal", "reason", "epic__title")
    list_filter = ("created_at",)
    inlines = [TaskInlineForStory]

    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Tasks'

@admin.register(Epic)
class EpicAdmin(admin.ModelAdmin):
    list_display = ("title", "key_result", "created_at", "updated_at")
    search_fields = ("title", "description", "key_result__name")
    list_filter = ("created_at",)
    inlines = [StoryInline]
    def task_count(self, obj):
        return Task.objects.filter(story__epic=obj).count()
    task_count.short_description = 'Total Tasks'

# ----------------------------
# Scorecard Admin
# ----------------------------

@admin.register(MetricDimension)
class MetricDimensionAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "category", "is_active", "sort_order")
    list_filter = ("is_active", "category")
    search_fields = ("name", "key", "category", "description")
    ordering = ("sort_order", "category", "name")
    prepopulated_fields = {"key": ("name",)}  # optional convenience

    fieldsets = (
        ("Dimension", {"fields": ("name", "key", "category", "description")}),
        ("Display & Status", {"fields": ("sort_order", "is_active")}),
    )


class KeyResultMetricInline(admin.TabularInline):
    model = KeyResultMetric
    extra = 0
    autocomplete_fields = ("dimension",)
    fields = (
        "dimension",
        "value_type", "unit",
        "target_value", "current_value",
        "polarity",
        "threshold_green", "threshold_yellow", "threshold_red",
        "weight",
        "notes",
    )
    show_change_link = True

    # Keeps the inline usable visually
    classes = ("collapse",)  # comment this out if you want always open


@admin.register(KeyResult)
class KeyResultAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "objective", "target_value", "current_value", "unit")
    list_filter = ("unit", "objective__strategy__entity")
    search_fields = ("name", "description", "objective__name", "objective__strategy__name")
    inlines = [KeyResultMetricInline]



@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ("name", "entity", "theme")
    list_filter = ("entity", "theme")
    search_fields = ("name", "description", "entity__name")


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ("name", "strategy", "owner", "start_date", "end_date", "completed")
    list_filter = ("completed", "strategy__entity")
    search_fields = ("name", "description", "owner", "strategy__name")

