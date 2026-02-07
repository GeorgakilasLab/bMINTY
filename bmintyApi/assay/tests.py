from django.test import TestCase

from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from studies.models import Study 
from assay.models import Assay
from django.utils import timezone

class AssayViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.study = Study.objects.create(
            external_id="STUDY123",
            name="Study 1",
            description="Study on tamoxifen treatment.",
            availability=True
        )
        self.assay_data = {
            "external_id": "GSM111222",
            "type": "ChIP-Seq",
            "target": "GATA3",
            "name": "Patient 1",
            "tissue": "Peripheral blood",
            "cell_type": "Macrophages",
            "treatment": "Treated with tamoxifen",
            "date": "2024-03-17",
            "platform": "Illumina NextSeq 2000",
            "kit": "TruSeq ChIP Library Preparation Kit",
            "description": "Investigating the effect of tamoxifen.",
            "study": self.study,
            "availability": True
        }
        self.assay_url = reverse('assay-list-create', args=[self.study.id])

    def test_create_assay(self):
        """Test creating a new assay"""
        # Modify the assay data to pass the id instead of the study object
        self.assay_data["study"] = self.study.id  # Use the id, not the study object
        
        response = self.client.post(self.assay_url, self.assay_data, format='json')
        
        # Check if the assay was created successfully
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Assay.objects.count(), 1)
        self.assertEqual(Assay.objects.get().name, 'Patient 1')


    def test_list_assays(self):
        """Test listing all assays"""
        # Pass the Study instance directly instead of the id
        self.assay_data["study"] = self.study  # This line ensures the study is a valid instance
        
        Assay.objects.create(**self.assay_data)
        response = self.client.get(self.assay_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_assay(self):
        """Test updating an assay"""
        assay = Assay.objects.create(**self.assay_data)
        update_data = {
            "name": "Updated Assay",
            "availability": False,
            "study": assay.study.id,  # Include the study field
            "external_id": "new_external_id",  # Add external_id field
            "type": "new_type",  # Add type field
            "treatment": "new_treatment",  # Add treatment field
            "platform": "new_platform",  # Add platform field
            "kit": "new_kit"  # Add kit field
        }

        # Send the update request
        response = self.client.put(reverse('assay-detail', args=[assay.study.id, assay.assay_id]), update_data, format='json')
        
        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the update
        self.assertEqual(response.data['name'], 'Updated Assay')
        self.assertEqual(response.data['availability'], False)


class AssayStatusUpdateTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.study = Study.objects.create(
            external_id="STUDY123",
            name="Study 1",
            description="Study on tamoxifen treatment.",
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
            description="Investigating the effect of tamoxifen.",
            study=self.study,
            availability=True
        )
        self.status_url = reverse('assay-status-change', args=[self.study.id, self.assay.pk])

    def test_change_assay_status(self):
        """Test changing the availability of an assay"""
        data = {"availability": False}
        response = self.client.patch(self.status_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assay.refresh_from_db()  # Reload the assay to get updated data
        self.assertEqual(self.assay.availability, False)

    def test_invalid_status_change(self):
        """Test invalid status change with missing 'availability' field"""
        data = {}
        response = self.client.patch(self.status_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
