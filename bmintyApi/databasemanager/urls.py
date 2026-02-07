# databasemanager/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Database import/export endpoints
    path('database/import/sqlite/', views.import_sqlite, name='import_sqlite'),
    path('database/import/table/<str:table>/', views.import_table, name='import_table'),
    path('database/import/bulk/', views.import_bulk_data, name='import_bulk_data'),
    path('database/import/bulk/<str:job_id>/status/', views.import_bulk_data_status, name='import_bulk_data_status'),
    
    path('database/export/sqlite/', views.export_sqlite, name='export_sqlite'),
    path('database/export/sqlite/filtered/', views.export_filtered_sqlite, name='export_filtered_sqlite'),
    # Alias for frontend compatibility
    path('export_filtered_sqlite/', views.export_filtered_sqlite, name='export_filtered_sqlite_alias'),
]
