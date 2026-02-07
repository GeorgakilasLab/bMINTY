from django.shortcuts import render
from django.db.models import Count, Q, Prefetch, F
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models       import Study
from .serializers  import (
    StudySerializer,
    StudyExploreSerializer,
    StudyAssaySerializer,
    AssayDetailSerializer,
    StudyListSerializer,
)
from bmintyApi.pagination import CustomPageNumberPagination
from assembly.models      import Assembly
from assay.models         import Assay
from interval.models      import Interval
from signals.models       import Signal, Cell

import logging
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


class StudyListCreateView(generics.ListCreateAPIView):
    """
    Study Management API
    
    **List Studies (GET):**
    Retrieve a paginated list of studies with optional filtering.
    
    **Study Filters:**
    - study_name: Filter by study name (partial match)
    - study_external_id: Filter by external ID like GEO accession (partial match)
    - study_repository: Filter by repository name (partial match)
    - study_description: Filter by description (partial match)
    - study_note: Filter by note (partial match)
    - study_availability: Filter by availability (true/false/1/0, default: true)
    
    **Assay Filters** (shows studies containing matching assays):
    - assay_name, assay_external_id: Filter by assay identifiers
    - assay_type: Filter by assay type (e.g., scRNA-seq, scATAC-seq)
    - tissue: Filter by tissue type (e.g., Lung, Kidney)
    - assay_target: Filter by target (partial match)
    - assay_date: Filter by date (partial match)
    - assay_kit: Filter by kit (partial match)
    - cell_type: Filter by cell type (e.g., T cells, Macrophages)
    - treatment: Filter by treatment condition
    - assay_description: Filter by description (partial match)
    - assay_note: Filter by note (partial match)
    - platform: Filter by sequencing platform (e.g., 10x Genomics)
    - assay_availability: Filter by assay availability (true/false, default: true)
    
    **Genomic Filters:**
    - interval_type: Filter by genomic interval type
    - biotype: Filter by gene biotype
    - assembly_name: Filter by genome assembly name
    - assembly_species: Filter by species
    
    **Pagination:**
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10)
    
    **Example:**
    /api/studies/?tissue=lung&assay_type=scRNA-seq&page=1&page_size=20
    
    ---
    
    **Create Study (POST):**
    Create a new study record.
    
    **Required fields:**
    - name: Study name
    - external_id: External repository ID (e.g., GSE123456)
    - external_repo: Repository name (e.g., GEO, ArrayExpress)
    
    **Optional fields:**
    - description: Study description
    - availability: Whether the study is publicly available (default: true)
    - note: Additional notes about the study
    """
    queryset         = Study.objects.all()
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        return StudyListSerializer if self.request.method == 'GET' else StudySerializer

    def get_queryset(self):
        qs     = super().get_queryset()
        params = self.request.query_params

        def parse_bool(val):
            if val is None:
                return None
            v = str(val).lower()
            if v in ('1', 'true', 'yes', 'available', 't', 'on'):
                return True
            if v in ('0', 'false', 'no', 'unavailable', 'f', 'off'):
                return False
            return None

        # — Study‐level filters (handles both single values and arrays) —
        study_names = _get_multi_value_param(params, 'study_name')
        if study_names:
            name_q = Q()
            for name in study_names:
                name_q |= Q(name__iexact=name)
            qs = qs.filter(name_q)
        
        study_external_ids = _get_multi_value_param(params, 'study_external_id')
        if study_external_ids:
            ext_id_q = Q()
            for ext_id in study_external_ids:
                ext_id_q |= Q(external_id__iexact=ext_id)
            qs = qs.filter(ext_id_q)
        
        study_repositories = _get_multi_value_param(params, 'study_repository')
        if study_repositories:
            repo_q = Q()
            for repo in study_repositories:
                repo_q |= Q(external_repo__icontains=repo)
            qs = qs.filter(repo_q)
        
        study_descriptions = _get_multi_value_param(params, 'study_description')
        if study_descriptions:
            desc_q = Q()
            for desc in study_descriptions:
                desc_q |= Q(description__icontains=desc)
            qs = qs.filter(desc_q)
        
        study_notes = _get_multi_value_param(params, 'study_note')
        if study_notes:
            note_q = Q()
            for note in study_notes:
                note_q |= Q(note__icontains=note)
            qs = qs.filter(note_q)
        
        # Study availability filter - default to True (only show available studies) when not specified
        if 'study_availability' in params or 'study_availability[]' in params:
            sval = parse_bool(params.get('study_availability') or params.get('study_availability[]'))
            if sval is not None:
                qs = qs.filter(availability=sval)
        else:
            # Default: only show available studies
            qs = qs.filter(availability=True)

        # — Assay‐level filters narrow which studies appear —
        ASSAY_LOOKUPS = {
          'assay_name':        'name__iexact',
          'assay_external_id': 'external_id__iexact',
          'assay_type':        'type__iexact',
          'tissue':            'tissue__iexact',
          'assay_target':      'target__icontains',
          'assay_date':        'date__icontains',
          'assay_kit':         'kit__icontains',
          'assay_cell_type':   'cell_type__iexact',  # Assay.cell_type metadata field
          'treatment':         'treatment__iexact',
          'assay_description': 'description__icontains',
          'assay_note':        'note__icontains',
          'platform':          'platform__iexact',
        }
        assay_q = Assay.objects.all()
        assay_filters_applied = False
        
        # Parse assay_availability filter early so we can use it for both filtering and annotation
        raw_av = params.get('assay_availability') or params.get('assay_availability[]')
        assay_availability_filter = parse_bool(raw_av)
        
        for p, lookup in ASSAY_LOOKUPS.items():
            values = _get_multi_value_param(params, p)
            if values:
                assay_filters_applied = True
                value_q = Q()
                for v in values:
                    value_q |= Q(**{lookup: v})
                assay_q = assay_q.filter(value_q)
        
        if assay_availability_filter is not None:
            assay_filters_applied = True
            assay_q = assay_q.filter(availability=assay_availability_filter)
        
        if assay_filters_applied:
            qs = qs.filter(assays__in=assay_q).distinct()

        # — Cell-level filters (Cell.type and Cell.label, NOT Assay.cell_type) —
        # Note: 'cell_type' in ASSAY_LOOKUPS above refers to Assay.cell_type (assay metadata)
        # For filtering by actual Cell objects, we need separate handling
        # OPTIMIZATION: Query cells first to get assay_ids, then filter studies by those assays
        
        # Support both 'cell_type' and legacy 'cell_kind' for Cell.type filtering
        cell_types = _get_multi_value_param(params, 'cell_type')
        if not cell_types:
            cell_types = _get_multi_value_param(params, 'cell_kind')
        
        if cell_types:
            # Normalize cell type values
            normalized_types = []
            for kind in cell_types:
                k = (kind or '').strip().lower()
                if k in ('single cell', 'single-cell', 'singlecell'):
                    k = 'cell'
                elif k == 'srt':
                    k = 'spot'
                normalized_types.append(k)
            
            # OPTIMIZED: Query Cell table directly to get assay_ids with matching cells
            # This avoids the expensive study→assay→cell join
            cell_type_q = Q()
            for k in normalized_types:
                cell_type_q |= Q(type__iexact=k)
            matching_assay_ids = Cell.objects.filter(cell_type_q).values_list('assay_id', flat=True).distinct()
            qs = qs.filter(assays__id__in=matching_assay_ids)
        
        cell_labels = _get_multi_value_param(params, 'cell_label')
        if cell_labels:
            # OPTIMIZED: Query Cell table directly to get assay_ids with matching labels
            label_q = Q()
            for lbl in cell_labels:
                label_q |= Q(label__iexact=lbl)
            matching_assay_ids = Cell.objects.filter(label_q).values_list('assay_id', flat=True).distinct()
            qs = qs.filter(assays__id__in=matching_assay_ids)

        # — Interval filters - OPTIMIZED: Get assay IDs from signals table first —
        # Instead of going study→assay→signal→interval (scanning millions of signals),
        # we query signal table directly to find assay_ids with matching intervals
        interval_types = _get_multi_value_param(params, 'interval_type')
        if interval_types:
            # Step 1: Get interval IDs matching the type filter
            type_q = Q()
            for itype in interval_types:
                type_q |= Q(type__iexact=itype)
            matching_interval_ids = list(Interval.objects.filter(type_q).values_list('id', flat=True))
            
            if matching_interval_ids:
                # Step 2: Get distinct assay_ids from signals that reference these intervals
                # This uses the idx_signal_interval_id index and is much faster
                # CHUNKING: SQLite has a limit of 999 SQL variables, so chunk the IDs
                chunk_size = 999
                all_assay_ids = set()
                for i in range(0, len(matching_interval_ids), chunk_size):
                    chunk = matching_interval_ids[i:i + chunk_size]
                    chunk_assay_ids = Signal.objects.filter(
                        interval_id__in=chunk
                    ).values_list('assay_id', flat=True).distinct()
                    all_assay_ids.update(chunk_assay_ids)
                
                if all_assay_ids:
                    qs = qs.filter(assays__id__in=all_assay_ids)
        
        biotypes = _get_multi_value_param(params, 'biotype')
        if biotypes:
            # Step 1: Get interval IDs matching the biotype filter
            biotype_q = Q()
            for bio in biotypes:
                biotype_q |= Q(biotype__iexact=bio)
            matching_interval_ids = list(Interval.objects.filter(biotype_q).values_list('id', flat=True))
            
            if matching_interval_ids:
                # Step 2: Get distinct assay_ids from signals that reference these intervals
                # CHUNKING: SQLite has a limit of 999 SQL variables, so chunk the IDs
                chunk_size = 999
                all_assay_ids = set()
                for i in range(0, len(matching_interval_ids), chunk_size):
                    chunk = matching_interval_ids[i:i + chunk_size]
                    chunk_assay_ids = Signal.objects.filter(
                        interval_id__in=chunk
                    ).values_list('assay_id', flat=True).distinct()
                    all_assay_ids.update(chunk_assay_ids)
                
                if all_assay_ids:
                    qs = qs.filter(assays__id__in=all_assay_ids)
        
        # Assembly filters - OPTIMIZED to use CSV assemblies field instead of expensive joins
        assembly_names = _get_multi_value_param(params, 'assembly_name')
        if assembly_names:
            # Look up assembly IDs matching the names
            assembly_ids = Assembly.objects.filter(
                name__in=assembly_names
            ).values_list('id', flat=True)
            if assembly_ids:
                # Build regex pattern to match any of these IDs in CSV field on Assay
                id_pattern = '|'.join([f'(^{id}$|^{id},|,{id},|,{id}$)' for id in assembly_ids])
                qs = qs.filter(assays__assemblies__regex=id_pattern)
        
        assembly_versions = _get_multi_value_param(params, 'assembly_version')
        if assembly_versions:
            # Look up assembly IDs matching the versions
            assembly_ids = Assembly.objects.filter(
                version__in=assembly_versions
            ).values_list('id', flat=True)
            if assembly_ids:
                id_pattern = '|'.join([f'(^{id}$|^{id},|,{id},|,{id}$)' for id in assembly_ids])
                qs = qs.filter(assays__assemblies__regex=id_pattern)
        
        assembly_species = _get_multi_value_param(params, 'assembly_species')
        if assembly_species:
            # Look up assembly IDs matching the species
            assembly_ids = Assembly.objects.filter(
                species__in=assembly_species
            ).values_list('id', flat=True)
            if assembly_ids:
                id_pattern = '|'.join([f'(^{id}$|^{id},|,{id},|,{id}$)' for id in assembly_ids])
                qs = qs.filter(assays__assemblies__regex=id_pattern)

        # — Finally annotate assay_count —
        # Respect the assay_availability filter to show counts matching what user is filtering for
        if assay_availability_filter is True:
            # When filtering for available assays, count only available ones
            qs = qs.annotate(
                assay_count=Count('assays', filter=Q(assays__availability=True), distinct=True)
            )
        elif assay_availability_filter is False:
            # When filtering for unavailable assays, count only unavailable ones
            qs = qs.annotate(
                assay_count=Count('assays', filter=Q(assays__availability=False), distinct=True)
            )
        else:
            # Default when no availability filter: count only available assays
            qs = qs.annotate(
                assay_count=Count('assays', filter=Q(assays__availability=True), distinct=True)
            )
        
        # Default ordering by study ID ascending
        return qs.order_by('id')
