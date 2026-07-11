from django.urls import path

from .views import (
    AdminVideoProjectDetailView,
    AdminVideoProjectListView,
    VideoProjectDetailView,
    VideoProjectListCreateView,
)

app_name = "video_generation"

urlpatterns = [
    path("video-projects/", VideoProjectListCreateView.as_view(), name="video-project-list-create"),
    path("video-projects/<int:id>/", VideoProjectDetailView.as_view(), name="video-project-detail"),
    path("admin/video-projects/", AdminVideoProjectListView.as_view(), name="admin-video-project-list"),
    path("admin/video-projects/<int:id>/", AdminVideoProjectDetailView.as_view(), name="admin-video-project-detail"),
]
