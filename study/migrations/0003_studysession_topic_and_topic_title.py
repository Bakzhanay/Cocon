import django.db.models.deletion
from django.db import migrations, models


def backfill_session_topics(apps, schema_editor):
    StudySession = apps.get_model("study", "StudySession")
    for session in StudySession.objects.select_related("subject__section__topic", "section__topic"):
        topic = None
        if session.subject_id:
            topic = session.subject.section.topic
        elif session.section_id:
            topic = session.section.topic
        if topic:
            session.topic_id = topic.id
            session.topic_title = topic.title
            session.save(update_fields=["topic", "topic_title"])


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0002_studysession_activity_type_and_more"),
        ("topics", "0002_subject_priority_subject_weekly_goal_minutes"),
    ]

    operations = [
        migrations.AddField(
            model_name="studysession",
            name="topic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="topics.topic",
            ),
        ),
        migrations.AddField(
            model_name="studysession",
            name="topic_title",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.RunPython(backfill_session_topics, migrations.RunPython.noop),
    ]
