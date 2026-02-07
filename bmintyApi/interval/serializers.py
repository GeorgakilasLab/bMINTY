from rest_framework import serializers
from .models import Interval


class NullableIntegerField(serializers.IntegerField):
    def to_representation(self, value):
        if value in (None, '', 'NULL'):
            return None
        return super().to_representation(value)


class IntervalSerializer(serializers.ModelSerializer):
    # expose the raw FK column:
    assembly_id = NullableIntegerField(allow_null=True, required=False, read_only=True)
    start = NullableIntegerField(allow_null=True, required=False)
    end = NullableIntegerField(allow_null=True, required=False)
    summit = NullableIntegerField(allow_null=True, required=False)

    class Meta:
        model = Interval
        fields = [
            'id',
            'external_id',
            'parental_id',
            'name',
            'type',
            'biotype',
            'chromosome',
            'start',
            'end',
            'strand',
            'summit',
            'assembly_id',   # ← add it here
        ]
    
    def validate(self, data):
        # Define mandatory fields (apart from the auto-increment PK)
        mandatory_fields = ['external_id', 'type', 'chromosome', 'start', 'end', 'strand', 'assembly_id']
        for field in mandatory_fields:
            if field not in data or data[field] in [None, '']:
                raise serializers.ValidationError({field: "This field is required."})
        return data
