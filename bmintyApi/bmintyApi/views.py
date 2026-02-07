from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import F
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from studies.models import Study
from assay.models import Assay
from interval.models import Interval
from assembly.models import Assembly
from signals.models import Signal, Cell
import logging

logger = logging.getLogger(__name__)


def home(request):
    return HttpResponse("Welcome to the API!")

# map “filter name” → (Model, model_field_name)
FIELD_MAP = {
    # Study-level
    'study_name':        (Study,    'name'),
    'study_external_id': (Study,    'external_id'),
    'study_repository':  (Study,    'external_repo'),
    'study_description': (Study,    'description'),
    'study_note':        (Study,    'note'),
    'study_availability':(Study,    'availability'),

    # Assay-level
    'assay_name':        (Assay,    'name'),
    'assay_external_id': (Assay,    'external_id'),
    'assay_type':        (Assay,    'type'),
    'tissue':            (Assay,    'tissue'),
    'assay_target':      (Assay,    'target'),
    'assay_date':        (Assay,    'date'),
    'assay_kit':         (Assay,    'kit'),
    'assay_cell_type':   (Assay,    'cell_type'),
    'treatment':         (Assay,    'treatment'),
    'assay_description': (Assay,    'description'),
    'assay_note':        (Assay,    'note'),
    'platform':          (Assay,    'platform'),

    # Interval-level
    'interval_type':     (Interval, 'type'),
    'biotype':           (Interval, 'biotype'),

    # Assembly-level
    'assembly_name':     (Assembly, 'name'),
    'assembly_version':  (Assembly, 'version'),
    'assembly_species':  (Assembly, 'species'),

    # Cell-level
    'cell_type':         (Cell,     'type'),
    'cell_label':        (Cell,     'label'),
}