# class StudyListCreateView(generics.ListCreateAPIView):
#     # queryset = Study.objects.all()
#     def get_queryset(self):
#         """Optionally filter by availability"""
#         queryset = Study.objects.all()
#         availability = self.request.query_params.get('availability')

#         if availability is not None:
#             if availability.lower() == 'true':
#                 queryset = queryset.filter(availability=True)
#             elif availability.lower() == 'false':
#                 queryset = queryset.filter(availability=False)

#         return queryset    
#     serializer_class = StudySerializer
#     pagination_class = CustomPageNumberPagination


class StudyDetailUpdateView(generics.RetrieveUpdateAPIView):
    """
    Study Detail API - View and update study metadata
    
    - GET: Retrieve study details
    - PATCH/PUT: Update study metadata
    
    Note: Studies cannot be deleted through the API.
    """
    queryset = Study.objects.all()
    serializer_class = StudySerializer

class StudyChangeStatus(APIView):
    """
    PATCH /api/studies/{study_id}/status/
      payload: { "study_availability": true|false }
    """
    def patch(self, request, pk):
        # 1) Fetch or 404
        try:
            study = Study.objects.get(pk=pk)
        except Study.DoesNotExist:
            return Response(
                {'error': 'Study not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2) Validate payload
        if 'study_availability' not in request.data:
            return Response(
                {'error': "'availability' field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        new_avail = request.data['study_availability']

        # 3) Toggle logic & messages
        if study.availability and new_avail is False:
            study.availability = False
            study.save()
            return Response({'message': 'Study deactivated successfully.'})

        if not study.availability and new_avail is True:
            study.availability = True
            study.save()
            return Response({'message': 'Study activated successfully.'})

        if study.availability and new_avail is True:
            return Response({'message': 'Study is already activated.'})

        if not study.availability and new_avail is False:
            return Response({'message': 'Study is already deactivated.'})    
class StudyExploreAPIView(APIView):
    """
    GET /api/studies/{study_id}/explore/
    Now returns assemblies, assays, interval_counts, cell_count, peak_count
    """
    def get(self, request, pk):
        # 1) fetch or 404
        try:
            study = Study.objects.get(pk=pk)
        except Study.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 2) intervals via signals→assay→study
        intervals = Interval.objects.filter(
            signals__assays__study=study
        ).distinct()

        # 3) assemblies
        assembly_ids = intervals.values_list('assembly_id', flat=True).distinct()
        assemblies   = Assembly.objects.filter(assembly_id__in=assembly_ids,
                                               availability=True)

        # 4) assays for study
        assays = (
            Assay.objects
                .filter(availability=True)
                .annotate(study_count=Count('study', distinct=True))
                .filter(study=study)
        )

        # 5) interval_counts
        qs = intervals.values('type', 'biotype').annotate(count=Count('pk'))
        interval_counts = {}
        for row in qs:
            t = row['type']
            b = row['biotype'] or ''
            interval_counts.setdefault(t, {})[b] = row['count']

        # 6) cell_count & peak_count
        cell_count = Signal.objects.filter(
            assays__study=study
        ).values('cell').distinct().count()

        peak_count = Signal.objects.filter(
            assays__study=study
        ).count()

        payload = {
            'assemblies':      assemblies,
            'assays':          assays,
            'interval_counts': interval_counts,
            'cell_count':      cell_count,
            'peak_count':      peak_count,
        }
        serializer = StudyExploreSerializer(payload)
        return Response(serializer.data)
    
