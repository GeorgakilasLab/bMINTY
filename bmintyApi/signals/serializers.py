from rest_framework import serializers
from .models import Cell, Signal


class SafeIntegerField(serializers.IntegerField):
    def to_representation(self, value):
        if value in (None, '', 'NULL'):
            return None
        try:
            return super().to_representation(value)
        except (TypeError, ValueError):
            return None


class CellSerializer(serializers.ModelSerializer):
    x_coordinate = SafeIntegerField(allow_null=True, required=False)
    y_coordinate = SafeIntegerField(allow_null=True, required=False)
    z_coordinate = SafeIntegerField(allow_null=True, required=False)
    class Meta:
        model = Cell
        fields = [
            'id',
            'name',
            'type',
            'label',
            'x_coordinate',
            'y_coordinate',
            'z_coordinate',
        ]
        read_only_fields = ['id']

class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = [
            'id',
            'signal',
            'p_value',
            'padj_value',
            'assay',
            'interval',
            'cell',
        ]
        read_only_fields = ['id']
