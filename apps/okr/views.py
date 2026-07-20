# apps/okr/views.py
from __future__ import annotations
import re
from decimal import Decimal
import os
from xhtml2pdf import pisa
from django.forms import inlineformset_factory
from django.forms import modelform_factory
from django.views import View
from django import forms
from .models import Entity, Epic, Task, ProgressUpdate, Strategy, Objective, KeyResult
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView
from django.db.models import Q
from openai import OpenAI

from django.contrib import messages  # <-- make sure this is imported at top
from django.views.generic import DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Count
from django.db.models import Prefetch
from django.shortcuts import redirect
from django.views.generic.edit import UpdateView
from django.views.generic.edit import CreateView
from .models import KeyResultMetric  # <-- add if not already imported
from apps.mnemos.models import FileAttachment, AiArtifact
from apps.common.models import AiUsageEvent  # matches your file :contentReference[oaicite:1]{index=1}
from .forms import EpicForm
from apps.mnemos.models import FileAttachment
from apps.mnemos.models import AiArtifact
from apps.mnemos.models import AiArtifact
from apps.mnemos.models import FileAttachment

from .forms import ObjectiveForm, StrategyForm, StoryForm
from ..common.chat_r1 import rewrite_objective_description, chat_with_gpt  # ✅ import GPT function
from .models import Entity, Strategy, Objective, KeyResult, Epic, Story, Task

from .forms import TaskForm

client = OpenAI()  # uses OPENAI_API_KEY env var

ObjectiveFormSet = inlineformset_factory(
    Objective, KeyResult,
    fields=('name', 'target_value', 'current_value', 'unit'),
    extra=1,
    can_delete=False
)

ObjectiveForm = modelform_factory(Objective, fields=['name', 'description', 'owner', 'start_date', 'end_date'])
class ObjectiveUpdateView(LoginRequiredMixin, UpdateView):
    model = Objective
    form_class = ObjectiveForm
    template_name = 'okr/objective_form.html'  # reuse your create template
    success_url = reverse_lazy('okr:objective-list')

