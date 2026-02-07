from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Assembly

class AssemblyAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create initial test assemblies
        self.assembly1 = Assembly.objects.create(
            name="Ensembl v102",
            version="GRCh38",
            species="hsa"
        )
        self.assembly2 = Assembly.objects.create(
            name="UCSC Genome Browser",
            version="hg19",
            species="hsa"
        )
        self.valid_payload = {
            "name": "NCBI",
            "version": "GRCm38",
            "species": "mmu"
        }
        self.invalid_payload = {
            "name": "",
            "version": "",
            "species": "mmu"
        }

    def test_list_assemblies(self):
        response = self.client.get('/api/assemblies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_valid_assembly(self):
        response = self.client.post('/api/assemblies/', data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Assembly.objects.count(), 3)
        self.assertEqual(Assembly.objects.get(assembly_id=response.data['assembly_id']).name, 'NCBI')

    def test_create_invalid_assembly(self):
        response = self.client.post('/api/assemblies/', data=self.invalid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_single_assembly(self):
        response = self.client.get(f'/api/assemblies/{self.assembly1.assembly_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Ensembl v102')

    def test_update_assembly(self):
        response = self.client.patch(
            f'/api/assemblies/{self.assembly1.assembly_id}/',
            {'species': 'mmu'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_assembly = Assembly.objects.get(assembly_id=self.assembly1.assembly_id)
        self.assertEqual(updated_assembly.species, 'mmu')

    def test_delete_assembly(self):
        response = self.client.delete(f'/api/assemblies/{self.assembly2.assembly_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Assembly.objects.count(), 1)
