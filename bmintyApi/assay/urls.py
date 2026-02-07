# assay/urls.py
from django.urls import path
from .views import (
    AssayListAllView,
    AssayDetailUpdateView,
    AssayChangeStatus,
    AssayDetailView,
    StudyAssaysView,
)

urlpatterns = [
    # Global assay endpoints (all assays across all studies)
    path('assays/', AssayListAllView.as_view(), name='assay-list-all'),
    path('assays/<int:pk>/', AssayDetailUpdateView.as_view(), name='assay-detail-update'),
    path('assays/<int:pk>/status/', AssayChangeStatus.as_view(), name='assay-status-change'),
    path('assays/<int:assay_id>/details/', AssayDetailView.as_view(), name='assay-details'),
    
    # Study-nested assay endpoints
    # URL: /api/studies/<study_id>/assays/
    path('studies/<int:study_id>/assays/', StudyAssaysView.as_view(), name='study-assay-list-create'),
    path('studies/<int:study_id>/assays/<int:pk>/', AssayDetailUpdateView.as_view(), name='study-assay-detail'),
    path('studies/<int:study_id>/assays/<int:pk>/status/', AssayChangeStatus.as_view(), name='study-assay-status'),
    path('studies/<int:study_id>/assays/<int:assay_id>/details/', AssayDetailView.as_view(), name='study-assay-details'),
]
