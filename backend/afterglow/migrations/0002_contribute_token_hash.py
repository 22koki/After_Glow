from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("afterglow", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="universe",
            name="contribute_token_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
