from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Prefetch, F
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from bmintyApi.pagination import CustomPageNumberPagination
from .models import Assay, Study
from assembly.models import Assembly
from studies.models import Study
import logging
from .serializers import AssaySerializer
from studies.serializers import StudyAssaySerializer, AssayDetailSerializer
from rest_framework.exceptions import NotFound

# Set up logging
logger = logging.getLogger(__name__)

def _get_multi_value_param(query_params, param_name):
    """
    Get parameter values, handling both array format (param_name[]) and single values.
    Returns a list of values, filtering out empty or whitespace-only strings.
    """
    # Check for array format: param_name[]
    array_values = query_params.getlist(f'{param_name}[]')
    if array_values:
        # Filter out empty/whitespace strings
        return [v.strip() for v in array_values if v and v.strip()]
    
    # Check for single value
    single_value = query_params.get(param_name)
    if single_value and single_value.strip():
        return [single_value.strip()]
    
    return []

class AssayListCreateView(generics.ListCreateAPIView):
    """
    Assay Management API
    
    **List Assays (GET):**
    Retrieve all assays belonging to a specific study.
    
    URL Parameters:
    - study_id: The ID of the parent study (in URL path)
    
    Query Parameters:
    - assay_availability: Filter by availability (true/false, default: true)
    - assay_type: Filter by assay type (e.g., scRNA-seq, scATAC-seq)
    - tissue: Filter by tissue type
    - assay_target: Filter by target (partial match)
    - assay_date: Filter by date (partial match)
    - assay_kit: Filter by kit (partial match)
    - treatment: Filter by treatment
    - assay_description: Filter by description (partial match)
    - assay_note: Filter by note (partial match)
    
    Example: GET /api/studies/1/assays/?tissue=Lung (only shows available assays by default)
    
    ---
    
    **Create Assay (POST):**
    Create a new assay within a study.
    
    Required fields:
    - name: Assay name
    - external_id: External ID (e.g., GSM123456)
    - type: Assay type (scRNA-seq, scATAC-seq, Bulk RNA-seq, etc.)
    - date: Experiment date (MM/DD/YYYY)
    - platform: Sequencing platform (10x Genomics, Illumina, etc.)
    - pipeline_id: Analysis pipeline ID
    
    Optional fields:
    - target, tissue, cell_type, treatment, kit, description, availability, note
    
    Example: POST /api/studies/1/assays/ with JSON body
    """
    serializer_class = AssaySerializer

    @swagger_auto_schema(
        operation_summary="List assays for a study",
        operation_description="""
        Retrieve all assays belonging to a specific study.
        
        **URL Parameters:**
        - `study_id`: The ID of the parent study
        
        **Query Parameters:**
        - `assay_availability`: Filter by availability (true/false, default: true)
        - `assay_type`: Filter by assay type (e.g., scRNA-seq, scATAC-seq)
        - `tissue`: Filter by tissue type
        - `assay_target`: Filter by target (partial match)
        - `assay_date`: Filter by date (partial match)
        - `assay_kit`: Filter by kit (partial match)
        - `treatment`: Filter by treatment
        - `assay_description`: Filter by description (partial match)
        - `assay_note`: Filter by note (partial match)
        
        **Example:**
        `/api/studies/1/assays/?tissue=Lung` (only shows available assays by default)
        """,
        manual_parameters=[
            openapi.Parameter(
                'assay_availability',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by availability: true or false"
            ),
            openapi.Parameter(
                'assay_type',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by assay type"
            ),
            openapi.Parameter(
                'tissue',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by tissue type"
            ),
            openapi.Parameter(
                'assay_target',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by target (partial match)"
            ),
            openapi.Parameter(
                'assay_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by date (partial match)"
            ),
            openapi.Parameter(
                'assay_kit',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by kit (partial match)"
            ),
            openapi.Parameter(
                'treatment',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by treatment"
            ),
            openapi.Parameter(
                'assay_description',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by description (partial match)"
            ),
            openapi.Parameter(
                'assay_note',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filter by note (partial match)"
            ),
        ],
        responses={
            200: AssaySerializer(many=True),
            404: "Study not found"
        },
        tags=['Assays']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a new assay",
        operation_description="""
        Create a new assay within a study.
        
        **Required fields:**
        - `name`: Assay name
        - `external_id`: External ID (e.g., GSM123456)
        - `type`: Assay type (e.g., scRNA-seq, scATAC-seq, Bulk RNA-seq)
        - `date`: Experiment date (format: MM/DD/YYYY)
        - `platform`: Sequencing platform (e.g., 10x Genomics, Illumina)
        - `pipeline_id`: Analysis pipeline ID
        
        **Optional fields:**
        - `target`: Experimental target
        - `tissue`: Tissue type
        - `cell_type`: Cell type
        - `treatment`: Treatment condition
        - `kit`: Library prep kit
        - `description`: Assay description
        - `availability`: Publicly available (default: true)
        - `note`: Additional notes
        """,
        request_body=AssaySerializer,
        responses={
            201: AssaySerializer,
            400: "Validation error",
            404: "Study not found"
        },
        tags=['Assays']
    )

    def get_queryset(self):
        """Filter by study_id from URL and optionally by other assay filters"""
        study_id = self.kwargs.get('study_id')  # ✅ from URL, not query params
        queryset = Assay.objects.filter(study_id=study_id)
        
        params = self.request.query_params

        # Filter by availability - default to showing only available assays
        availability = params.get('assay_availability')
        if availability is not None:
            if availability.lower() == 'true':
                queryset = queryset.filter(availability=True)
            elif availability.lower() == 'false':
                queryset = queryset.filter(availability=False)
        else:
            # Default: only show available assays
            queryset = queryset.filter(availability=True)
        
        # Additional assay filters
        assay_types = _get_multi_value_param(params, 'assay_type')
        if assay_types:
            type_q = Q()
            for atype in assay_types:
                type_q |= Q(type__iexact=atype)
            queryset = queryset.filter(type_q)
        
        tissues = _get_multi_value_param(params, 'tissue')
        if tissues:
            tissue_q = Q()
            for tissue in tissues:
                tissue_q |= Q(tissue__iexact=tissue)
            queryset = queryset.filter(tissue_q)
        
        targets = _get_multi_value_param(params, 'assay_target')
        if targets:
            target_q = Q()
            for target in targets:
                target_q |= Q(target__icontains=target)
            queryset = queryset.filter(target_q)
        
        dates = _get_multi_value_param(params, 'assay_date')
        if dates:
            date_q = Q()
            for date in dates:
                date_q |= Q(date__icontains=date)
            queryset = queryset.filter(date_q)
        
        kits = _get_multi_value_param(params, 'assay_kit')
        if kits:
            kit_q = Q()
            for kit in kits:
                kit_q |= Q(kit__icontains=kit)
            queryset = queryset.filter(kit_q)
        
        treatments = _get_multi_value_param(params, 'treatment')
        if treatments:
            treatment_q = Q()
            for treatment in treatments:
                treatment_q |= Q(treatment__iexact=treatment)
            queryset = queryset.filter(treatment_q)
        
        descriptions = _get_multi_value_param(params, 'assay_description')
        if descriptions:
            desc_q = Q()
            for desc in descriptions:
                desc_q |= Q(description__icontains=desc)
            queryset = queryset.filter(desc_q)
        
        notes = _get_multi_value_param(params, 'assay_note')
        if notes:
            note_q = Q()
            for note in notes:
                note_q |= Q(note__icontains=note)
            queryset = queryset.filter(note_q)

        return queryset.order_by('id')

    
    pagination_class = CustomPageNumberPagination

    def create(self, request, *args, **kwargs):
        """Ensure assay is linked to the correct study"""
        study_id = kwargs.get('study_id')
        study = get_object_or_404(Study, pk=study_id)

        # Debugging print statement to inspect incoming data
        print("Incoming request data:", request.data)

        request.data['study'] = study.pk  # Using study.pk to link the ForeignKey

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(study=study)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Validation errors:", serializer.errors)  # Debug print for validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class AssayDetailUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Assay.objects.all()
    serializer_class = AssaySerializer

    def get_queryset(self):
        """
        If a nested route supplies study_id, filter by it.
        Otherwise (flat route), just use all assays.
        """
        qs = Assay.objects.all()
        study_id = self.kwargs.get('study_id')
        if study_id is not None:
            qs = qs.filter(study_id=study_id)
        return qs

    def get_object(self):
        study_id = self.kwargs.get('study_id')
        pk = self.kwargs.get('pk')
        logger.debug(f"Retrieving Assay pk={pk} (study_id={study_id})")
        return get_object_or_404(self.get_queryset(), pk=pk)

    # PATCH works out of the box as partial update; leave perform_update if you like the logs
    def perform_update(self, serializer):
        assay = serializer.instance
        logger.debug(f"Updating Assay {assay.id} with data: {serializer.validated_data}")
        serializer.save()
        logger.info(f"Assay {assay.id} updated")

