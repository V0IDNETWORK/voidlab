"""VOIDLAB root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/labs/", include("apps.labs.urls")),
    path("api/v1/leaderboard/", include("apps.leaderboard.urls")),
    path("api/v1/core/", include("apps.core.urls")),
    # OpenAPI schema + interactive docs
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
