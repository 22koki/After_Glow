from django.urls import include, path
from django.http import JsonResponse

urlpatterns = [
    path("api/health/", lambda request: JsonResponse({"status": "ok", "app": "Afterglow"})),
    path("api/", include("afterglow.urls")),
]
