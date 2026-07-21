import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from topics.models import Section, Subject, Topic
from users.models import UserPreferences
from planner.models import Task
from planner.services import (
    find_matching_task,
    record_task_focus,
    task_matches_context,
    task_progress_payload,
)

from .models import StudySession, StudySessionSegment


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def _user_local_date(user):
    preferences, _ = UserPreferences.objects.get_or_create(user=user)
    try:
        user_timezone = ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")
    return timezone.now().astimezone(user_timezone).date()


class StudyContextError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _resolve_study_context(user, *, topic_id=None, section_id=None, subject_id=None):
    topic = None
    section = None
    subject = None

    if subject_id:
        subject = (
            Subject.objects
            .filter(id=subject_id, section__topic__user=user)
            .select_related("section", "section__topic")
            .first()
        )
        if not subject:
            raise StudyContextError("Subject not found", status=404)
        section = subject.section
        topic = section.topic

    if section_id:
        requested_section = (
            Section.objects
            .filter(id=section_id, topic__user=user)
            .select_related("topic")
            .first()
        )
        if not requested_section:
            raise StudyContextError("Section not found", status=404)
        if subject and subject.section_id != requested_section.id:
            raise StudyContextError("Subject and section do not match")
        section = requested_section
        topic = section.topic

    if topic_id:
        requested_topic = Topic.objects.filter(id=topic_id, user=user).first()
        if not requested_topic:
            raise StudyContextError("Topic not found", status=404)
        if section and section.topic_id != requested_topic.id:
            raise StudyContextError("Topic and section do not match")
        topic = requested_topic

    return topic, section, subject


def _valid_activity_type(value):
    valid_activity_types = {choice[0] for choice in StudySession.ACTIVITY_CHOICES}
    return value if value in valid_activity_types else "general"


def _segment_matches(segment, *, topic, section, subject, activity_type):
    return (
        segment.topic_id == (topic.id if topic else None)
        and segment.section_id == (section.id if section else None)
        and segment.subject_id == (subject.id if subject else None)
        and segment.activity_type == activity_type
    )


def _create_segment(session, *, topic, section, subject, activity_type, offset):
    return StudySessionSegment.objects.create(
        session=session,
        topic=topic,
        section=section,
        subject=subject,
        activity_type=activity_type,
        topic_title=topic.title if topic else "",
        section_title=section.title if section else "",
        subject_title=subject.title if subject else "",
        started_offset_seconds=max(0, offset),
    )


def _close_current_segment(session, elapsed_seconds):
    segment = session.segments.order_by("-id").first()
    if not segment:
        segment = _create_segment(
            session,
            topic=session.topic,
            section=session.section,
            subject=session.subject,
            activity_type=session.activity_type,
            offset=0,
        )
    segment.duration_seconds = max(
        0,
        elapsed_seconds - segment.started_offset_seconds,
    )
    segment.save(update_fields=["duration_seconds"])
    return segment


def _task_focus_duration(session):
    if not session.task_id:
        return 0
    segments = list(
        session.segments.select_related("topic", "section", "subject").all()
    )
    if not segments:
        return session.duration_seconds
    return sum(
        segment.duration_seconds
        for segment in segments
        if task_matches_context(
            session.task,
            topic=segment.topic,
            section=segment.section,
            subject=segment.subject,
            activity_type=segment.activity_type,
        )
    )


