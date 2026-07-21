import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0001_initial"),
        ("topics", "0011_subject_soft_delete_and_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="activity_type",
            field=models.CharField(
                choices=[
                    ("any", "Any study activity"),
                    ("general", "General study"),
                    ("notes", "Notes"),
                    ("flashcards", "Flashcards"),
                    ("reading", "Reading"),
                ],
                default="any",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="completed_by_focus",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="task",
            name="focused_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="task",
            name="section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="planned_tasks",
                to="topics.section",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="subject",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="planned_tasks",
                to="topics.subject",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="target_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="task",
            name="topic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="planned_tasks",
                to="topics.topic",
            ),
        ),
    ]
