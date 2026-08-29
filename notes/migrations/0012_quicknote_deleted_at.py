from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0011_quicknote_is_pinned"),
    ]

    operations = [
        migrations.AddField(
            model_name="quicknote",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
