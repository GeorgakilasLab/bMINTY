from rest_framework.routers import DefaultRouter
from .views import AssemblyViewSet

router = DefaultRouter()
router.register(r'assemblies', AssemblyViewSet)  # This MUST be present

urlpatterns = router.urls
