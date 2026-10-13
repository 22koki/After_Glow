import secrets
import hashlib
import hmac
import uuid

from django.conf import settings
from django.db import models


def private_memory_path(instance, filename):
    from pathlib import Path
    extension = Path(filename).suffix.lower()
    return f"memories/{instance.universe_id}/{uuid.uuid4().hex}{extension}"


class Universe(models.Model):
    OCCASIONS = [
        ("wedding", "Wedding"),
        ("birthday", "Birthday"),
        ("anniversary", "Anniversary"),
        ("graduation", "Graduation"),
        ("family", "Family"),
        ("tribute", "Tribute"),
        ("other", "Something special"),
    ]
    THEMES = [
        ("midnight", "Midnight indigo"),
        ("rose", "Dusty rose"),
        ("aurora", "Aurora"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="universes")
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=600, blank=True)
    occasion = models.CharField(max_length=24, choices=OCCASIONS, default="other")
    theme = models.CharField(max_length=24, choices=THEMES, default="midnight")
    event_date = models.DateField(null=True, blank=True)
    allow_guest_posts = models.BooleanField(default=True)
    invite_token_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def issue_invite(self):
        token = secrets.token_urlsafe(32)
        self.invite_token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.save(update_fields=["invite_token_hash"])
        return token

    def accepts_invite(self, token):
        if not token or not self.invite_token_hash or len(token) > 256:
            return False
        digest = hashlib.sha256(token.encode()).hexdigest()
        return hmac.compare_digest(digest, self.invite_token_hash)

    def __str__(self):
        return self.title


class Memory(models.Model):
    KINDS = [
        ("note", "Written note"),
        ("photo", "Photograph"),
        ("audio", "Voice recording"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    universe = models.ForeignKey(Universe, on_delete=models.CASCADE, related_name="memories")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=100)
    story = models.TextField(max_length=2000, blank=True)
    kind = models.CharField(max_length=10, choices=KINDS, default="note")
    attachment = models.FileField(upload_to=private_memory_path, blank=True)
    author_name = models.CharField(max_length=80, default="Someone special")
    approved = models.BooleanField(default=False)
    unlock_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
