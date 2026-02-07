# pipelines/urls.py
from django.urls import path
from .views import PipelineListCreateAPIView, PipelineDetailAPIView

urlpatterns = [
    path('pipelines/', PipelineListCreateAPIView.as_view(), name='pipeline-list'),
    path('pipelines/<int:pipeline_id>/', PipelineDetailAPIView.as_view(), name='pipeline-detail'),
]
