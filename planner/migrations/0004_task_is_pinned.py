from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("planner", "0003_milestone"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="is_pinned",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
