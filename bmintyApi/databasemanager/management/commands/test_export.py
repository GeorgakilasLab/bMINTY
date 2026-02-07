from django.core.management.base import BaseCommand
from django.test import Client

class Command(BaseCommand):
    help = 'Test the export_filtered_sqlite endpoint'

    def handle(self, *args, **options):
        client = Client(SERVER_NAME='localhost')
        
        # Test the endpoint
        response = client.get('/api/export_filtered_sqlite/', HTTP_HOST='localhost')
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type', 'N/A')}")
        print(f"Content-Length: {len(response.content)}")
        print(f"First 200 bytes: {response.content[:200]}")