@login_required
def start_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    topic_id = data.get("topic_id")
    subject_id = data.get("subject_id")
    section_id = data.get("section_id")
    task = None
    task_id = data.get("task_id")
    if task_id:
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid study task"}, status=400)
        task = (
            Task.objects.filter(
                id=task_id,
                user=request.user,
                completed=False,
                target_minutes__gt=0,
            )
            .select_related("topic", "section", "subject")
            .first()
        )
        if not task:
            return JsonResponse({"error": "Study task not found"}, status=404)

        if not any((topic_id, section_id, subject_id)):
            topic_id = task.topic_id
            section_id = task.section_id
            subject_id = task.subject_id
    try:
        planned_duration = int(data.get("planned_duration_seconds") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid planned duration"}, status=400)
    if planned_duration and not 1 <= planned_duration <= 24 * 60 * 60:
        return JsonResponse({"error": "Invalid planned duration"}, status=400)

    activity_type = data.get("activity_type", "general")
    if task and not any(data.get(key) for key in ("topic_id", "section_id", "subject_id")):
        if task.activity_type != "any":
            activity_type = task.activity_type
    activity_type = _valid_activity_type(activity_type)
    try:
        topic, section, subject = _resolve_study_context(
            request.user,
            topic_id=topic_id,
            section_id=section_id,
            subject_id=subject_id,
        )
    except StudyContextError as error:
        return JsonResponse({"error": str(error)}, status=error.status)

    if task:
        if not task_matches_context(
            task,
            topic=topic,
            section=section,
            subject=subject,
            activity_type=activity_type,
        ):
            return JsonResponse(
                {"error": "This page does not match the selected study task."},
                status=400,
            )
    else:
        task = find_matching_task(
            request.user,
            topic=topic,
            section=section,
            subject=subject,
            activity_type=activity_type,
            local_date=_user_local_date(request.user),
        )

    now = timezone.now()
    StudySession.objects.filter(
        user=request.user,
        completed=False,
        ended_at__isnull=True,
    ).update(ended_at=now, status="cancelled")

    session = StudySession.objects.create(
        user=request.user,
        started_at=now,
        task=task,
        topic=topic,
        subject=subject,
        section=section,
        planned_duration_seconds=planned_duration,
        activity_type=activity_type,
        topic_title=topic.title if topic else "",
        subject_title=subject.title if subject else "",
        section_title=section.title if section else "",
        status="active",
    )
    _create_segment(
        session,
        topic=topic,
        section=section,
        subject=subject,
        activity_type=activity_type,
        offset=0,
    )
    return JsonResponse({
        "success": True,
        "session_id": session.id,
        "task": task_progress_payload(task) if task else None,
    })


@login_required
@transaction.atomic
def sync_session_context(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        elapsed_seconds = int(data.get("elapsed_seconds") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid elapsed time"}, status=400)
    if not 0 <= elapsed_seconds <= 24 * 60 * 60:
        return JsonResponse({"error": "Invalid elapsed time"}, status=400)

    session = (
        StudySession.objects
        .select_for_update()
        .filter(
            id=data.get("session_id"),
            user=request.user,
            completed=False,
            ended_at__isnull=True,
            status="active",
        )
        .first()
    )
    if not session:
        return JsonResponse({"error": "No active session"}, status=404)

    try:
        topic, section, subject = _resolve_study_context(
            request.user,
            topic_id=data.get("topic_id"),
            section_id=data.get("section_id"),
            subject_id=data.get("subject_id"),
        )
    except StudyContextError as error:
        return JsonResponse({"error": str(error)}, status=error.status)
    activity_type = _valid_activity_type(data.get("activity_type", "general"))

    current_segment = session.segments.order_by("-id").first()
    if current_segment:
        elapsed_seconds = max(
            elapsed_seconds,
            current_segment.started_offset_seconds,
        )
    if current_segment and _segment_matches(
        current_segment,
        topic=topic,
        section=section,
        subject=subject,
        activity_type=activity_type,
    ):
        return JsonResponse({"success": True, "changed": False})

    _close_current_segment(session, elapsed_seconds)
    _create_segment(
        session,
        topic=topic,
        section=section,
        subject=subject,
        activity_type=activity_type,
        offset=elapsed_seconds,
    )

    session.topic = topic
    session.section = section
    session.subject = subject
    session.activity_type = activity_type
    session.topic_title = topic.title if topic else ""
    session.section_title = section.title if section else ""
    session.subject_title = subject.title if subject else ""
    session.save(update_fields=[
        "topic",
        "section",
        "subject",
        "activity_type",
        "topic_title",
        "section_title",
        "subject_title",
    ])
    return JsonResponse({"success": True, "changed": True})


@login_required
@transaction.atomic
def stop_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    session_id = data.get("session_id")
    sessions = StudySession.objects.select_for_update().filter(user=request.user)
    if session_id:
        session = sessions.filter(id=session_id).first()
    else:
        session = (
            sessions
            .filter(completed=False, ended_at__isnull=True)
            .order_by("-started_at")
            .first()
        )

    if not session:
        return JsonResponse({"error": "No active session"}, status=404)

    if session.completed:
        return JsonResponse({
            "success": True,
            "duration": session.duration_seconds,
            "already_completed": True,
            "task": task_progress_payload(session.task) if session.task_id else None,
        })

    requested_duration = data.get("duration_seconds")
    if requested_duration is not None:
        try:
            requested_duration = int(requested_duration)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid duration"}, status=400)
        if not 1 <= requested_duration <= 24 * 60 * 60:
            return JsonResponse({"error": "Invalid duration"}, status=400)
        latest_segment = session.segments.order_by("-id").first()
        if (
            latest_segment
            and requested_duration < latest_segment.started_offset_seconds
        ):
            return JsonResponse({"error": "Duration is shorter than tracked context"}, status=400)

    session.ended_at = timezone.now()
    session.duration_seconds = requested_duration or max(
        1,
        int((session.ended_at - session.started_at).total_seconds()),
    )
    try:
        session.paused_seconds = max(0, int(data.get("paused_seconds") or 0))
    except (TypeError, ValueError):
        session.paused_seconds = 0
    session.status = "completed"
    session.completed = True
    _close_current_segment(session, session.duration_seconds)
    session.save(update_fields=[
        "ended_at",
        "duration_seconds",
        "paused_seconds",
        "status",
        "completed",
    ])

    task_update = record_task_focus(session.task_id, _task_focus_duration(session))

    return JsonResponse({
        "success": True,
        "duration": session.duration_seconds,
        "task": task_update,
    })


@login_required
def cancel_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    session = StudySession.objects.filter(
        id=data.get("session_id"),
        user=request.user,
    ).first()
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)

    if not session.completed:
        session.ended_at = timezone.now()
        session.duration_seconds = 0
        session.status = "cancelled"
        session.save(update_fields=["ended_at", "duration_seconds", "status"])

    return JsonResponse({"success": True})


@login_required
def activity(request):
    try:
        year = int(request.GET.get("year", timezone.localdate().year))
        month = int(request.GET.get("month", timezone.localdate().month))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid month"}, status=400)

    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return JsonResponse({"error": "Invalid month"}, status=400)

    preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
    try:
        user_timezone = ZoneInfo(preferences.timezone)
    except ZoneInfoNotFoundError:
        user_timezone = ZoneInfo("UTC")
    month_start = datetime(year, month, 1, tzinfo=user_timezone)
    next_month = (
        datetime(year + 1, 1, 1, tzinfo=user_timezone)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=user_timezone)
    )
    sessions = StudySession.objects.filter(
        user=request.user,
        completed=True,
        status="completed",
        ended_at__gte=month_start,
        ended_at__lt=next_month,
    ).values_list("ended_at", "duration_seconds")
    days = {}
    for ended_at, duration_seconds in sessions:
        date_key = ended_at.astimezone(user_timezone).date().isoformat()
        item = days.setdefault(date_key, {"date": date_key, "count": 0, "duration_seconds": 0})
        item["count"] += 1
        item["duration_seconds"] += duration_seconds
    tasks = []
    local_today = timezone.now().astimezone(user_timezone).date()
    for task in Task.objects.filter(
        user=request.user,
        due_date__gte=month_start.date(),
        due_date__lt=next_month.date(),
    ).values("due_date", "completed"):
        tasks.append({
            "date": task["due_date"].isoformat(),
            "completed": task["completed"],
            "missed": task["due_date"] < local_today and not task["completed"],
        })

    return JsonResponse({
        "days": [days[key] for key in sorted(days)],
        "tasks": tasks,
    })
