from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from .views import home  # or wherever your home view is defined
from .views import FilterSuggestionAPIView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="BMinty API",
      default_version='v1',
      description="API documentation for BMinty project",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@bminty.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Studies with nested assays
    path('api/', include('studies.urls')),
    path('api/', include('assay.urls')),
    
    # Resource endpoints
    path('api/', include('databasemanager.urls')),
    path('api/', include('assembly.urls')),
    path('api/', include('interval.urls')),
    path('api/', include('pipelines.urls')),
    path('api/', include('signals.urls')),
    
    # Utility endpoints
    path('', home, name='home'),
    path('api/filters/<str:field>/', FilterSuggestionAPIView.as_view(), name='filter-suggestions'),
    
    # Swagger documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