def camel_to_snake(name):
    """Convert camelCase or PascalCase to snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def normalize_keys(obj):
    """Recursively normalize all keys in a dict or list from camelCase to snake_case."""
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            new_key = camel_to_snake(k)
            new_obj[new_key] = normalize_keys(v)
        return new_obj
    elif isinstance(obj, list):
        return [normalize_keys(item) for item in obj]
    else:
        return obj

def generate_kr_suggestion(objective_description):
    """
    Suggest a key result based on the given objective description.
    Replace this mock logic with your actual AI integration later.
    """
    # Simple heuristic example
    if "revenue" in objective_description.lower():
        return "Achieve $10,000 in monthly revenue"
    elif "scale" in objective_description.lower():
        return "Increase production capacity by 25%"
    elif "customers" in objective_description.lower():
        return "Onboard 100 new customers"
    else:
        return "Define measurable success criteria aligned with this objective"

def rewrite_objective_description(description_text):
    prompt = f"Rewrite the following business objective description to be more concise and impactful: {description_text}"
    response = chat_with_gpt(prompt=prompt)
    return response.choices[0].message.content


class EntityListView(LoginRequiredMixin, ListView):
    model = Entity
    template_name = 'okr/entity_list.html'
    context_object_name = 'entities'

    def get_queryset(self):
        return Entity.objects.annotate(
            strategy_count=Count('strategies')
        )


class EntityStrategyListView(LoginRequiredMixin, ListView):
    model = Strategy
    template_name = 'okr/strategy_list.html'
    context_object_name = 'object_list'

    def get_queryset(self):
        entity_id = self.kwargs['pk']
        return Strategy.objects.filter(entity_id=entity_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entity'] = Entity.objects.get(pk=self.kwargs['pk'])
        return context

class ObjectiveListView(LoginRequiredMixin, ListView):
    model = Objective
    template_name = 'okr/objective_list.html'
    context_object_name = 'objectives'  # <--- Required for template


class ObjectiveCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = ObjectiveForm()
        return render(request, 'okr/objective_form.html', {'form': form})

    def post(self, request):
        form = ObjectiveForm(request.POST)

        if 'rewrite' in request.POST:  # ✅ Handle rewrite request
            if form.is_valid():
                cleaned = form.cleaned_data
                new_description = rewrite_objective_description(cleaned['description'])
                form = ObjectiveForm(initial={**cleaned, 'description': new_description})
            return render(request, 'okr/objective_form.html', {'form': form})

        elif form.is_valid():
            form.save()
            return redirect('objective-list')

        return render(request, 'okr/objective_form.html', {'form': form})



class ObjectiveDetailView(LoginRequiredMixin, DetailView):
    model = Objective
    template_name = 'okr/objective_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Prefer using the same queryset in template
        key_results = self.object.key_results.prefetch_related(
            Prefetch("metrics", queryset=KeyResultMetric.objects.select_related("dimension"))
        )
        context['key_results'] = key_results

        # ---- Scorecard preview rollup (compact) ----
        dim = {}  # {dimension_id: {...}}
        krs_with_metrics = 0
        total_metrics = 0

        for kr in key_results:
            metrics = list(getattr(kr, "metrics").all())  # related_name="metrics"
            if metrics:
                krs_with_metrics += 1
            for m in metrics:
                total_metrics += 1
                d_id = m.dimension_id
                if d_id not in dim:
                    dim[d_id] = {
                        "dimension": m.dimension,
                        "rag": {"green": 0, "yellow": 0, "red": 0, "gray": 0},
                        "count": 0,
                    }
                rag = m.status_rag()
                dim[d_id]["rag"][rag] = dim[d_id]["rag"].get(rag, 0) + 1
                dim[d_id]["count"] += 1

        # Sort dimensions by (sort_order, name) and take top 3 for preview
        dim_rows = sorted(
            dim.values(),
            key=lambda x: (x["dimension"].sort_order, x["dimension"].name.lower())
        )[:3]

        context["scorecard_preview"] = {
            "krs_with_metrics": krs_with_metrics,
            "total_krs": key_results.count(),
            "total_metrics": total_metrics,
            "dimensions": dim_rows,
            "more_dimensions_count": max(0, len(dim) - len(dim_rows)),
        }

        return context

KeyResultForm = modelform_factory(KeyResult, fields=['name', 'description', 'target_value', 'unit'])
class KeyResultCreateView(LoginRequiredMixin, View):
    form_class = KeyResultForm
    template_name = 'okr/keyresult_form.html'

    def get_initial(self):
        objective = get_object_or_404(Objective, pk=self.kwargs['pk'])
        return {'objective': objective}

    def get(self, request, pk):
        objective = get_object_or_404(Objective, pk=pk)
        form = KeyResultForm()
        return render(request, self.template_name, {'form': form, 'objective': objective})

    from django.contrib import messages

    def post(self, request, pk):
        objective = get_object_or_404(Objective, pk=pk)
        form = KeyResultForm(request.POST)

        if form.is_valid():
            kr = form.save(commit=False)
            kr.objective = objective
            kr.save()

            messages.success(request, '✅ Key Result saved successfully!')  # <-- new line!

            return redirect('objective-detail', pk=objective.pk)

        return render(request, self.template_name, {'form': form, 'objective': objective})

class KeyResultDeleteView(DeleteView):
    model = KeyResult
    template_name = 'okr/keyresult_confirm_delete.html'
    def get_success_url(self):
        return reverse_lazy('okr:objective-detail', kwargs={'pk': self.object.objective_id})

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import pandas as pd
import plotly.express as px

from .models import Strategy


@login_required
def sunburst_okr_view(request):
    data = []
    initiative_name = "TrustBixxx"

    strategies = Strategy.objects.prefetch_related(
        "objectives__key_results__epics__stories__tasks"
    ).all()

    def avg(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else 0

    strategy_progresses = []

    for strategy in strategies:
        objective_progresses = []

        for obj in strategy.objectives.all():
            kr_progresses = []

            for kr in obj.key_results.all():
                exec_progress_pct = kr.execution_progress or 0
                exec_progress = exec_progress_pct / 100.0

                # color stretch so low values are easier to distinguish
                color_progress = exec_progress ** 0.5 if exec_progress > 0 else 0

                kr_progresses.append(exec_progress)

                data.append({
                    "id": f"kr-{kr.id}",
                    "parent": f"obj-{obj.id}",
                    "label": kr.name,
                    "value": max(exec_progress, 0.001),
                    "color": color_progress,
                    "summary": kr.description or "",
                    "level": "Key Result",
                    "execution_label": f"{exec_progress_pct:.1f}%",
                    "outcome_label": f"{kr.progress:.1f}%",
                    "current_value": kr.current_value,
                    "target_value": kr.target_value,
                    "unit": kr.unit,
                })

            obj_progress = avg(kr_progresses)
            obj_color = obj_progress ** 0.5 if obj_progress > 0 else 0
            objective_progresses.append(obj_progress)

            data.append({
                "id": f"obj-{obj.id}",
                "parent": f"strategy-{strategy.id}",
                "label": obj.name,
                "value": max(sum(kr_progresses), 0.001),
                "color": obj_color,
                "summary": getattr(obj, "description", "") or "",
                "level": "Objective",
                "execution_label": f"{obj_progress * 100:.1f}%",
                "outcome_label": "",
                "current_value": "",
                "target_value": "",
                "unit": "",
            })

        strategy_progress = avg(objective_progresses)
        strategy_color = strategy_progress ** 0.5 if strategy_progress > 0 else 0
        strategy_progresses.append(strategy_progress)

        data.append({
            "id": f"strategy-{strategy.id}",
            "parent": "initiative-root",
            "label": strategy.name,
            "value": max(sum(objective_progresses), 0.001),
            "color": strategy_color,
            "summary": "",
            "level": "Strategy",
            "execution_label": f"{strategy_progress * 100:.1f}%",
            "outcome_label": "",
            "current_value": "",
            "target_value": "",
            "unit": "",
        })

    initiative_progress = avg(strategy_progresses)
    initiative_color = initiative_progress ** 0.5 if initiative_progress > 0 else 0

    data.append({
        "id": "initiative-root",
        "parent": "",
        "label": initiative_name,
        "value": max(sum(strategy_progresses), 0.001),
        "color": initiative_color,
        "summary": "",
        "level": "Initiative",
        "execution_label": f"{initiative_progress * 100:.1f}%",
        "outcome_label": "",
        "current_value": "",
        "target_value": "",
        "unit": "",
    })

    df = pd.DataFrame(data)

    if df.empty:
        chart_html = "<div class='text-soft'>No OKR data available yet.</div>"
        return render(request, "okr/sunburst.html", {"chart_html": chart_html})

    max_color = max(df["color"].max(), 0.01)

    fig = px.sunburst(
        df,
        ids="id",
        names="label",
        parents="parent",
        values="value",
        color="color",
        color_continuous_scale="purples",
        range_color=[0, max_color],
        custom_data=[
            "level",
            "summary",
            "execution_label",
            "outcome_label",
            "current_value",
            "target_value",
            "unit",
        ],
        title="Objectives & Key Results Execution Visualization",
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Level: %{customdata[0]}<br>"
            "Execution: %{customdata[2]}<br>"
            "%{customdata[1]}<br>"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        paper_bgcolor="#070618",
        plot_bgcolor="#070618",
        font_color="white",
        margin=dict(t=60, l=20, r=20, b=20),
        coloraxis_colorbar=dict(title="Progress"),
    )

    chart_html = fig.to_html(full_html=False)
    return render(request, "okr/sunburst.html", {"chart_html": chart_html})


class StrategyListView(LoginRequiredMixin, ListView):
    model = Strategy
    template_name = 'okr/strategy_list.html'

    def get_queryset(self):
        afsi_entity = Entity.objects.filter(name__iexact="AFSI").first()
        return Strategy.objects.filter(entity=afsi_entity)


class StrategyDetailView(DetailView):
    model = Strategy
    template_name = 'okr/strategy_detail.html'


class StrategyUpdateView(UpdateView):
    model = Strategy
    form_class = StrategyForm
#    fields = ['name', 'description']
    template_name = 'okr/strategy_form.html'
    success_url = reverse_lazy('okr:strategy-list')


class StrategyCreateView(CreateView):
    model = Strategy
    fields = ['entity', 'name', 'description', 'theme']
    template_name = 'okr/strategy_form.html'
    success_url = reverse_lazy('okr:strategy-list')


class StrategyDeleteView(DeleteView):
    model = Strategy
    template_name = 'okr/strategy_confirm_delete.html'
    success_url = reverse_lazy('okr:strategy-list')

@login_required()
@csrf_exempt
def rewrite_objective_description_api(request):
    print("Objective description")
    if request.method == "POST":
        body = json.loads(request.body)
        objective_text = body.get("objective", "")

        prompt = f"Write a concise and impactful business objective description for: {objective_text}"
        rewritten = chat_with_gpt(prompt).choices[0].message.content

        return JsonResponse({'rewritten': rewritten})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required()
@csrf_exempt
def rewrite_keyresult_api(request):
    print("Key Result", request.method)
    if request.method == "POST":
        body = json.loads(request.body)
        kr_text = body.get("key_result", "")
        print("Key Result", request.method, " : ", kr_text)
        prompt = f"Rewrite the following Key Result to make it clear, measurable, and outcome-focused:\n\n{kr_text}"
        rewritten = chat_with_gpt(prompt).choices[0].message.content

        return JsonResponse({'rewritten': rewritten})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def keyresult_epics_view(request, pk):
    key_result = get_object_or_404(KeyResult, pk=pk)
    epics = key_result.epics.all()
    return render(request, 'okr/keyresult_epics.html', {
        'key_result': key_result,
        'epics': epics
    })

@login_required
def keyresult_drawer_view(request, pk):
    key_result = get_object_or_404(KeyResult.objects.prefetch_related("epics__stories__tasks"), pk=pk)
    return render(request, "okr/partials/keyresult_drawer.html", {
        "key_result": key_result,
    })

class KeyResultUpdateView(UpdateView):
    model = KeyResult
    fields = ['name', 'description', 'target_value', 'current_value', 'unit']
    template_name = 'okr/keyresult_form.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Safety: if a KR is orphaned (objective_id is NULL), don't blow up templates.
        """
        self.object = self.get_object()
        if not self.object.objective_id:
            return redirect('okr:objective-list')  # or a dedicated "orphan repair" page
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["objective"] = self.object.objective  # ✅ used by template back-links
        return context

    def get_success_url(self):
        return reverse_lazy('okr:objective-detail', kwargs={'pk': self.object.objective_id})


