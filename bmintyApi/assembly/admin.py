from django.contrib import admin
from .models import Assembly

@admin.register(Assembly)
class AssemblyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version', 'species')
    search_fields = ('name', 'version', 'species')
    list_filter = ('species',)
