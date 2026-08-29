from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0005_task_completion_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="milestone",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
