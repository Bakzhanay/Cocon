from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0010_note_is_pinned_quicknote"),
    ]

    operations = [
        migrations.AddField(
            model_name="quicknote",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name="quicknote",
            options={"ordering": ["-is_pinned", "-updated_at"]},
        ),
    ]
