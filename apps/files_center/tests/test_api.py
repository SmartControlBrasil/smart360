from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import FileCollection, FileLink, StoredFile


class FilesCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="files@smart360.local",
            password="StrongPass123",
            first_name="Files",
        )
        self.client.force_authenticate(self.user)

    def test_create_category_and_file(self):
        category_response = self.client.post(
            reverse("files-categories-list"),
            {
                "name": "Technical Document",
                "description": "Technical docs",
                "is_active": True,
                "ordering": 1,
            },
            format="json",
        )
        self.assertEqual(category_response.status_code, status.HTTP_201_CREATED)

        uploaded = SimpleUploadedFile("manual.pdf", b"pdf-binary-content", content_type="application/pdf")
        file_response = self.client.post(
            reverse("files-files-list"),
            {
                "original_name": "manual.pdf",
                "file": uploaded,
                "mime_type": "application/pdf",
                "category": category_response.data["id"],
                "storage_backend": "local",
                "visibility": "internal",
                "uploaded_by": self.user.id,
                "metadata": {"module": "knowledge_engine"},
            },
        )
        self.assertEqual(file_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StoredFile.objects.filter(original_name="manual.pdf").exists())

    def test_create_file_link(self):
        stored_file = StoredFile.objects.create(
            original_name="logo.png",
            stored_name="logo-test.png",
            file=SimpleUploadedFile("logo.png", b"img", content_type="image/png"),
            mime_type="image/png",
            size_bytes=3,
            uploaded_by=self.user,
        )
        response = self.client.post(
            reverse("files-file-links-list"),
            {
                "stored_file": stored_file.id,
                "related_module": "smart_site_factory",
                "related_item_type": "site_order",
                "related_item_id": "SO-100",
                "relation_type": "branding_logo",
                "is_primary": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FileLink.objects.filter(stored_file=stored_file, relation_type="branding_logo").exists())

    def test_create_collection_and_item(self):
        stored_file = StoredFile.objects.create(
            original_name="gallery.jpg",
            stored_name="gallery-test.jpg",
            file=SimpleUploadedFile("gallery.jpg", b"img", content_type="image/jpeg"),
            mime_type="image/jpeg",
            size_bytes=3,
            uploaded_by=self.user,
        )
        collection_response = self.client.post(
            reverse("files-collections-list"),
            {
                "name": "Product Gallery",
                "description": "Gallery collection",
                "collection_type": "gallery",
                "created_by": self.user.id,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(collection_response.status_code, status.HTTP_201_CREATED)

        item_response = self.client.post(
            reverse("files-collection-items-list"),
            {
                "collection": collection_response.data["id"],
                "stored_file": stored_file.id,
                "ordering": 1,
                "is_primary": True,
            },
            format="json",
        )
        self.assertEqual(item_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FileCollection.objects.filter(name="Product Gallery").exists())

