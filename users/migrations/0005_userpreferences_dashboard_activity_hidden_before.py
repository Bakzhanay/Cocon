from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_userpreferences_auto_detect_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="userpreferences",
            name="dashboard_activity_hidden_before",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