class EpicDetailView(LoginRequiredMixin, DetailView):
    model = Epic
    template_name = 'okr/epic_detail.html'
    context_object_name = 'epic'


class OKRHierarchyView(TemplateView):
    template_name = 'okr/hierarchy_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        afsi_entity = Entity.objects.filter(name__iexact="AFSI").first()
        context["entity"] = afsi_entity

        if afsi_entity:
            strategies = afsi_entity.strategies.prefetch_related(
                'objectives__key_results__epics__stories__tasks'
            )
        else:
            strategies = Strategy.objects.none()

        context["strategies"] = strategies
        return context

@csrf_exempt
def rewrite_strategy_description_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "")
        entity_id = data.get("entity_id")

        entity = Entity.objects.filter(id=entity_id).first()
        entity_desc = entity.description if entity else ""
        entity_name = entity.name if entity else ""
        prompt = f"""
Write a concise, strategic description for a strategy titled: "{name}".

This strategy belongs to the following entity:
"{entity_name}"

The description should align with {entity_desc} and reflect a clear business purpose.
"""

        rewritten = chat_with_gpt(prompt).choices[0].message.content
        return JsonResponse({'rewritten': rewritten})

    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def rewrite_epic_description(request):
    data = json.loads(request.body)
    title = data.get("title")
    prompt = f"Write a concise, strategic Epic description for a software platform titled '{title}' supporting AI-enabled indoor farming and traceability."
    result = chat_with_gpt(prompt).choices[0].message.content
    return JsonResponse({'rewritten': result})

@csrf_exempt
def generate_user_story(request):
    data = json.loads(request.body)
    role = data.get("role")
    goal = data.get("goal")
    prompt = f"Write a user story in the format 'As a {role}, I want to {goal} so that...'"
    result = chat_with_gpt(prompt).choices[0].message.content
    return JsonResponse({'rewritten': result})

@csrf_exempt
def suggest_task_title(request):
    data = json.loads(request.body)
    story = data.get("story", "")
    prompt = f"Suggest a task someone might do to support this story: {story}"
    result = chat_with_gpt(prompt).choices[0].message.content
    return JsonResponse({'rewritten': result})


class EpicUpdateView(LoginRequiredMixin, UpdateView):
    model = Epic
    fields = ['title', 'description']
    template_name = 'okr/epic_form.html'

    def get_success_url(self):
        epic = self.object
        if epic.key_result_id:
            return reverse("okr:keyresult-epics", args=[epic.key_result_id])
        return reverse("okr:strategy-heatmap")


class EpicDeleteView(LoginRequiredMixin, DeleteView):
    model = Epic
    template_name = 'okr/epic_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('keyresult-epics', kwargs={'pk': self.object.key_result.id})

class EpicCreateView(LoginRequiredMixin, CreateView):
    model = Epic
    form_class = EpicForm
    template_name = 'okr/epic_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.key_result = get_object_or_404(KeyResult, pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.key_result = self.key_result
        self.success_url = reverse_lazy('okr:keyresult-epics', kwargs={'pk': self.key_result.id})
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['key_result'] = self.key_result
        return context


