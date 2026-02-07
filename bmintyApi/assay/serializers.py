from rest_framework import serializers
from .models import Assay


class AssaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Assay
        fields = ['id', 'external_id', 'type', 'target', 'name', 'tissue', 
                  'cell_type', 'treatment', 'date', 'platform', 'kit', 
                  'description', 'study', 'pipeline', 'availability', 'note',
                  'assemblies',
                  'interval_count', 'signal_nonzero', 'signal_zero', 'cell_total']
        read_only_fields = ['interval_count', 'signal_nonzero', 'signal_zero', 'cell_total']
        extra_kwargs = {
            'external_id': {'required': True},  
            'name': {'required': True},  
            'type': {'required': True},  
            'treatment': {'required': True},  
            'platform': {'required': True},  
            'kit': {'required': True},  
            'study': {'required': True},  
            'pipeline': {'required': True},  
            'note': {'required': False, 'allow_blank': True},
            'assemblies': {'required': False, 'allow_blank': True},
        }
