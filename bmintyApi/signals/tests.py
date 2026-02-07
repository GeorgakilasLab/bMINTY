from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from studies.models   import Study
from assay.models     import Assay
from interval.models import Interval
from .models          import Cell, Signal

class CellAPITestCase(APITestCase):
    def setUp(self):
        self.base_url = reverse('cell-list')

        # API payload: no assay field
        self.api_payload = {
            'name':         'CGTAGCTTCG',
            'x_coordinate': 100,
            'y_coordinate': 200,
            'z_coordinate': 50,
        }

        # ORM payload is identical
        self.orm_payload = dict(self.api_payload)

    def test_create_cell(self):
        resp = self.client.post(self.base_url, self.api_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cell.objects.count(), 1)
        self.assertEqual(Cell.objects.get().name, 'CGTAGCTTCG')

    def test_list_cells(self):
        Cell.objects.create(**self.orm_payload)
        resp = self.client.get(self.base_url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) >= 1)

    def test_retrieve_cell(self):
        cell = Cell.objects.create(**self.orm_payload)
        url  = reverse('cell-detail', args=[cell.cell_id])
        resp = self.client.get(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['cell_id'], cell.cell_id)

    def test_update_cell(self):
        cell = Cell.objects.create(**self.orm_payload)
        url  = reverse('cell-detail', args=[cell.cell_id])
        resp = self.client.patch(url, {'name': 'NEWNAME'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cell.refresh_from_db()
        self.assertEqual(cell.name, 'NEWNAME')

    def test_delete_cell(self):
        cell = Cell.objects.create(**self.orm_payload)
        url  = reverse('cell-detail', args=[cell.cell_id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cell.objects.filter(cell_id=cell.cell_id).exists())


class SignalAPITestCase(APITestCase):
    def setUp(self):
        # Create the chain: Study → Assay → Interval
        self.study = Study.objects.create(
            external_id="STUDY123",
            name="Test Study",
            description="For signals",
            availability=True
        )
        self.assay = Assay.objects.create(
            external_id="GSM1",
            type="ChIP-Seq",
            target="GATA3",
            name="A1",
            tissue="Blood",
            cell_type="Macro",
            treatment="Treat",
            date="2024-03-17",
            platform="NextSeq",
            kit="TruSeq",
            description="D",
            study=self.study,
            availability=True
        )
        self.interval = Interval.objects.create(
            external_id="INT1",
            parent=None,
            name="int1",
            type="transcript",
            biotype=None,
            chromosome="chr1",
            start=100,
            end=200,
            strand="+",
            summit=None,
            assembly_id=1,
            availability=True
        )

        # Create a cell *without* assay
        self.cell = Cell.objects.create(
            name='CGTAGCTTCG',
            x_coordinate=100,
            y_coordinate=200,
            z_coordinate=50,
        )

        self.base_url    = reverse('signal-list')
        self.api_payload = {
            'signal':     500,
            'p_value':    None,
            'padj_value': None,
            'assay':      self.assay.pk,
            'interval':   self.interval.pk,
            'cell':       self.cell.pk,
        }
        self.orm_payload = {
            'signal':     500,
            'p_value':    None,
            'padj_value': None,
            'assay':      self.assay,
            'interval':   self.interval,
            'cell':       self.cell,
        }

    def test_create_signal(self):
        resp = self.client.post(self.base_url, self.api_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Signal.objects.count(), 1)
        self.assertEqual(Signal.objects.get().signal, 500)

    def test_list_signals(self):
        Signal.objects.create(**self.orm_payload)
        resp = self.client.get(self.base_url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(resp.data) >= 1)

    def test_retrieve_signal(self):
        sig = Signal.objects.create(**self.orm_payload)
        url = reverse('signal-detail', args=[sig.signal_id])
        resp = self.client.get(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['signal_id'], sig.signal_id)

    def test_update_signal(self):
        sig = Signal.objects.create(**self.orm_payload)
        url = reverse('signal-detail', args=[sig.signal_id])
        resp = self.client.patch(url, {'signal': 600}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sig.refresh_from_db()
        self.assertEqual(sig.signal, 600)

    def test_delete_signal(self):
        sig = Signal.objects.create(**self.orm_payload)
        url = reverse('signal-detail', args=[sig.signal_id])
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Signal.objects.filter(signal_id=sig.signal_id).exists())