class StoryCreateView(CreateView):
    model = Story
    form_class = StoryForm
    template_name = "okr/story_form.html"

    def get_initial(self):
        initial = super().get_initial()
        epic_id = (self.request.GET.get("epic") or "").strip()
        if epic_id.isdigit():
            initial["epic"] = int(epic_id)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        epic_id = (self.request.GET.get("epic") or "").strip()
        if epic_id.isdigit():
            ctx["epic_id"] = int(epic_id)
            ctx["epic"] = Epic.objects.only("id", "title").filter(id=int(epic_id)).first()
        else:
            ctx["epic_id"] = None
            ctx["epic"] = None
        return ctx

    def get_success_url(self):
        epic_id = getattr(self.object, "epic_id", None)
        if epic_id:
            return f"{reverse('okr:story-list')}?epic={epic_id}"
        return reverse_lazy("okr:story-list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        epic_id = (self.request.GET.get("epic") or "").strip()
        if epic_id.isdigit():
            form.fields["epic"].initial = int(epic_id)
            form.fields["epic"].disabled = True
        return form


class StoryDetailView(DetailView):
    model = Story
    template_name = 'okr/story_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = ['Pending', 'In Progress', 'Done']
        return context


class StoryUpdateView(UpdateView):
    model = Story
    form_class = StoryForm
    template_name = "okr/story_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        epic_id = getattr(self.object, "epic_id", None)
        ctx["epic_id"] = epic_id
        ctx["epic"] = Epic.objects.only("id", "title").filter(id=epic_id).first() if epic_id else None
        return ctx

    def get_success_url(self):
        epic_id = getattr(self.object, "epic_id", None)
        if epic_id:
            return f"{reverse('okr:story-list')}?epic={epic_id}"
        return reverse_lazy("okr:story-list")


class StoryDeleteView(DeleteView):
    model = Story
    template_name = 'okr/story_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy("okr:story-list")


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "okr/task_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.story = None
        story_id = kwargs.get("story_id")
        if story_id:
            self.story = get_object_or_404(Story, pk=story_id)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if "assigned_user" in getattr(self.form_class, "base_fields", {}):
            initial.setdefault("assigned_user", self.request.user)
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)

        # ✅ CRITICAL: enforce story for /stories/<id>/tasks/add/
        if self.story is not None:
            obj.story = self.story

        # Optional ownership/audit fields
        for field in ("created_by", "owner", "updated_by"):
            if hasattr(obj, field) and not getattr(obj, field, None):
                setattr(obj, field, self.request.user)

        obj.save()
        form.save_m2m()
        self.object = obj
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("okr:task-detail", args=[self.object.pk])

@csrf_exempt
def update_task_status(request, pk):
    print('update task status')
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')

            task = Task.objects.get(pk=pk)
            task.status = new_status
            task.save()
            print('update task status - task saved', task.status)
            return JsonResponse({'success': True, 'task_id': task.id, 'new_status': task.status})
        except Task.DoesNotExist:
            print('update task status - not found')
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
        except Exception as e:
            print('update task status', e)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


class EntityForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6})
        }

# 2. Create the EntityCreateView
def clean_story_field(value, prefix):
    return value.replace(prefix, '').strip() if value else ''


