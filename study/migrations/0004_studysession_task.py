import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0002_study_tasks"),
        ("study", "0003_studysession_topic_and_topic_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="studysession",
            name="task",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="study_sessions",
                to="planner.task",
            ),
        ),
    ]
