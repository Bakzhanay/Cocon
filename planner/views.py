from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task


@login_required
@require_POST
def add_task(request):
    form = TaskForm(request.POST, user=request.user)
    if form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        messages.success(
            request,
            "Study plan added." if task.is_study_task else "Task added.",
        )
    else:
        error_text = " ".join(
            error
            for errors in form.errors.values()
            for error in errors
        )
        messages.error(request, error_text or "The task could not be added.")
    return redirect("topics:home")


@login_required
@require_POST
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.mark_manually(not task.completed)
    task.save(update_fields=["completed", "completed_at", "completed_by_focus"])
    return redirect("topics:home")


@login_required
@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    return redirect("topics:home")
