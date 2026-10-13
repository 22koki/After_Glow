# Generated for Afterglow's initial private-memory models.
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import afterglow.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Universe",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, max_length=600)),
                ("occasion", models.CharField(choices=[("wedding", "Wedding"), ("birthday", "Birthday"), ("anniversary", "Anniversary"), ("graduation", "Graduation"), ("family", "Family"), ("tribute", "Tribute"), ("other", "Something special")], default="other", max_length=24)),
                ("theme", models.CharField(choices=[("midnight", "Midnight indigo"), ("rose", "Dusty rose"), ("aurora", "Aurora")], default="midnight", max_length=24)),
                ("event_date", models.DateField(blank=True, null=True)),
                ("allow_guest_posts", models.BooleanField(default=True)),
                ("invite_token_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="universes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Memory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=100)),
                ("story", models.TextField(blank=True, max_length=2000)),
                ("kind", models.CharField(choices=[("note", "Written note"), ("photo", "Photograph"), ("audio", "Voice recording")], default="note", max_length=10)),
                ("attachment", models.FileField(blank=True, upload_to=afterglow.models.private_memory_path)),
                ("author_name", models.CharField(default="Someone special", max_length=80)),
                ("approved", models.BooleanField(default=False)),
                ("unlock_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("universe", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memories", to="afterglow.universe")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
