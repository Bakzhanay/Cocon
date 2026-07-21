from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Task


def task_matches_context(task, *, topic, section, subject, activity_type):
    if task.activity_type != "any" and task.activity_type != activity_type:
        return False
    if task.subject_id:
        return subject is not None and task.subject_id == subject.id
    if task.section_id:
        return section is not None and task.section_id == section.id
    if task.topic_id:
        return topic is not None and task.topic_id == topic.id
    return True


def find_matching_task(user, *, topic, section, subject, activity_type, local_date):
    candidates = list(
        Task.objects.filter(
            Q(due_date__isnull=True) | Q(due_date__lte=local_date),
            user=user,
            completed=False,
            target_minutes__gt=0,
        ).select_related("topic", "section", "subject")
    )
    matches = [
        task for task in candidates
        if task_matches_context(
            task,
            topic=topic,
            section=section,
            subject=subject,
            activity_type=activity_type,
        )
    ]
    if not matches:
        return None

    def priority(task):
        specificity = 3 if task.subject_id else 2 if task.section_id else 1 if task.topic_id else 0
        activity_specificity = 1 if task.activity_type != "any" else 0
        return (
            -specificity,
            -activity_specificity,
            task.due_date or date.max,
            task.created_at,
            task.id,
        )

    return sorted(matches, key=priority)[0]


def task_progress_payload(task):
    return {
        "id": task.id,
        "title": task.title,
        "focused_seconds": task.focused_seconds,
        "focused_minutes": task.focused_minutes,
        "target_minutes": task.target_minutes,
        "remaining_minutes": task.remaining_minutes,
        "progress_percent": task.progress_percent,
        "completed": task.completed,
        "completed_by_focus": task.completed_by_focus,
    }


def record_task_focus(task_id, duration_seconds):
    if not task_id or duration_seconds <= 0:
        return None

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(id=task_id).first()
        if not task or not task.is_study_task:
            return None

        task.focused_seconds += duration_seconds
        if task.focused_seconds >= task.target_seconds:
            task.completed = True
            task.completed_at = timezone.now()
            task.completed_by_focus = True
        task.save(
            update_fields=[
                "focused_seconds",
                "completed",
                "completed_at",
                "completed_by_focus",
            ]
        )
    return task_progress_payload(task)
