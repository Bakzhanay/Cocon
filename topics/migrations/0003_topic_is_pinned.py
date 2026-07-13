from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("topics", "0002_subject_priority_subject_weekly_goal_minutes"),
    ]

    operations = [
        migrations.AddField(
            model_name="topic",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name="topic",
            options={"ordering": ["-is_pinned", "title"]},
        ),
    ]
