from .models import Strategy, Objective, KeyResult, Epic, Entity, Story
from django import forms
from django.contrib.auth import get_user_model
from .models import Task

User = get_user_model()

# Centralize the CSS classes so forms stay consistent
INPUT_GLASS = "input-glass"
TEXTAREA_GLASS = "textarea-glass"

class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        # Make it explicit so the template + JS always have these fields available
        fields = ["entity", "name", "description", "theme"]
        widgets = {
            "entity": forms.Select(attrs={"class": INPUT_GLASS}),
            "name": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 5}),
            "theme": forms.Select(attrs={"class": INPUT_GLASS}),
        }



class ObjectiveForm(forms.ModelForm):
    class Meta:
        model = Objective
        fields = ["name", "description", "owner", "start_date", "end_date"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 7}),
            # owner is typically a ModelChoiceField -> select
            "owner": forms.Select(attrs={"class": INPUT_GLASS}),
            "start_date": forms.DateInput(attrs={"class": INPUT_GLASS, "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": INPUT_GLASS, "type": "date"}),
        }


class KeyResultForm(forms.ModelForm):
    class Meta:
        model = KeyResult
        fields = ["name", "description", "target_value", "unit"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 5}),
            "target_value": forms.NumberInput(attrs={"class": INPUT_GLASS}),
            "unit": forms.Select(attrs={"class": INPUT_GLASS}),
        }

class EntityForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = ["name", "description"]  # adjust if your model has more fields
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 7}),
        }

class EpicForm(forms.ModelForm):
    class Meta:
        model = Epic
        # Usually key_result is set in the view (from the URL), so we don't expose it in the form
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "description": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 7}),
        }

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ["epic", "title", "role", "goal", "reason"]
        widgets = {
            "epic": forms.Select(attrs={"class": INPUT_GLASS}),
            "title": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "role": forms.TextInput(attrs={"class": INPUT_GLASS}),
            "goal": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 4}),
            "reason": forms.Textarea(attrs={"class": TEXTAREA_GLASS, "rows": 4}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status", "title", "completed", "assigned_user", "due_date", "notes"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 8, "class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    assigned_user = forms.ModelChoiceField(
        queryset=User.objects.order_by("first_name", "last_name", "username"),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Assigned to",
        empty_label="Unassigned"
    )
