from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SchemaAndDocsTests(APITestCase):
    def test_healthcheck_details_endpoint_responds(self):
        response = self.client.get(reverse("healthcheck-details"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schema_endpoint_responds(self):
        response = self.client.get(reverse("api-schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_endpoint_responds(self):
        response = self.client.get(reverse("swagger-ui"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_redoc_endpoint_responds(self):
        response = self.client.get(reverse("redoc"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
