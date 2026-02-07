from rest_framework import generics
from .models      import Cell, Signal
from .serializers import CellSerializer, SignalSerializer

# --- Cell Endpoints ---

class CellListAPIView(generics.ListAPIView):
    queryset         = Cell.objects.all()
    serializer_class = CellSerializer

class CellDetailAPIView(generics.RetrieveAPIView):
    queryset         = Cell.objects.all()
    serializer_class = CellSerializer
    lookup_field     = 'cell_id'


# --- Signal Endpoints ---

class SignalListAPIView(generics.ListAPIView):
    queryset         = Signal.objects.all()
    serializer_class = SignalSerializer

class SignalDetailAPIView(generics.RetrieveAPIView):
    queryset         = Signal.objects.all()
    serializer_class = SignalSerializer
    lookup_field     = 'signal_id'
