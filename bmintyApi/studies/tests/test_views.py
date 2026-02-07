# studies/tests/test_views.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from studies.models import Study

class StudyAPITest(APITestCase):
    def setUp(self):
        # create a couple of studies
        self.s1 = Study.objects.create(
            external_id='ext1',
            external_repo='repo1',
            name='Study One',
            description='First',
            availability=True
        )
        self.s2 = Study.objects.create(
            external_id='ext2',
            external_repo='repo2',
            name='Study Two',
            description='Second',
            availability=False
        )

    def test_list_all_studies(self):
        url = reverse('study-list')  # or the name you gave in urls.py
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # no pagination, so resp.data is a list
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), 2)

    def test_filter_availability(self):
        url = reverse('study-list')
        resp = self.client.get(f"{url}?availability=true")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['external_id'], 'ext1')

    def test_get_detail(self):
        url = reverse('study-detail', kwargs={'study_id': self.s1.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'Study One')

    def test_create_study(self):
        url = reverse('study-list')
        payload = {
            'external_id':   'ext3',
            'external_repo': 'repo3',
            'name':          'Study Three',
            'description':   'Third',
            'availability':  True
        }
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Study.objects.filter(external_id='ext3').exists())
