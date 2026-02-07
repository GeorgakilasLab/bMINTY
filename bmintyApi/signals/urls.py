from django.urls import path
from .views import (
    CellListAPIView, CellDetailAPIView,
    SignalListAPIView, SignalDetailAPIView,
)

urlpatterns = [
    # Cells
    path('cells/',           CellListAPIView.as_view(), name='cell-list'),
    path('cells/<int:cell_id>/', CellDetailAPIView.as_view(), name='cell-detail'),

    # Signals
    path('signals/',             SignalListAPIView.as_view(), name='signal-list'),
    path('signals/<int:signal_id>/', SignalDetailAPIView.as_view(), name='signal-detail'),
]
