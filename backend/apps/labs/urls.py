from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, LabViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("", LabViewSet, basename="lab")

urlpatterns = router.urls
