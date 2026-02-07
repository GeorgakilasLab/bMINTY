from django.test import TestCase
from django.db.models import Count
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response

from .models         import Study
from .serializers    import StudySerializer, StudyExploreSerializer
from assay.models    import Assay
from interval.models import Interval
from signals.models  import Signal
from assembly.models import Assembly


class StudyListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/studies/    → list all studies (no pagination)
    POST /api/studies/    → create a new study
    """
    queryset         = Study.objects.all()
    serializer_class = StudySerializer
    pagination_class = None   # tests expect response.data to be a raw list


class StudyDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/studies/{study_id}/    → retrieve one study
    PUT    /api/studies/{study_id}/    → update that study
    DELETE /api/studies/{study_id}/    → delete
    """
    queryset         = Study.objects.all()
    serializer_class = StudySerializer
    lookup_field     = 'study_id'      # use URL kwarg `study_id` instead of `pk`


class StudyChangeStatus(APIView):
    """
    PATCH /api/studies/{study_id}/status/
      payload: { "availability": true|false }
    """

    def patch(self, request, study_id):
        # 1) Fetch or 404
        try:
            study = Study.objects.get(pk=study_id)
        except Study.DoesNotExist:
            return Response({'error': 'Study not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        # 2) Validate payload
        if 'availability' not in request.data:
            return Response({'error': "'availability' field is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        new_avail = request.data['availability']

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
    Returns JSON with:
      - assemblies: list of AssemblySerializer
      - interval_counts: { type: { biotype: count, … }, … }
      - cell_count: int
      - peak_count: int
    """
    def get(self, request, study_id):
        # 1) Fetch or 404
        try:
            study = Study.objects.get(pk=study_id)
        except Study.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 2) All intervals tied via signals → assays → this study
        intervals = Interval.objects.filter(
            signals__assay__study=study
        ).distinct()

        # 3) Assemblies for those intervals
        assembly_ids = intervals.values_list('assembly_id', flat=True).distinct()
        assemblies   = Assembly.objects.filter(
            assembly_id__in=assembly_ids,
            availability=True
        )

        # 4) Count intervals by type & biotype
        qs = intervals.values('type', 'biotype').annotate(count=Count('pk'))
        interval_counts = {}
        for row in qs:
            t = row['type']
            b = row['biotype'] or ''
            interval_counts.setdefault(t, {})[b] = row['count']

        # 5) Distinct cells via signals
        cell_count = Signal.objects.filter(
            assay__study=study
        ).values('cell').distinct().count()

        # 6) Total signals = peak count
        peak_count = Signal.objects.filter(
            assay__study=study
        ).count()

        payload = {
            'assemblies':      assemblies,
            'interval_counts': interval_counts,
            'cell_count':      cell_count,
            'peak_count':      peak_count,
        }
        serializer = StudyExploreSerializer(payload)
        return Response(serializer.data)
