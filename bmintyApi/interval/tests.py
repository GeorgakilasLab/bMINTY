from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Interval

class IntervalAPITestCase(APITestCase):
    def setUp(self):
        # Assuming 'create-interval' is the name given in urls.py for the POST endpoint
        self.url = reverse('create-interval')
        self.valid_payload = {
            "external_id": "ENST8190381290381",
            "type": "transcript",
            "chromosome": "chr1",
            "start": 293109,
            "end": 391309,
            "strand": "1",
            "assembly_id": 1,
            "availability": True
        }

    def test_create_interval_success(self):
        """
        Test that a valid interval creation returns a 201 status code and
        that the interval is stored in the database.
        """
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interval.objects.count(), 1)
        interval = Interval.objects.first()
        self.assertEqual(interval.external_id, self.valid_payload["external_id"])

    def test_create_interval_missing_mandatory_field(self):
        """
        Test that creation fails when a mandatory field (e.g., external_id) is missing.
        """
        # Remove the mandatory field 'external_id'
        invalid_payload = self.valid_payload.copy()
        invalid_payload.pop('external_id')
        response = self.client.post(self.url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('external_id', response.data)

    def test_create_interval_missing_optional_field(self):
        """
        Test that the endpoint successfully creates an interval even if an optional field is missing.
        """
        # 'name' is an optional field; it's omitted here.
        payload = self.valid_payload.copy()
        # Ensure 'name' is not present in the payload
        payload.pop('name', None)
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interval.objects.count(), 1)

    def test_create_interval_invalid_type(self):
        """
        Test that providing an invalid 'type' (not in the predetermined choices)
        results in a 400 error.
        """
        payload = self.valid_payload.copy()
        payload['type'] = "invalid_type"
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('type', response.data)
