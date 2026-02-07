# pipelines/serializers.py
from rest_framework import serializers
from .models import Pipeline

class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = [
            'id',
            'name',
            'description',
            'external_url',
        ]
        read_only_fields = ['id']