class EntityCreateView(CreateView):
    model = Entity
    form_class = EntityForm
    template_name = 'okr/entity_create.html'  # you'll need to create this
    success_url = reverse_lazy('okr:entity-list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Send description to GPT and get OKR Structure
        entity = self.object
        gpt_response = self.generate_okr_structure(entity.name, entity.description)

        if gpt_response:
            self.build_okr_hierarchy(entity, gpt_response)

        return response

    def build_okr_hierarchy(self, entity, data):
        # Counters
        strategy_count = 0
        objective_count = 0
        keyresult_count = 0
        epic_count = 0
        story_count = 0
        task_count = 0

        for strategy_data in data.get('strategies', []):
            strategy = Strategy.objects.create(
                entity=entity,
                name=strategy_data['name'],
                description=strategy_data.get('description', ''),
            )
            strategy_count += 1

            for objective_data in strategy_data.get('objectives', []):
                objective = Objective.objects.create(
                    strategy=strategy,
                    name=objective_data['name'],
                    description=objective_data.get('description', ''),
                    owner='Auto-generated',
                    start_date='2025-01-01',
                    end_date='2025-12-31',
                )
                objective_count += 1

                kr_list = objective_data.get('key_results') or objective_data.get('keyresults') or []
                for kr_data in kr_list:
                    kr = KeyResult.objects.create(
                        objective=objective,
                        name=kr_data['name'],
                        description=kr_data.get('description', ''),
                        target_value=100,
                        current_value=0,
                        unit='%',
                    )
                    keyresult_count += 1

                    epic_list = kr_data.get('epics', [])
                    for epic_data in epic_list:
                        epic = Epic.objects.create(
                            key_result=kr,
                            title=epic_data.get('title') or epic_data.get('name', 'Unnamed Epic'),
                            description=epic_data.get('description', ''),
                        )
                        epic_count += 1

                        story_list = epic_data.get('stories', [])
                        for story_data in story_list:
                            story = Story.objects.create(
                                epic=epic,
                                title=story_data.get('title') or story_data.get('name', 'Unnamed Story'),
                                role=clean_story_field(story_data.get('role'), 'As a'),
                                goal=clean_story_field(story_data.get('goal'), 'I want to'),
                                reason=clean_story_field(story_data.get('reason'), 'so that'),
                            )
                            story_count += 1

                            task_list = story_data.get('tasks', [])
                            for task_title in task_list:
                                Task.objects.create(
                                    story=story,
                                    title=task_title
                                )
                                task_count += 1

        # 🎯 Now send a success Toast message instead of just printing
        success_message = (
            f"✅ OKR Hierarchy Created: "
            f"{strategy_count} Strategies, {objective_count} Objectives, {keyresult_count} Key Results, "
            f"{epic_count} Epics, {story_count} Stories, {task_count} Tasks."
        )

        messages.success(self.request, success_message)
    def generate_okr_structure(self, name, description):
        prompt = f"""
    You are an expert in business strategy and OKR (Objectives and Key Results) development.

    Given the following business entity name and description, generate a highly structured and practical JSON output that includes:
    - 2 Strategies (aligned to the entity's mission)
    - Each Strategy should have 2-3 Objectives
    - Each Objective should have 2-3 Key Results
    - Each Key Result should have 1-2 Epics
    - Each Epic should have 2-3 Stories
    - Each Story should have 2-3 Tasks

    Each item should include:
    - A clear and concise **name** (required)
    - A **description** (1-2 short sentences)
    - For Stories: also generate a **role** ("As a..."), a **goal**, and a **reason**
    - Tasks should be simple, actionable, and relevant

    Return ONLY a valid JSON object. Avoid any additional commentary.

    Entity Name: "{name}"
    Entity Description: "{description}"
    """
        try:
            response = chat_with_gpt(prompt)
            content = response.choices[0].message.content.strip()

            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()
            print(content)
            if not content.startswith('{'):
                print("Error: GPT content not JSON after cleaning:\n", content)
                return None

            raw_data = json.loads(content)
            normalized_data = normalize_keys(raw_data)  # <-- normalize here
            return normalized_data

        except Exception as e:
            print("Error generating OKRs:", e)
            return None


class EntityDeleteView(DeleteView):
    model = Entity
    template_name = 'okr/entity_confirm_delete.html'
    success_url = reverse_lazy('okr:entity-list')

    def delete(self, request, *args, **kwargs):
        """
        Overriding delete to ensure cascading deletes.
        Django's default ForeignKey behavior with on_delete=CASCADE
        will handle Objectives, Key Results, etc.
        """
        return super().delete(request, *args, **kwargs)

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
import pandas as pd
import plotly.express as px

from .models import Entity


@login_required
def entity_sunburst_view(request, pk):
    entity = get_object_or_404(Entity, pk=pk)

    data = []
    MIN_VISIBLE_PROGRESS = 0.10

    strategies = entity.strategies.prefetch_related(
        "objectives__key_results__epics__stories__tasks"
    ).all()

    def avg(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else 0

    strategy_progresses = []
    strategy_display_values = []

    for strategy in strategies:
        objective_progresses = []
        objective_display_values = []

        for obj in strategy.objectives.all():
            kr_progresses = []
            kr_display_values = []

            for kr in obj.key_results.all():
                exec_progress_pct = kr.execution_progress or 0
                exec_progress = exec_progress_pct / 100.0
                color_progress = exec_progress ** 0.5 if exec_progress > 0 else 0
                display_value = max(exec_progress, MIN_VISIBLE_PROGRESS)

                kr_progresses.append(exec_progress)
                kr_display_values.append(display_value)

                data.append({
                    "id": f"kr-{kr.id}",
                    "parent": f"obj-{obj.id}",
                    "label": kr.name,
                    "value": display_value,
                    "color": color_progress,
                    "summary": kr.description or "",
                    "level": "Key Result",
                    "execution_label": f"{exec_progress_pct:.1f}%",
                    "outcome_label": f"{kr.progress:.1f}%",
                    "current_value": kr.current_value,
                    "target_value": kr.target_value,
                    "unit": kr.unit,
                    "url": reverse("okr:keyresult-drawer", args=[kr.pk]),  # or keyresult-detail if you have one
                })

            obj_progress = avg(kr_progresses)
            obj_color = obj_progress ** 0.5 if obj_progress > 0 else 0
            obj_display_value = max(sum(kr_display_values), MIN_VISIBLE_PROGRESS)

            objective_progresses.append(obj_progress)
            objective_display_values.append(obj_display_value)

            data.append({
                "id": f"obj-{obj.id}",
                "parent": f"strategy-{strategy.id}",
                "label": obj.name,
                "value": obj_display_value,
                "color": obj_color,
                "summary": getattr(obj, "description", "") or "",
                "level": "Objective",
                "execution_label": f"{obj_progress * 100:.1f}%",
                "outcome_label": "",
                "current_value": "",
                "target_value": "",
                "unit": "",
                "url": reverse("okr:objective-detail", args=[obj.pk]),
            })

        strategy_progress = avg(objective_progresses)
        strategy_color = strategy_progress ** 0.5 if strategy_progress > 0 else 0
        strategy_display_value = max(sum(objective_display_values), MIN_VISIBLE_PROGRESS)

        strategy_progresses.append(strategy_progress)
        strategy_display_values.append(strategy_display_value)

        data.append({
            "id": f"strategy-{strategy.id}",
            "parent": "initiative-root",
            "label": strategy.name,
            "value": strategy_display_value,
            "color": strategy_color,
            "summary": "",
            "level": "Strategy",
            "execution_label": f"{strategy_progress * 100:.1f}%",
            "outcome_label": "",
            "current_value": "",
            "target_value": "",
            "unit": "",
            "url": "",  # add a strategy page later if you want
        })

    initiative_progress = avg(strategy_progresses)
    initiative_color = initiative_progress ** 0.5 if initiative_progress > 0 else 0
    initiative_display_value = max(sum(strategy_display_values), MIN_VISIBLE_PROGRESS)

    data.append({
        "id": "initiative-root",
        "parent": "",
        "label": entity.name,
        "value": initiative_display_value,
        "color": initiative_color,
        "summary": "",
        "level": "Initiative",
        "execution_label": f"{initiative_progress * 100:.1f}%",
        "outcome_label": "",
        "current_value": "",
        "target_value": "",
        "unit": "",
        "url": "",
    })

    df = pd.DataFrame(data)

    if df.empty:
        fig = px.sunburst(
            names=["No Data Available"],
            parents=[""],
            values=[1],
            title=f"{entity.name} - OKR Sunburst Visualization",
        )
    else:
        max_color = max(df["color"].max(), 0.01)

    custom_scale = [
        [0.00, "#8b1026"],  # deep wine
        [0.18, "#d55a2a"],  # ember
        [0.38, "#f3c78d"],  # warm sand
        [0.58, "#dce7dc"],  # pale sage
        [0.78, "#79b98f"],  # soft green
        [1.00, "#0f6b50"],  # deep emerald
    ]

    fig = px.sunburst(
        df,
        ids="id",
        names="label",
        parents="parent",
        values="value",
        color="color",
        color_continuous_scale=custom_scale,
        range_color=[0, max_color],
        custom_data=[
            "level",
            "summary",
            "execution_label",
            "outcome_label",
            "current_value",
            "target_value",
            "unit",
            "url",
        ],
        title=f"{entity.name} - OKR Execution Sunburst",
    )

    fig.update_traces(
        insidetextfont=dict(
            family="Inter, Segoe UI, Arial, sans-serif",
            size=13,
            color="black",
        ),
        marker=dict(
            line=dict(color="rgba(255,255,255,0.16)", width=1.2)
        ),
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.97)",
            bordercolor="rgba(0,0,0,0.10)",
            font=dict(
                color="black",
                size=14,
                family="Inter, Segoe UI, Arial, sans-serif",
            ),
        ),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Level: %{customdata[0]}<br>"
            "Execution: %{customdata[2]}<br>"
            "%{customdata[1]}<br>"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        width=1600,
        height=1100,
        paper_bgcolor="#050816",
        plot_bgcolor="#050816",
        font=dict(
            family="Inter, Segoe UI, Arial, sans-serif",
            size=16,
            color="black",
        ),
        title=dict(
            text=f"{entity.name} OKR Execution Sunburst",
            x=0.5,
            xanchor="center",
            font=dict(
                family="Inter, Segoe UI, Arial, sans-serif",
                size=24,
                color="white",
            ),
        ),
        margin=dict(t=80, l=40, r=40, b=40),
        coloraxis_colorbar=dict(
            title=dict(
                text="Execution",
                font=dict(
                    family="Inter, Segoe UI, Arial, sans-serif",
                    size=16,
                    color="white",
                ),
            ),
            tickfont=dict(
                family="Inter, Segoe UI, Arial, sans-serif",
                size=13,
                color="white",
            ),
            thickness=22,
            len=0.78,
            outlinewidth=0,
            bgcolor="rgba(255,255,255,0.03)",
        ),
    )
    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return render(
        request,
        "okr/sunburst.html",
        {
            "chart_html": chart_html,
            "entity": entity,
        },
    )