class FilterSuggestionAPIView(APIView):
    """
    Filter Autocomplete API
    
    Provides autocomplete suggestions for filtering studies, assays, intervals, and assemblies.
    Returns a list of distinct values matching your search query.
    """
    
    @swagger_auto_schema(
        operation_summary="Get filter suggestions",
        operation_description="""
        Get autocomplete suggestions for a specific filter field.
        
        **Available filter fields:**
        - **Study filters:** study_name, study_external_id, study_repository, study_description, study_note, study_availability
        - **Assay filters:** assay_name, assay_external_id, assay_type, tissue, assay_target, assay_date, assay_kit, assay_cell_type, treatment, assay_description, assay_note, platform
        - **Interval filters:** interval_type, biotype
        - **Assembly filters:** assembly_name, assembly_version, assembly_species
        - **Cell filters:** cell_type (cell|spot), cell_label
        
        **Example:** 
        - Get tissue types containing "lung": `/api/filters/tissue/?q=lung&limit=10`
        - Get all assay types: `/api/filters/assay_type/?q=&limit=20`
        """,
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="Search query to filter results (case-insensitive partial match). Leave empty to get all values.",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Maximum number of suggestions to return (default: 10)",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response(
                description="List of matching values",
                examples={
                    "application/json": ["Lung", "Kidney", "Brain"]
                }
            ),
            400: openapi.Response(
                description="Invalid filter field",
                examples={
                    "application/json": {"error": "Invalid filter: invalid_field"}
                }
            )
        },
        tags=['Filters']
    )
    def get(self, request, field):
        # 1) Validate field
        entry = FIELD_MAP.get(field)
        if not entry:
            return Response(
                {'error': f'Invalid filter: {field}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Model, attr = entry
        
        # 2) Grab query params
        q     = request.query_params.get('q', '')
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10

        # 3) Build filter kwargs dynamically for the main search
        lookup = { f"{attr}__icontains": q } if q else {}

        # 4) Apply contextual filters based on other active filters
        qs = Model.objects.filter(**lookup)
        
        # Helper to parse boolean values
        def parse_bool(val):
            if val is None or val == '':
                return None
            v = str(val).lower()
            if v in ('1', 'true', 'yes', 'available', 't', 'on', 'all'):
                return True if v != 'all' else None
            if v in ('0', 'false', 'no', 'unavailable', 'f', 'off'):
                return False
            return None
        
        params = request.query_params
        
        # Determine which model we're querying to apply appropriate filters
        if Model == Study:
            # For study fields, filter by assay-level and deeper constraints
            assay_filters = {}
            if params.get('assay_name'):
                assay_filters['assays__name__icontains'] = params['assay_name']
            if params.get('assay_external_id'):
                assay_filters['assays__external_id__icontains'] = params['assay_external_id']
            if params.get('assay_type'):
                assay_filters['assays__type__icontains'] = params['assay_type']
            if params.get('tissue'):
                assay_filters['assays__tissue__icontains'] = params['tissue']
            if params.get('cell_type'):
                assay_filters['assays__cell_type__icontains'] = params['cell_type']
            if params.get('treatment'):
                assay_filters['assays__treatment__icontains'] = params['treatment']
            if params.get('platform'):
                assay_filters['assays__platform__icontains'] = params['platform']
            av_bool = parse_bool(params.get('assay_availability'))
            if av_bool is not None:
                assay_filters['assays__availability'] = av_bool
            
            if assay_filters:
                qs = qs.filter(**assay_filters).distinct()
            
            # Interval and assembly filters
            if params.get('interval_type'):
                qs = qs.filter(assays__signals__interval__type__icontains=params['interval_type']).distinct()
            if params.get('biotype'):
                qs = qs.filter(assays__signals__interval__biotype__icontains=params['biotype']).distinct()
            if params.get('assembly_name'):
                qs = qs.filter(assays__signals__interval__assembly__name__icontains=params['assembly_name']).distinct()
            if params.get('assembly_version'):
                qs = qs.filter(assays__signals__interval__assembly__version__icontains=params['assembly_version']).distinct()
                
        elif Model == Assay:
            # For assay fields, filter by study-level and deeper constraints
            if params.get('study_name'):
                qs = qs.filter(study__name__icontains=params['study_name'])
            if params.get('study_external_id'):
                qs = qs.filter(study__external_id__icontains=params['study_external_id'])
            sv_bool = parse_bool(params.get('study_availability'))
            if sv_bool is not None:
                qs = qs.filter(study__availability=sv_bool)
            
            # Other assay filters (excluding the current field being queried)
            if field != 'assay_name' and params.get('assay_name'):
                qs = qs.filter(name__icontains=params['assay_name'])
            if field != 'assay_external_id' and params.get('assay_external_id'):
                qs = qs.filter(external_id__icontains=params['assay_external_id'])
            if field != 'assay_type' and params.get('assay_type'):
                qs = qs.filter(type__icontains=params['assay_type'])
            if field != 'tissue' and params.get('tissue'):
                qs = qs.filter(tissue__icontains=params['tissue'])
            if field != 'cell_type' and params.get('cell_type'):
                qs = qs.filter(cell_type__icontains=params['cell_type'])
            if field != 'treatment' and params.get('treatment'):
                qs = qs.filter(treatment__icontains=params['treatment'])
            if field != 'platform' and params.get('platform'):
                qs = qs.filter(platform__icontains=params['platform'])
            
            # Interval and assembly filters
            if params.get('interval_type'):
                qs = qs.filter(signals__interval__type__icontains=params['interval_type']).distinct()
            if params.get('biotype'):
                qs = qs.filter(signals__interval__biotype__icontains=params['biotype']).distinct()
            if params.get('assembly_name'):
                qs = qs.filter(signals__interval__assembly__name__icontains=params['assembly_name']).distinct()
            if params.get('assembly_version'):
                qs = qs.filter(signals__interval__assembly__version__icontains=params['assembly_version']).distinct()
                
        elif Model == Interval:
            # For interval fields, filter by study/assay/assembly constraints
            if params.get('study_name'):
                qs = qs.filter(signals__assay__study__name__icontains=params['study_name']).distinct()
            if params.get('study_external_id'):
                qs = qs.filter(signals__assay__study__external_id__icontains=params['study_external_id']).distinct()
            
            if params.get('assay_name'):
                qs = qs.filter(signals__assay__name__icontains=params['assay_name']).distinct()
            if params.get('assay_type'):
                qs = qs.filter(signals__assay__type__icontains=params['assay_type']).distinct()
            if params.get('tissue'):
                qs = qs.filter(signals__assay__tissue__icontains=params['tissue']).distinct()
            if params.get('cell_type'):
                qs = qs.filter(signals__assay__cell_type__icontains=params['cell_type']).distinct()
            if params.get('treatment'):
                qs = qs.filter(signals__assay__treatment__icontains=params['treatment']).distinct()
            if params.get('platform'):
                qs = qs.filter(signals__assay__platform__icontains=params['platform']).distinct()
            
            if params.get('assembly_name'):
                qs = qs.filter(assembly__name__icontains=params['assembly_name'])
            if params.get('assembly_version'):
                qs = qs.filter(assembly__version__icontains=params['assembly_version'])
                
        elif Model == Assembly:
            # For assembly fields, filter by study/assay/interval constraints
            if params.get('study_name'):
                qs = qs.filter(intervals__signals__assay__study__name__icontains=params['study_name']).distinct()
            if params.get('study_external_id'):
                qs = qs.filter(intervals__signals__assay__study__external_id__icontains=params['study_external_id']).distinct()
            
            if params.get('assay_name'):
                qs = qs.filter(intervals__signals__assay__name__icontains=params['assay_name']).distinct()
            if params.get('assay_type'):
                qs = qs.filter(intervals__signals__assay__type__icontains=params['assay_type']).distinct()
            if params.get('tissue'):
                qs = qs.filter(intervals__signals__assay__tissue__icontains=params['tissue']).distinct()
            if params.get('cell_type'):
                qs = qs.filter(intervals__signals__assay__cell_type__icontains=params['cell_type']).distinct()
            
            if params.get('interval_type'):
                qs = qs.filter(intervals__type__icontains=params['interval_type']).distinct()
            if params.get('biotype'):
                qs = qs.filter(intervals__biotype__icontains=params['biotype']).distinct()
        
        elif Model == Cell:
            # For cell fields, filter by assay-level constraints
            if params.get('assay_name'):
                qs = qs.filter(assay__name__icontains=params['assay_name'])
            if params.get('assay_type'):
                qs = qs.filter(assay__type__icontains=params['assay_type'])
            if params.get('tissue'):
                qs = qs.filter(assay__tissue__icontains=params['tissue'])
            if params.get('assay_cell_type'):
                qs = qs.filter(assay__cell_type__icontains=params['assay_cell_type'])
            if params.get('treatment'):
                qs = qs.filter(assay__treatment__icontains=params['treatment'])
            if params.get('platform'):
                qs = qs.filter(assay__platform__icontains=params['platform'])
            
            # For cell_label, exclude nulls since we're looking for actual values
            if attr == 'label':
                qs = qs.exclude(label__isnull=True).exclude(label__exact='')

        # 5) Query the DB: distinct + order + limit
        results = (
            qs.order_by(attr)
              .values_list(attr, flat=True)
              .distinct()[:limit]
        )

        # 6) Return as simple JSON list
        return Response(list(results))
        return Response(debug_info)