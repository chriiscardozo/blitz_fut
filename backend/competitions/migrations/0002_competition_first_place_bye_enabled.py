from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="competition",
            name="first_place_bye_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
