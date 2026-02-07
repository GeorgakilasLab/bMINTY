from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Interval
from .serializers import IntervalSerializer
from bmintyApi.pagination import CustomPageNumberPagination
import logging

logger = logging.getLogger(__name__)

class IntervalViewSet(viewsets.ModelViewSet):
    """
    Genomic Interval Management
    
    View genomic intervals (genes, peaks, regions) that are analyzed in assays.
    Intervals define the genomic features where signals are measured.
    
    **Read-Only Operations:**
    - **GET** `/api/intervals/` - List all intervals (paginated)
    - **GET** `/api/intervals/{id}/` - Get interval details
    
    **Note:** Intervals are imported via bulk importer only.
    Creation, updates, and deletion are not available through the API.
    
    **Interval Types:**
    - gene, exon, intron, promoter, enhancer, peak, etc.
    
    **Biotypes:**
    - protein_coding, lncRNA, miRNA, rRNA, pseudogene, etc.
    """
    queryset = Interval.objects.all()
    serializer_class = IntervalSerializer
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'head', 'options']  # Read-only access
    
    @swagger_auto_schema(
        operation_summary="List genomic intervals",
        operation_description="""
        Retrieve paginated list of genomic intervals with optional filtering.
        
        **Query Parameters:**
        - `availability`: Filter by availability (true/false)
        - `page`: Page number
        - `page_size`: Items per page
        """,
        manual_parameters=[
            openapi.Parameter('availability', openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Filter by availability"),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Page number"),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="Items per page"),
        ],
        responses={200: IntervalSerializer(many=True)},
        tags=['Intervals']
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Get interval details",
        operation_description="Retrieve detailed information about a specific genomic interval.",
        responses={200: IntervalSerializer, 404: "Interval not found"},
        tags=['Intervals']
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        availability = self.request.query_params.get('availability')
        logger.info(f"Fetching intervals - filter availability={availability}")
        if availability is not None:
            queryset = queryset.filter(availability=(availability.lower() == 'true'))
        return queryset    