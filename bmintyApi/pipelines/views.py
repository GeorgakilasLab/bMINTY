# pipelines/views.py
from rest_framework import generics
from .models import Pipeline
from .serializers import PipelineSerializer

class PipelineListCreateAPIView(generics.ListCreateAPIView):
    """
    Pipeline list and creation endpoint.
    
    - GET: List all pipelines
    - POST: Create a new pipeline
    """
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer

class PipelineDetailAPIView(generics.RetrieveAPIView):
    """
    Pipeline detail endpoint (read-only).
    
    - GET: Retrieve pipeline details
    
    Note: Pipelines cannot be modified or deleted once created.
    """
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer
    lookup_field = 'pipeline_id'
