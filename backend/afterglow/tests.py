import hashlib
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Memory, Universe


class AfterglowAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="owner@example.com", password="TestPass123!", first_name="Alex"
        )
        self.universe = Universe.objects.create(owner=self.user, title="Our little cosmos")
        self.invite = self.universe.issue_invite("contribute")
        self.base = f"/api/universes/{self.universe.id}/"

    def owner(self):
        self.client.force_authenticate(self.user)

    def guest(self):
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.invite)

    def test_private_universe_requires_correct_invite(self):
        self.assertEqual(self.client.get(self.base).status_code, 404)
        self.guest()
        self.assertEqual(self.client.get(self.base).status_code, 200)

    def test_guest_submission_needs_approval(self):
        self.guest()
        created = self.client.post(self.base + "memories/", {
            "title": "A message", "story": "The happiest day", "kind": "note",
            "author_name": "Taylor",
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.data["approved"])
        self.assertEqual(len(self.client.get(self.base + "memories/").data), 0)

        self.owner()
        self.client.credentials()
        pending = self.client.get(self.base + "memories/").data
        self.assertEqual(len(pending), 1)
        self.assertEqual(self.client.post(
            f"/api/memories/{pending[0]['id']}/moderate/",
            {"action": "approve"},
        ).status_code, 200)

        self.guest()
        self.assertEqual(len(self.client.get(self.base + "memories/").data), 1)

    def test_future_capsule_never_reveals_content(self):
        self.owner()
        capsule = Memory.objects.create(
            universe=self.universe, title="Surprise", story="Private until tomorrow",
            kind="note", author_name="Alex", approved=True,
            unlock_at=timezone.now() + timedelta(days=1),
        )
        self.client.credentials()
        response = self.client.get(self.base + "memories/")
        self.assertEqual(response.data[0]["title"], "A sealed memory")
        self.assertEqual(response.data[0]["story"], "")
        self.assertTrue(response.data[0]["locked"])
        self.assertIsNone(response.data[0]["media_url"])

    def test_rotate_invite_invalidates_previous_link(self):
        self.owner()
        self.client.credentials()
        response = self.client.post(self.base + "invite/", {"mode": "contribute"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["invite_token"], self.invite)
        self.guest()
        self.assertEqual(self.client.get(self.base).status_code, 404)

    def test_guest_cannot_moderate(self):
        item = Memory.objects.create(universe=self.universe, title="Hello", story="Hi")
        self.guest()
        response = self.client.post(
            f"/api/memories/{item.id}/moderate/", {"action": "approve"}
        )
        self.assertIn(response.status_code, [401, 403])

    def test_media_url_cannot_bypass_invite(self):
        self.owner()
        with tempfile.TemporaryDirectory() as temp:
            with override_settings(MEDIA_ROOT=temp):
                item = Memory.objects.create(
                    universe=self.universe, title="Audio", kind="audio", approved=True
                )
                item.attachment.save("voice.mp3", SimpleUploadedFile("voice.mp3", b"ID3fake"))
                self.client.force_authenticate(user=None)
                self.client.credentials()
                self.assertEqual(
                    self.client.get(f"/api/memories/{item.id}/media/").status_code, 404
                )

    def test_cannot_claim_a_written_note_is_an_image(self):
        self.owner()
        self.client.credentials()
        upload = SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(self.base + "memories/", {
            "kind": "photo", "title": "Fake", "author_name": "Alex",
            "attachment": upload,
        }, format="multipart")
        self.assertEqual(response.status_code, 400)


class SharingAndEditingTests(APITestCase):
    def setUp(self):
        self.owner_user = get_user_model().objects.create_user(
            username="keeper@example.com", password="KeeperTest123!"
        )
        self.universe = Universe.objects.create(owner=self.owner_user, title="Eternal summer")
        self.view_key = self.universe.issue_invite("view")
        self.write_key = self.universe.issue_invite("contribute")
        self.base = f"/api/universes/{self.universe.id}/"

    def test_read_only_invite_cannot_post(self):
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.view_key)
        self.assertEqual(self.client.get(self.base).status_code, 200)
        response = self.client.post(self.base + "memories/", {
            "kind": "note", "title": "Unauthorized", "story": "No."
        }, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.universe.memories.count(), 0)

    def test_contribution_invite_requires_moderation(self):
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.write_key)
        self.assertTrue(self.client.get(self.base).data["can_contribute"])
        self.assertEqual(self.client.post(self.base + "memories/", {
            "kind": "note", "title": "First dance", "story": "In the moonlight"
        }, format="json").status_code, 201)
        self.assertEqual(self.client.get(self.base + "memories/").data, [])

    def test_sealed_memory_hidden_from_guests_not_owner(self):
        item = Memory.objects.create(
            universe=self.universe, title="A secret", story="For next year",
            approved=True, unlock_at=timezone.now() + timedelta(days=365),
        )
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.view_key)
        r = self.client.get(self.base + "memories/")
        self.assertEqual(r.data[0]["title"], "A sealed memory")
        self.assertEqual(r.data[0]["story"], "")
        self.client.credentials()
        self.client.force_authenticate(user=self.owner_user)
        r = self.client.get(self.base + "memories/")
        self.assertEqual(r.data[0]["title"], "A secret")
        self.assertEqual(r.data[0]["story"], "For next year")

    def test_only_owner_can_change_and_export(self):
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.write_key)
        self.assertEqual(self.client.patch(self.base, {"title": "Hacked"}, format="json").status_code, 403)
        self.assertEqual(self.client.get(self.base + "export/").status_code, 401)
        self.client.credentials()
        self.client.force_authenticate(user=self.owner_user)
        self.assertEqual(self.client.patch(self.base, {"title": "New title"}, format="json").status_code, 200)
        self.assertEqual(self.client.get(self.base + "export/").status_code, 200)

    def test_new_invitation_types_can_be_rotated_independently(self):
        self.client.force_authenticate(user=self.owner_user)
        rotated = self.client.post(self.base + "invite/", {"mode": "view"}, format="json")
        self.assertEqual(rotated.status_code, 200)
        self.assertNotEqual(rotated.data["invite_token"], self.view_key)
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.view_key)
        self.assertEqual(self.client.get(self.base).status_code, 404)
        self.client.credentials(HTTP_X_UNIVERSE_INVITE=self.write_key)
        self.assertEqual(self.client.get(self.base).status_code, 200)