@login_required
def entity_hierarchy_view(request, pk):
    entity = get_object_or_404(Entity, pk=pk)

    strategies = entity.strategies.prefetch_related(
        'objectives__key_results__epics__stories__tasks'
    )

    return render(request, 'okr/hierarchy_report.html', {
        'strategies': strategies,
        'entity': entity,  # we'll use this later for a back button if needed
    })

@login_required
def entity_hierarchy_pdf(request, pk):
    entity = get_object_or_404(Entity, pk=pk)
    strategies = entity.strategies.prefetch_related(
        'objectives__key_results__epics__stories__tasks'
    )

    template = get_template('okr/hierarchy_report_pdf.html')
    html = template.render({'strategies': strategies, 'entity': entity})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{entity.name}_OKR_Hierarchy.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response

@login_required
def objective_scorecard_view(request, pk):
    objective = get_object_or_404(Objective, pk=pk)

    # Prefetch metrics efficiently
    key_results = objective.key_results.prefetch_related(
        Prefetch("metrics", queryset=KeyResultMetric.objects.select_related("dimension"))
    )

    # Build dimension-centric rollup
    dim_rollup = {}  # key -> {dimension, items[], avg_progress, rag_counts}
    for kr in key_results:
        for m in kr.metrics.all():
            dkey = m.dimension.key
            dim_rollup.setdefault(dkey, {
                "dimension": m.dimension,
                "items": [],
                "progress_values": [],
                "rag": {"green": 0, "yellow": 0, "red": 0, "gray": 0},
            })

            pr = m.progress_ratio()
            if pr is not None:
                dim_rollup[dkey]["progress_values"].append(pr * m.weight)

            dim_rollup[dkey]["items"].append({
                "kr": kr,
                "metric": m,
                "progress": pr,
                "rag": m.status_rag(),
            })
            dim_rollup[dkey]["rag"][m.status_rag()] += 1

    # finalize rollups
    rows = []
    for dkey, payload in dim_rollup.items():
        vals = payload["progress_values"]
        avg = (sum(vals) / len(vals)) if vals else None
        rows.append({
            "dimension": payload["dimension"],
            "avg_progress": avg,
            "rag": payload["rag"],
            "items": payload["items"],
        })

    # sort by dimension sort_order then name
    rows.sort(key=lambda r: (r["dimension"].sort_order, r["dimension"].name.lower()))

    return render(request, "okr/objective_scorecard.html", {
        "objective": objective,
        "rows": rows,
    })

AT_RISK_STATUSES = {"at_risk", "blocked"}  # <-- change to match your system (see note below)

