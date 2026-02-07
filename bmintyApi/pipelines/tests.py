# pipelines/tests.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from studies.models import Study
from assay.models   import Assay
from .models        import Pipeline

class PipelineAPITestCase(APITestCase):
    def setUp(self):
        # 1) Create a Study & Assay so the FK chain is satisfied
        self.study = Study.objects.create(
            external_id="STUDY123",
            name="Study 1",
            description="Dummy study for pipelines tests",
            availability=True
        )
        self.assay = Assay.objects.create(
            external_id="GSM111222",
            type="ChIP-Seq",
            target="GATA3",
            name="Patient 1",
            tissue="Peripheral blood",
            cell_type="Macrophages",
            treatment="Treated with tamoxifen",
            date="2024-03-17",
            platform="Illumina NextSeq 2000",
            kit="TruSeq ChIP Library Preparation Kit",
            description="Dummy assay for pipelines tests",
            study=self.study,
            availability=True
        )

        # URL for list/create
        self.base_url = reverse('pipeline-list')

        # payload for the DRF client (assay as PK)
        self.api_payload = {
            'name':         'scRNA-Seq analysis',
            'description': (
                'the pipeline for analyzing scRNA-Seq from assay XX includes '
                'fastqc, fastp, star and htseq'
            ),
            'external_url': 'https://workflowhub.eu/xxxxxxxxxx',
            'assay':        self.assay.pk,
        }

        # payload for direct ORM creation (assay as instance)
        self.orm_payload = {
            'name':         self.api_payload['name'],
            'description':  self.api_payload['description'],
            'external_url': self.api_payload['external_url'],
            'assay':        self.assay,
        }

    def test_create_pipeline(self):
        response = self.client.post(self.base_url, self.api_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Pipeline.objects.count(), 1)
        self.assertEqual(Pipeline.objects.get().name, self.api_payload['name'])

    def test_list_pipelines(self):
        # create via ORM
        Pipeline.objects.create(**self.orm_payload)
        response = self.client.get(self.base_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_retrieve_pipeline(self):
        pipeline = Pipeline.objects.create(**self.orm_payload)
        url = reverse('pipeline-detail', args=[pipeline.pipeline_id])
        resp = self.client.get(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['pipeline_id'], pipeline.pipeline_id)

    def test_update_pipeline(self):
        pipeline = Pipeline.objects.create(**self.orm_payload)
        url = reverse('pipeline-detail', args=[pipeline.pipeline_id])
        data = {'name': 'updated name'}
        resp = self.client.patch(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        pipeline.refresh_from_db()
        self.assertEqual(pipeline.name, 'updated name')

    def test_delete_pipeline(self):
        pipeline = Pipeline.objects.create(**self.orm_payload)
        url = reverse('pipeline-detail', args=[pipeline.pipeline_id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pipeline.objects.filter(pk=pipeline.pipeline_id).exists())
