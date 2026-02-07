from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Assembly
from .serializers import AssemblySerializer
from bmintyApi.pagination import CustomPageNumberPagination
import logging

logger = logging.getLogger(__name__)

class AssemblyViewSet(viewsets.ModelViewSet):
    """
    Genome Assembly Management
    
    Manage genome assemblies (reference genomes) used in genomic intervals.
    Assemblies define the coordinate system for genomic data.
    
    **Operations:**
    - **GET** `/api/assemblies/` - List all assemblies (paginated)
    - **GET** `/api/assemblies/{id}/` - Get assembly details
    - **POST** `/api/assemblies/` - Create new assembly
    - **PATCH** `/api/assemblies/{id}/` - Update assembly
    
    **Common Assemblies:**
    - Human: GRCh38, GRCh37 (hg19)
    - Mouse: GRCm39, GRCm38
    - See NCBI or Ensembl for more assemblies
    """
    queryset = Assembly.objects.all()
    serializer_class = AssemblySerializer
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # Allow read, create, and update

    @swagger_auto_schema(
        operation_summary="List genome assemblies",
        operation_description="Retrieve paginated list of genome assemblies with optional filtering.",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number"),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Items per page"),
        ],
        responses={200: AssemblySerializer(many=True)},
        tags=['Assemblies']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Get assembly details",
        operation_description="Retrieve detailed information about a specific genome assembly.",
        responses={200: AssemblySerializer, 404: "Assembly not found"},
        tags=['Assemblies']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update assembly",
        operation_description="Partially update a genome assembly record (e.g., species, description).",
        request_body=AssemblySerializer,
        responses={200: AssemblySerializer, 400: "Validation error", 404: "Assembly not found"},
        tags=['Assemblies']
    )
    def partial_update(self, request, *args, **kwargs):
        logger.info(f"Patching assembly ID={kwargs.get('pk')} with data: {request.data}")
        response = super().partial_update(request, *args, **kwargs)
        logger.info(f"Patched assembly ID={kwargs.get('pk')}")
        return response
