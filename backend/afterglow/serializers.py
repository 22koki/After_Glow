from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from .models import Memory, Universe


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=80)
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value


class UniverseSerializer(serializers.ModelSerializer):
    memory_count = serializers.IntegerField(source="memories.count", read_only=True)

    class Meta:
        model = Universe
        fields = [
            "id", "title", "description", "occasion", "theme",
            "event_date", "allow_guest_posts", "created_at", "memory_count",
        ]
        read_only_fields = ["id", "created_at", "memory_count"]


class MemoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = ["title", "story", "kind", "attachment", "author_name", "unlock_at"]
        extra_kwargs = {
            "attachment": {"required": False, "allow_empty_file": False},
            "story": {"required": False, "allow_blank": True},
            "unlock_at": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        kind = attrs.get("kind", "note")
        attachment = attrs.get("attachment")
        story = attrs.get("story", "").strip()
        if kind == "note" and not story:
            raise serializers.ValidationError({"story": "Write something to remember."})
        if kind != "note" and not attachment:
            raise serializers.ValidationError({"attachment": "Choose a photo or voice recording."})
        if kind == "note" and attachment:
            raise serializers.ValidationError({"attachment": "Written notes cannot include an attachment."})
        if attachment:
            if attachment.size > 8 * 1024 * 1024:
                raise serializers.ValidationError({"attachment": "Maximum file size is 8 MB."})
            extension = Path(attachment.name).suffix.lower()
            declared_type = getattr(attachment, "content_type", "")
            if kind == "photo":
                allowed = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
                if extension not in allowed or declared_type not in {"image/jpeg", "image/png", "image/webp"}:
                    raise serializers.ValidationError({"attachment": "Upload a JPG, PNG, or WEBP image."})
                try:
                    with Image.open(attachment) as image:
                        if image.format != allowed[extension]:
                            raise ValueError("Mismatched format")
                        image.verify()
                except (UnidentifiedImageError, OSError, ValueError):
                    raise serializers.ValidationError({"attachment": "This is not a valid image file."})
                finally:
                    attachment.seek(0)
            if kind == "audio":
                allowed_audio = {
                    ".mp3": {"audio/mpeg", "audio/mp3"},
                    ".m4a": {"audio/mp4", "audio/x-m4a"},
                    ".wav": {"audio/wav", "audio/x-wav", "audio/wave"},
                    ".webm": {"audio/webm"},
                    ".ogg": {"audio/ogg"},
                }
                if extension not in allowed_audio or declared_type not in allowed_audio[extension]:
                    raise serializers.ValidationError({"attachment": "Upload MP3, M4A, WAV, WEBM or OGG audio."})
        return attrs


class MemorySerializer(serializers.ModelSerializer):
    locked = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    story = serializers.SerializerMethodField()

    class Meta:
        model = Memory
        fields = [
            "id", "title", "story", "kind", "author_name", "approved",
            "created_at", "unlock_at", "locked", "media_url",
        ]

    def get_locked(self, obj):
        return bool(obj.unlock_at and obj.unlock_at > timezone.now())

    def get_title(self, obj):
        return "A sealed memory" if self.get_locked(obj) else obj.title

    def get_story(self, obj):
        return "" if self.get_locked(obj) else obj.story

    def get_media_url(self, obj):
        if self.get_locked(obj) or not obj.attachment:
            return None
        return f"/api/memories/{obj.id}/media/"
