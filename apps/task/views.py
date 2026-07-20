from django.shortcuts import render, get_object_or_404, redirect
from apps.task.models import Task
from apps.task.forms import TaskForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

@login_required
def task_list(request):
    tasks = Task.objects.all().order_by('due_date')
    return render(request, 'task/task_list.html', {'tasks': tasks})

@login_required
def task_create(request):
    form = TaskForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('task:list')
    return render(request, 'task/task_form.html', {'form': form, 'title': 'Add Task'})

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=task)
    print("Edit")
    if form.is_valid():
        form.save()
        return redirect('task:list')
    return render(request, 'task/task_form.html', {'form': form, 'title': 'Edit Task'})

def kanban_view(request):
    return render(request, "task/kanban.html", {
        "todo": Task.objects.filter(status="todo"),
        "in_progress": Task.objects.filter(status="in_progress"),
        "completed": Task.objects.filter(status="completed"),
    })

@login_required
@require_POST
@csrf_protect
def update_task_status(request, task_id, new_status):
    if request.method == "POST":
        print("Task dropped", task_id, " status: ", new_status)
        Task.objects.filter(id=task_id).update(status=new_status)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)

@login_required
@require_POST
@csrf_protect
def delete_task(request, task_id):
    Task.objects.filter(id=task_id).delete()
    return JsonResponse({"success": True})

@login_required
def task_edit_tray(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskForm(instance=task)
    print("Save called")
    if request.method == "POST":
        print("Form post")
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            print("Form is valid")
            form.save()
            return JsonResponse({"success": True})
        else:
            print("❌ Form errors:", form.errors)

    if request.headers.get("HX-Request") or request.GET.get("ajax"):
        return render(request, "task/partials/task_edit_tray.html", {"form": form, "task": task})

    return redirect("task:list")  # fallback
