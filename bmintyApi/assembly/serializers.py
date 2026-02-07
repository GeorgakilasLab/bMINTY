from rest_framework import serializers
from .models import Assembly

class AssemblySerializer(serializers.ModelSerializer):
    class Meta:
        model = Assembly
        fields = '__all__'
