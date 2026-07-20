from django.urls import path
from . import views

app_name = 'task'
urlpatterns = [
    path('', views.task_list, name='list'),
    path('add/', views.task_create, name='task_create'),
    path('edit/<int:pk>/', views.task_edit, name='task_edit'),
    path('edit-tray/<int:pk>/', views.task_edit_tray, name='edit_tray'),
    path('kanban/', views.kanban_view, name='kanban_view'),
    path('delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('update-status/<int:task_id>/<str:new_status>/', views.update_task_status, name='update_task_status'),
]