class AssayChangeStatus(generics.GenericAPIView):
    serializer_class = AssaySerializer

    def get_queryset(self):
        """Filter assays by study_id and id from the URL"""
        study_id = self.kwargs.get('study_id')
        id = self.kwargs.get('pk')
        logger.debug(f"Fetching assays with study_id={study_id} and id={id}")
        return Assay.objects.filter(study_id=study_id, pk=id)

    def get_object(self):
        """Override to ensure correct retrieval based on study_id and pk"""
        queryset = self.get_queryset()
        logger.debug(f"Queryset for get_object: {queryset}")
        obj = get_object_or_404(queryset)
        logger.debug(f"Assay retrieved: {obj}")
        return obj

    def patch(self, request, study_id, pk, *args, **kwargs):
        """Toggle the availability of an assay"""
        logger.debug(f"Received PATCH request for study_id={study_id}, id={pk}, data={request.data}")
        assay = self.get_object()

        raw = request.data.get('assay_availability')
        if raw is None:
            logger.error("No 'assay_availability' parameter in request data")
            return Response({"error": "'assay_availability' parameter is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        availability = raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "yes", "on")

        if assay.availability == availability:
            logger.info(f"Assay already {'activated' if availability else 'deactivated'}")
            return Response(
                {"message": f"Assay is already {'activated' if availability else 'deactivated'}."},
                status=status.HTTP_200_OK
            )

        assay.availability = availability
        assay.save()
        logger.info(f"Assay {'activated' if availability else 'deactivated'} successfully: {assay}")

        return Response(
            {"message": f"Assay {'activated' if availability else 'deactivated'} successfully."},
            status=status.HTTP_200_OK
        )

        

class AssayListAllView(generics.ListAPIView):
    serializer_class = AssaySerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Assay.objects.all()

        def parse_bool(val):
            if val is None:
                return None
            v = str(val).lower()
            if v in ('1', 'true', 'yes', 'available', 't', 'on'):
                return True
            if v in ('0', 'false', 'no', 'unavailable', 'f', 'off'):
                return False
            return None

        # Filter by study_id if provided as query parameter
        study_id = self.request.query_params.get('study_id')
        if study_id is not None:
            queryset = queryset.filter(study_id=study_id)

        # Filter by pipeline if provided as query parameter
        pipeline_id = self.request.query_params.get('pipeline')
        if pipeline_id is not None:
            try:
                # Convert to int for filtering
                pid = int(pipeline_id)
                queryset = queryset.filter(pipeline_id=pid)
            except (ValueError, TypeError):
                pass  # Invalid pipeline_id, ignore it

        # Filter by availability if provided
        availability = self.request.query_params.get('assay_availability')
        av_bool = parse_bool(availability)
        if av_bool is not None:
            queryset = queryset.filter(availability=av_bool)
        
        return queryset.order_by('id')


class StudyAssaysView(generics.ListCreateAPIView):
    serializer_class = StudyAssaySerializer
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        # Use AssaySerializer for POST requests to properly handle creation
        if self.request.method == 'POST':
            return AssaySerializer
        return StudyAssaySerializer

    def get_queryset(self):
        study_id = self.kwargs['study_id']
        params   = self.request.query_params

        # base: all assays for this study; we'll apply availability below
        qs = Assay.objects.filter(study_id=study_id)

        def parse_bool(val):
            if val is None:
                return None
            v = str(val).lower()
            if v in ('1', 'true', 'yes', 'available', 't', 'on'):
                return True
            if v in ('0', 'false', 'no', 'unavailable', 'f', 'off'):
                return False
            return None

        # assay‐level text & availability filters - NOW SUPPORTS MULTI-VALUE ARRAYS
        ASSAY_LOOKUPS = {
            'assay_name':        'name__iexact',
            'assay_external_id': 'external_id__iexact',
            'assay_type':        'type__iexact',
            'tissue':            'tissue__iexact',
            'cell_type':         'cell_type__iexact',
            'treatment':         'treatment__iexact',
            'platform':          'platform__iexact',
        }
        for p, lookup in ASSAY_LOOKUPS.items():
            # Handle multi-value parameters (supports both single and array format)
            values = _get_multi_value_param(params, p)
            if values:
                # Build OR query for multiple values
                field_q = Q()
                for val in values:
                    field_q |= Q(**{lookup: val})
                qs = qs.filter(field_q)

        raw_av = params.get('assay_availability') or params.get('assay_availability[]')
        av_bool = parse_bool(raw_av)
        if av_bool is not None:
            qs = qs.filter(availability=av_bool)
        else:
            # Default: only show available assays
            qs = qs.filter(availability=True)

        # interval & assembly filters on assays
        if params.get('interval_type'):
            qs = qs.filter(
                signals__interval__type__iexact=params['interval_type']
            )
        if params.get('biotype'):
            qs = qs.filter(
                signals__interval__biotype__iexact=params['biotype']
            )
        
        # Assembly filters - OPTIMIZED to use CSV assemblies field instead of expensive joins
        assembly_names = _get_multi_value_param(params, 'assembly_name')
        if assembly_names:
            # Look up assembly IDs matching the names
            assembly_ids = Assembly.objects.filter(
                name__in=assembly_names
            ).values_list('id', flat=True)
            if assembly_ids:
                # Build regex pattern to match any of these IDs in CSV field
                # Pattern matches: start of string, after comma, or surrounded by commas
                id_pattern = '|'.join([f'(^{id}$|^{id},|,{id},|,{id}$)' for id in assembly_ids])
                qs = qs.filter(assemblies__regex=id_pattern)
        
        assembly_versions = _get_multi_value_param(params, 'assembly_version')
        if assembly_versions:
            # Look up assembly IDs matching the versions
            assembly_ids = Assembly.objects.filter(
                version__in=assembly_versions
            ).values_list('id', flat=True)
            if assembly_ids:
                id_pattern = '|'.join([f'(^{id}$|^{id},|,{id},|,{id}$)' for id in assembly_ids])
                qs = qs.filter(assemblies__regex=id_pattern)
        
        assembly_species = _get_multi_value_param(params, 'assembly_species')
        if assembly_species:
            # Look up assembly IDs matching the species
            assembly_ids = Assembly.objects.filter(
                species__in=assembly_species
            ).values_list('id', flat=True)
            if assembly_ids:
                id_pattern = '|'.join([f'(^{id}$|^{id},|,{id},|,{id}$)' for id in assembly_ids])
                qs = qs.filter(assemblies__regex=id_pattern)
        # annotate counts using stored assay fields to reduce DB load
        from django.db.models import F
        from django.db.models.functions import Coalesce
        return qs.annotate(
            study_count=Count('study', distinct=True),
            # Use signal_nonzero for peak count
            peak_count=Coalesce(F('signal_nonzero'), 0),
        ).order_by('id')

    def create(self, request, *args, **kwargs):
        """Handle POST to create a new assay for this study"""
        study_id = kwargs.get('study_id')
        study = get_object_or_404(Study, pk=study_id)
        
        # Add study to the request data
        data = request.data.copy()
        data['study'] = study.pk
        
        serializer = AssaySerializer(data=data)
        if serializer.is_valid():
            serializer.save(study=study)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AssayDetailView(APIView):
    """
    GET /api/studies/assays/{assay_id}/details/
    Returns the assembly, pipeline, and per‐interval breakdown.
    """
    def get(self, request, study_id, assay_id):
        # 1) fetch or 404
        try:
            assay = Assay.objects.get(pk=assay_id)
        except Assay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Avoid heavy DISTINCT queries; use stored metrics only
        pipeline_name = getattr(assay.pipeline, 'name', None)
        pipeline_description = getattr(assay.pipeline, 'description', None)
        pipeline_external_url = getattr(assay.pipeline, 'external_url', None)
        total_intervals = assay.interval_count or 0

        # Prefer CSV of assembly IDs stored on assay; resolve primary assembly name via first ID
        assemblies_field = assay.assemblies or ""
        id_tokens = [tok.strip() for tok in str(assemblies_field).split(',') if tok and tok.strip()]
        primary_assembly_name = None
        if id_tokens:
            first_tok = id_tokens[0]
            try:
                asm_obj = Assembly.objects.filter(id=int(first_tok)).first()
            except ValueError:
                asm_obj = None
            primary_assembly_name = getattr(asm_obj, 'name', None)

        payload = {
            'assembly_name':          primary_assembly_name,
            # Pass CSV of IDs; AssayDetailSerializer.get_assemblies will resolve to full objects
            'assemblies':             assemblies_field,
            'pipeline_name':          pipeline_name,
            'pipeline_description':   pipeline_description,
            'pipeline_external_url':   pipeline_external_url,
            'total_intervals':        total_intervals,
            'signal_zero':            assay.signal_zero or 0,
            'signal_nonzero':         assay.signal_nonzero or 0,
            'cell_total':             assay.cell_total or 0,
            'note':                   getattr(assay, 'note', None),
        }
        serializer = AssayDetailSerializer(payload)
        return Response(serializer.data)
    