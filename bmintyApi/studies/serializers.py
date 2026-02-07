from rest_framework import serializers
from .models import Study
from assembly.models import Assembly
from assay.models    import Assay
from assay.serializers import AssaySerializer

    
class AssayWithStudyCountSerializer(AssaySerializer):
    study_count = serializers.IntegerField(read_only=True)

    class Meta(AssaySerializer.Meta):
        # inherit all the same fields as your AssaySerializer…
        fields = AssaySerializer.Meta.fields + ['study_count']

class StudySerializer(serializers.ModelSerializer):
    assays = AssayWithStudyCountSerializer(
         source='filtered_assays',
         many=True,
         read_only=True
     )

    class Meta:
        model  = Study
        fields = ['id','external_id','external_repo','name','description','availability','assays', 'note']
        read_only_fields = ['id']
        extra_kwargs = {
            'availability': {'required': False},     # default True will apply
            'description':  {'required': False, 'allow_blank': True},
            'external_repo': {'required': False, 'allow_blank': True},
        }
class AssemblySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Assembly
        fields = ['id', 'name', 'version', 'species']

class AssaySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Assay
        fields = ['id', 'name', 'external_id', 'platform']

class StudyExploreSerializer(serializers.Serializer):
    assemblies      = AssemblySerializer(many=True)
    assays          = AssayWithStudyCountSerializer(many=True)
    interval_counts = serializers.DictField(
        child=serializers.DictField(child=serializers.IntegerField())
    )
    cell_count      = serializers.IntegerField()
    peak_count      = serializers.IntegerField()
    


class StudyAssaySerializer(serializers.ModelSerializer):
    # intervals with signal > 0
    peak_count             = serializers.IntegerField(read_only=True)
    # stored counters on Assay
    signal_nonzero         = serializers.IntegerField(read_only=True)
    signal_zero            = serializers.IntegerField(read_only=True)
    cell_total             = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Assay
        fields = [
            'id', 'name', 'external_id', 'type', 'tissue', 'cell_type', 
            'treatment', 'platform', 'availability', 'note', 'assemblies',
            'kit', 'target', 'date', 'description', 'study',
            'peak_count',
            # prefer signal_* for display in Explore list
            'signal_nonzero', 'signal_zero', 'cell_total',
        ]
        read_only_fields = ['peak_count', 'signal_nonzero', 'signal_zero', 'cell_total', 'id']

# 2️⃣ Serializer for the assay’s detailed info
class AssayDetailSerializer(serializers.Serializer):
    assembly_name          = serializers.CharField(allow_null=True, required=False, default=None)
    assemblies             = serializers.SerializerMethodField()
    pipeline_name          = serializers.CharField(allow_null=True, required=False, default=None)
    pipeline_description   = serializers.CharField(allow_null=True, required=False, default=None, allow_blank=True)
    pipeline_external_url   = serializers.CharField(allow_null=True, required=False, default=None)
    total_intervals        = serializers.IntegerField()
    # New counters
    signal_zero            = serializers.IntegerField(required=False, default=0)
    signal_nonzero         = serializers.IntegerField(required=False, default=0)
    cell_total             = serializers.IntegerField(required=False, default=0)
    note                   = serializers.CharField(allow_blank=True, allow_null=True, required=False, default=None)

    def get_assemblies(self, obj):
        """
        Build assemblies list from `obj.assemblies` which may contain a CSV of
        assembly IDs (strings). Prefer IDs stored on the assay to avoid duplicates.
        When provided a list, filter it by the ID set to ensure only expected assemblies.
        """
        # Extract CSV of IDs from obj
        csv_val = None
        if hasattr(obj, 'assemblies'):
            csv_val = obj.assemblies
        elif isinstance(obj, dict):
            csv_val = obj.get('assemblies')

        ids = [s.strip() for s in str(csv_val).split(',') if csv_val and s and str(s).strip()]
        provided = None
        if isinstance(obj, dict):
            provided = obj.get('assemblies') if isinstance(obj.get('assemblies'), list) else None
        elif hasattr(obj, 'assemblies') and isinstance(getattr(obj, 'assemblies'), list):
            provided = getattr(obj, 'assemblies')

        # If IDs exist, prefer them; filter any provided list by IDs
        if ids:
            try:
                qs = Assembly.objects.filter(id__in=ids)
                serialized = AssemblySerializer(qs, many=True).data
                if provided:
                    # Filter provided list to match IDs to avoid duplicates
                    id_set = set(int(i) if str(i).isdigit() else i for i in ids)
                    filtered = [a for a in provided if a.get('id') in id_set]
                    # If filtering yields results, use them; otherwise use serialized from DB
                    return filtered if filtered else serialized
                return serialized
            except Exception:
                return [{ 'id': int(i) if str(i).isdigit() else i, 'name': None, 'version': None, 'species': None } for i in ids]

        # No IDs → return provided list if any, else empty
        return provided or []

class AssemblySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Assembly
        fields = ['id', 'name', 'version', 'species']
        
        

class StudyListSerializer(serializers.ModelSerializer):
    assay_count = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Study
        fields = ['id', 'external_id', 'external_repo', 'name', 'description', 'assay_count', 'availability', 'note']