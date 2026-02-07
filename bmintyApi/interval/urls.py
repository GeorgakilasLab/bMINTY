from rest_framework.routers import DefaultRouter
from .views import IntervalViewSet

router = DefaultRouter()
router.register(r'intervals', IntervalViewSet)     # Register intervals endpoint

urlpatterns = router.urls