@login_required
def strategy_heatmap(request):
    """
    /okr/heatmap/?entity=<id>&health=green|amber|red|none

    Notes:
    - Strategy has: entity, name, description, theme
    - Objective has: strategy, owner, start_date, end_date
    - KeyResult has: target_value, current_value
    """
    entity_id = (request.GET.get("entity") or "").strip()
    health_filter = (request.GET.get("health") or "").strip().lower()

    # Filter objectives by Strategy.entity (subsidiary)
    obj_q = Q()
    if entity_id.isdigit():
        obj_q &= Q(strategy__entity_id=int(entity_id))

    # Prefetch KRs (only fields that exist)
    # Prefetch latest ProgressUpdates for each KR (only the fields we need)
    update_qs = ProgressUpdate.objects.only("id", "key_result_id", "update_date").order_by("-update_date")

    kr_qs = (
        KeyResult.objects.all()
        .only("id", "objective_id", "target_value", "current_value", "name")
        .prefetch_related(Prefetch("updates", queryset=update_qs, to_attr="updates_all"))
    )

    obj_qs = (
        Objective.objects.select_related("strategy", "strategy__entity")
        .filter(obj_q)
        .prefetch_related(Prefetch("key_results", queryset=kr_qs, to_attr="key_results_all"))
        .only("id", "strategy_id", "name", "owner", "start_date", "end_date")
    )

    strategies = (
        Strategy.objects.select_related("entity")
        .prefetch_related(Prefetch("objectives", queryset=obj_qs, to_attr="objectives_filtered"))
        .only("id", "name", "entity_id", "theme")
        .order_by("name")
    )

    def kr_progress_pct(kr) -> float:
        tv = float(getattr(kr, "target_value", 0) or 0)
        cv = float(getattr(kr, "current_value", 0) or 0)
        if tv <= 0:
            return 0.0
        pct = (cv / tv) * 100.0
        return max(0.0, min(100.0, pct))

    today = timezone.now().date()
    rows = []

    for s in strategies:
        objectives = list(getattr(s, "objectives_filtered", []))
        objective_count = len(objectives)

        kr_count = 0
        at_risk_count = 0
        progress_values = []
        last_update = None
        for obj in objectives:
            krs = list(getattr(obj, "key_results_all", []))
            if not krs:
                continue

            kr_count += len(krs)
            for kr in krs:
                # last_update comes from ProgressUpdate.update_date
                updates = list(getattr(kr, "updates_all", []))
                if updates:
                    # updates are ordered newest-first
                    udate = updates[0].update_date
                    if udate and (last_update is None or udate > last_update):
                        last_update = udate

                tv = float(getattr(kr, "target_value", 0) or 0)
                cv = float(getattr(kr, "current_value", 0) or 0)

                if tv > 0 and cv < tv and obj.end_date and obj.end_date < timezone.now().date():
                    at_risk_count += 1

            # Objective progress = average of its KR %'s
            obj_pct = sum(kr_progress_pct(kr) for kr in krs) / len(krs)
            progress_values.append(obj_pct)

            # Inferred "at risk":
            # - Objective overdue AND objective not ~done (avg < 100)
            # - OR any KR is below target when overdue
            if obj.end_date and obj.end_date < today:
                if obj_pct < 100:
                    at_risk_count += 1
                else:
                    # still count KRs that are individually below target
                    for kr in krs:
                        if kr_progress_pct(kr) < 100:
                            at_risk_count += 1
                            break

        has_data = (objective_count > 0 and kr_count > 0 and len(progress_values) > 0)
        progress = round((sum(progress_values) / len(progress_values)) if has_data else 0.0, 1)

        # Deterministic health rules
        if not has_data:
            health = "none"
        elif progress < 40:
            health = "red"
        elif progress < 70 or at_risk_count >= 1:
            health = "amber"
        else:
            health = "green"

        owner_label = s.entity.name if getattr(s, "entity", None) else "—"

        rows.append({
            "strategy": s,
            "progress": progress,
            "health": health,
            "objective_count": objective_count,
            "kr_count": kr_count,
            "at_risk_count": at_risk_count,
            "owner_label": owner_label,
            "last_update": last_update,  # your models don't have timestamps on KR; we can enhance later
        })

    if health_filter in {"green", "amber", "red", "none"}:
        rows = [r for r in rows if r["health"] == health_filter]

    entities = Strategy.objects.select_related("entity").values_list("entity_id", "entity__name").distinct()

    return render(request, "okr/strategy_heatmap.html", {
        "rows": rows,
        "entity_id": entity_id,
        "health_filter": health_filter,
        "entities": [(eid, name) for eid, name in entities if eid],
    })

@login_required
def kr_at_risk_list(request):
    strategy_id = (request.GET.get("strategy") or "").strip()
    entity_id = (request.GET.get("entity") or "").strip()

    q = Q()
    if strategy_id.isdigit():
        q &= Q(objective__strategy_id=int(strategy_id))
    if entity_id.isdigit():
        q &= Q(objective__strategy__entity_id=int(entity_id))

    today = timezone.now().date()

    update_qs = ProgressUpdate.objects.only("id", "key_result_id", "update_date").order_by("-update_date")

    krs = (
        KeyResult.objects.select_related("objective", "objective__strategy", "objective__strategy__entity")
        .prefetch_related(Prefetch("updates", queryset=update_qs, to_attr="updates_all"))
        .filter(q)
    )

    at_risk = []
    for kr in krs:
        obj = kr.objective
        tv = float(kr.target_value or 0)
        cv = float(kr.current_value or 0)

        overdue = bool(obj.end_date and obj.end_date < today)
        behind = (tv > 0 and cv < tv)

        if overdue and behind:
            last_update = (kr.updates_all[0].update_date if getattr(kr, "updates_all", []) else None)
            at_risk.append((kr, last_update))

    # Sort: most overdue + oldest updates first (None last)
    at_risk.sort(key=lambda t: (t[1] is None, t[1] or today))

    return render(request, "okr/kr_at_risk_list.html", {"at_risk": at_risk})


class StoryListView(ListView):
    model = Story
    template_name = "okr/story_list.html"
    context_object_name = "stories"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            Story.objects
            .select_related("epic", "epic__key_result", "epic__key_result__objective")
            .annotate(task_count=Count("tasks", distinct=True))
            .order_by("-updated_at", "-created_at")
        )

        epic_id = (self.request.GET.get("epic") or "").strip()
        if epic_id.isdigit():
            qs = qs.filter(epic_id=int(epic_id))

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(role__icontains=q) |
                Q(goal__icontains=q) |
                Q(reason__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["epic_id"] = (self.request.GET.get("epic") or "").strip()
        ctx["q"] = (self.request.GET.get("q") or "").strip()
        return ctx


class TaskDetailView(DetailView):
    model = Task
    template_name = "okr/task_detail.html"
    context_object_name = "task"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ct = ContentType.objects.get_for_model(Task)

        ctx["ai_artifacts"] = AiArtifact.objects.filter(content_type=ct, object_id=self.object.pk).order_by(
            "-created_at")[:10]
        ctx["attachments"] = (
            FileAttachment.objects
            .select_related("file_asset")
            .filter(content_type=ct, object_id=self.object.pk)
            .order_by("-created_at")
        )
        return ctx

class TaskListView(ListView):
    model = Task
    template_name = "okr/task_list.html"
    context_object_name = "tasks"
    paginate_by = 50

    def get_queryset(self):
        qs = (
            Task.objects
            .select_related("story")
            .order_by("completed", "due_date", "-updated_at")
        )

        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()

        if status:
            qs = qs.filter(status=status)

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(notes__icontains=q) |
                Q(story__title__icontains=q)
            )

        return qs

