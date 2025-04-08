from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/",
        include(
            [
                path("orchestrator/", include("apps.orchestrator.urls")),
                path("files/", include("apps.file_management.urls")),
            ]
        ),
    ),
]
