from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("common.urls")),
    path("api/", include("novels.urls")),
    path("api/", include("chapters.urls")),
    path("api/", include("rankings.urls")),
    path("api/", include("users.urls")),
    path("api/", include("bookshelf.urls")),
    path("api/", include("comments.urls")),
    path("api/", include("video_generation.urls")),
]