class TaskUpdateView(UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "okr/task_edit.html"

    def get_success_url(self):
        return reverse("okr:task-detail", kwargs={"pk": self.object.pk})

RATES = {
    "gpt-4o": {"input": Decimal("2.50"), "cached_input": Decimal("1.25"), "output": Decimal("10.00")},
    "gpt-4o-mini": {"input": Decimal("0.15"), "cached_input": Decimal("0.08"), "output": Decimal("0.60")},
}

def estimate_cost(model, input_tokens, output_tokens, cached_input_tokens=0):
    rates = RATES.get(model)
    if not rates:
        return Decimal("0.000000")
    uncached = max(0, int(input_tokens) - int(cached_input_tokens))
    cost = (
        Decimal(uncached) * rates["input"] +
        Decimal(int(cached_input_tokens)) * rates["cached_input"] +
        Decimal(int(output_tokens)) * rates["output"]
    ) / Decimal("1000000")
    return cost.quantize(Decimal("0.000001"))

@login_required
def task_analyze_attachments(request, pk):
    task = get_object_or_404(Task, pk=pk)

    ct = ContentType.objects.get_for_model(Task)
    attachments = (
        FileAttachment.objects
        .select_related("file_asset")
        .filter(content_type=ct, object_id=task.pk)
        .order_by("-created_at")
    )

    if not attachments.exists():
        task.notes = (task.notes or "") + "\n\n[AI] No attachments found to analyze."
        task.save(update_fields=["notes", "updated_at"])
        return redirect("okr:task-detail", pk=task.pk)

    # Upload each file to OpenAI and collect file IDs
    file_ids = []
    used_attachments = []
    for a in attachments:
        fpath = a.file_asset.file.path

        # (Optional) defensive: fix legacy uploads/uploads paths
        if not os.path.exists(fpath) and (os.sep + "uploads" + os.sep + "uploads" + os.sep) in fpath:
            fpath2 = fpath.replace(os.sep + "uploads" + os.sep + "uploads" + os.sep,
                                   os.sep + "uploads" + os.sep, 1)
            if os.path.exists(fpath2):
                fpath = fpath2

        with open(fpath, "rb") as fh:
            uploaded = client.files.create(file=fh, purpose="assistants")
        file_ids.append(uploaded.id)
        used_attachments.append(a)

    prompt = f"""
You are analyzing documents attached to an internal task.

Task title: {task.title}

Please produce:
1) Executive summary (5-10 bullets)
2) Key numbers / highlights (if financial)
3) Risks / red flags
4) Recommended next actions (as checklist)
5) Questions to clarify

Be careful: only cite facts that appear in the documents.
""".strip()

    resp = client.responses.create(
        model="gpt-4o",
        input=[{
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}] +
                       [{"type": "input_file", "file_id": fid} for fid in file_ids]
        }]
    )

    analysis_text = resp.output_text
    model_name = getattr(resp, "model", "") or "gpt-4o"

    # ---- 1) Create usage event (apps/common) ----
    usage = getattr(resp, "usage", None) or {}
    input_tokens = int(getattr(usage, "input_tokens", 0) or usage.get("input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or usage.get("output_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or usage.get("total_tokens", 0) or (input_tokens + output_tokens))

    def _uval(obj, key, default=0):
        """
        Safe getter for OpenAI SDK usage objects:
        - works if obj is dict
        - works if obj is pydantic/object with attributes
        """
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    usage = getattr(resp, "usage", None)

    input_tokens = int(_uval(usage, "input_tokens", 0) or 0)
    output_tokens = int(_uval(usage, "output_tokens", 0) or 0)
    total_tokens = int(_uval(usage, "total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))

    itd = _uval(usage, "input_tokens_details", None)
    otd = _uval(usage, "output_tokens_details", None)

    cached = int(_uval(itd, "cached_tokens", 0) or 0)
    reasoning = int(_uval(otd, "reasoning_tokens", 0) or 0)

    cost_usd = estimate_cost(model_name, input_tokens, output_tokens, cached_input_tokens=cached)

    usage_event = AiUsageEvent.objects.create(
        content_type=ct,
        object_id=task.pk,
        actor=request.user,
        action="analyze_attachments",
        model=model_name,
        input_tokens=input_tokens,
        cached_input_tokens=cached,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        meta={"file_count": len(file_ids), "file_ids": file_ids},
    )

    # ---- 2) Save artifact in Mnemos (portable) ----
    artifact = AiArtifact.objects.create(
        content_type=ct,
        object_id=task.pk,
        artifact_type="analysis",
        title=f"Task Analysis: {task.title}",
        prompt=prompt,
        output_text=analysis_text,
        model=model_name,
        created_by=request.user,
        usage_event_id=usage_event.pk,   # ✅ put it right here...
    )
    artifact.attachments.set(used_attachments)

    # ---- 3) Append once into task.notes (working copy) ----
    stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n\n---\n[AI analysis @ {stamp}] (model={model_name}, tokens={total_tokens}, est=${cost_usd})\n{analysis_text}\n"
    task.notes = (task.notes or "").strip() + block
    task.save(update_fields=["notes", "updated_at"])

    return redirect("okr:task-detail", pk=task.pk)



"""      - One of the following named colorscales:
            ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
             'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
             'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
             'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
             'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
             'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
             'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
             'orrd', 'oryel', 'oxy', 'peach', 'phase', 'picnic', 'pinkyl',
             'piyg', 'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn',
             'puor', 'purd', 'purp', 'purples', 'purpor', 'rainbow', 'rdbu',
             'rdgy', 'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar',
             'spectral', 'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn',
             'tealrose', 'tempo', 'temps', 'thermal', 'tropic', 'turbid',
             'turbo', 'twilight', 'viridis', 'ylgn', 'ylgnbu', 'ylorbr',
             'ylorrd']."""