# studies/urls.py
from django.urls import path
from .views import (
    StudyListCreateView,
    StudyDetailUpdateView,
    StudyChangeStatus,
    StudyExploreAPIView,
)

urlpatterns = [
    # Study endpoints
    # URL: /api/studies/
    path('studies/', StudyListCreateView.as_view(), name='study-list-create'),
    path('studies/<int:pk>/', StudyDetailUpdateView.as_view(), name='study-detail'),
    path('studies/<int:pk>/status/', StudyChangeStatus.as_view(), name='study-status'),
    path('studies/<int:pk>/explore/', StudyExploreAPIView.as_view(), name='study-explore'),
]
