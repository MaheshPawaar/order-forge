from rest_framework.routers import SimpleRouter

from apps.catalog.views import ProductViewSet, SKUViewSet

router = SimpleRouter(trailing_slash=False)
router.register("products", ProductViewSet, basename="product")
router.register("skus", SKUViewSet, basename="sku")

urlpatterns = router.urls
