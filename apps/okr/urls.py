from django.urls import path
from .views import ObjectiveListView, ObjectiveDetailView,\
    ObjectiveCreateView, KeyResultCreateView, KeyResultUpdateView,\
    KeyResultDeleteView, sunburst_okr_view, ObjectiveUpdateView, \
    StrategyListView, StrategyCreateView, StrategyDetailView, \
    StrategyUpdateView, StrategyDeleteView, EpicDetailView, \
    rewrite_objective_description_api, rewrite_keyresult_api,\
    keyresult_epics_view, OKRHierarchyView, EntityListView, \
    EntityStrategyListView, rewrite_strategy_description_api
from .views import EpicUpdateView, EpicDeleteView, EpicCreateView
from .views import StoryUpdateView, StoryDeleteView, StoryDetailView
from .views import rewrite_epic_description, generate_user_story, suggest_task_title, update_task_status
from .views import EntityCreateView, EntityDeleteView
from .views import strategy_heatmap, kr_at_risk_list, task_analyze_attachments
from .views import entity_sunburst_view, entity_hierarchy_view, entity_hierarchy_pdf, objective_scorecard_view
from .views import StoryListView, StoryCreateView, TaskDetailView, TaskListView, TaskUpdateView
from .views import TaskCreateView, keyresult_drawer_view

app_name = "okr"

urlpatterns = [
    path('', ObjectiveListView.as_view(), name='objective-list'),
    path('objective/<int:pk>/', ObjectiveDetailView.as_view(), name='objective-detail'),
    path('create/', ObjectiveCreateView.as_view(), name='objective-create'),
    path('<int:pk>/add-kr/', KeyResultCreateView.as_view(), name='keyresult-create'),
    path('kr/<int:pk>/update/', KeyResultUpdateView.as_view(), name='keyresult-update'),
    path('kr/<int:pk>/delete/', KeyResultDeleteView.as_view(), name='keyresult-delete'),
    path('keyresult/<int:pk>/epics/create/', EpicCreateView.as_view(), name='epic-create'),
    path('rewrite-keyresult/', rewrite_keyresult_api, name='rewrite-keyresult'),
    path('okr-visual/', sunburst_okr_view, name='okr_visual'),
    path("kr/<int:pk>/drawer/", keyresult_drawer_view, name="keyresult-drawer"),
    path('objective/<int:pk>/edit/', ObjectiveUpdateView.as_view(), name='objective-edit'),
    path('strategies/', StrategyListView.as_view(), name='strategy-list'),
    path('strategies/<int:pk>/', StrategyDetailView.as_view(), name='strategy-detail'),
    path('strategies/<int:pk>/edit/', StrategyUpdateView.as_view(), name='strategy-edit'),
    path('strategies/create/', StrategyCreateView.as_view(), name='strategy-create'),
    path('strategies/<int:pk>/delete/', StrategyDeleteView.as_view(), name='strategy-delete'),
    path('rewrite-objective-description/', rewrite_objective_description_api, name='rewrite-objective-description'),
    path('epics/<int:pk>/', EpicDetailView.as_view(), name='epic-detail'),
    path('epic/<int:pk>/edit/', EpicUpdateView.as_view(), name='epic-update'),
    path('epic/<int:pk>/delete/', EpicDeleteView.as_view(), name='epic-delete'),
    path("story/create/", StoryCreateView.as_view(), name="story-create"),
    path('stories/', StoryListView.as_view(), name='story-list'),
    path('story/<int:pk>/edit/', StoryUpdateView.as_view(), name='story-update'),
    path('story/<int:pk>/delete/', StoryDeleteView.as_view(), name='story-delete'),
    path('story/<int:pk>/', StoryDetailView.as_view(), name='story-detail'),
    path('keyresult/<int:pk>/epics/', keyresult_epics_view, name='keyresult-epics'),
    path('okr/hierarchy/', OKRHierarchyView.as_view(), name='okr-hierarchy'),
    path('entities/', EntityListView.as_view(), name='entity-list'),
    path('entity/<int:pk>/strategies/', EntityStrategyListView.as_view(), name='entity-strategies'),
    path('api/rewrite-strategy-description/', rewrite_strategy_description_api, name='rewrite-strategy-description'),
    path("api/rewrite-epic-description/", rewrite_epic_description, name="rewrite-epic-description"),
    path("api/generate-user-story/", generate_user_story, name="generate-user-story"),
    path("api/suggest-task-title/", suggest_task_title, name="suggest-task-title"),

    # Tasks
    path("stories/<int:story_id>/tasks/add/", TaskCreateView.as_view(), name="task-create-for-story"),
    path("tasks/", TaskListView.as_view(), name="task-list"),
    path('task/<int:pk>/update-status/', update_task_status, name='update-task-status'),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:pk>/edit/", TaskUpdateView.as_view(), name="task-edit"),
    path("tasks/<int:pk>/analyze/", task_analyze_attachments, name="task-analyze"),
    path('entities/create/', EntityCreateView.as_view(), name='entity-create'),
    path('entities/<int:pk>/delete/', EntityDeleteView.as_view(), name='entity-delete'),
    path('entities/<int:pk>/sunburst/', entity_sunburst_view, name='entity-sunburst'),
    path('entities/<int:pk>/hierarchy/', entity_hierarchy_view, name='entity-hierarchy'),
    path('entities/<int:pk>/hierarchy/pdf/', entity_hierarchy_pdf, name='entity-hierarchy-pdf'),
    path("objective/<int:pk>/scorecard/", objective_scorecard_view, name="objective-scorecard"),
    path("heatmap/", strategy_heatmap, name="strategy-heatmap"),
    path("krs/at-risk/", kr_at_risk_list, name="kr-at-risk-list"),
    path("tasks/add/", TaskCreateView.as_view(), name="task-create"),
]
