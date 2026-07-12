from django.urls import path

from .views import (
    AdminVideoProjectDetailView,
    AdminVideoProjectListView,
    VideoProjectAiStoryboardView,
    VideoProjectChapterCreateView,
    VideoProjectCapabilitiesView,
    VideoProjectDetailView,
    VideoProjectListCreateView,
    VideoProjectStoryboardView,
    VideoProjectStoryboardJobView,
    VideoProjectLatestStoryboardJobView,
    VideoGenerationJobDetailView,
    VideoGenerationJobRetryView,
    VideoSceneDetailView,
    VideoStoryDraftView,
    VideoSourceChapterListView,
)

app_name = "video_generation"

urlpatterns = [
    path("video-source-chapters/", VideoSourceChapterListView.as_view(), name="video-source-chapter-list"),
    path("video-projects/capabilities/", VideoProjectCapabilitiesView.as_view(), name="video-project-capabilities"),
    path("video-projects/story-draft/", VideoStoryDraftView.as_view(), name="video-story-draft"),
    path("video-projects/from-chapter/", VideoProjectChapterCreateView.as_view(), name="video-project-chapter-create"),
    path("video-projects/", VideoProjectListCreateView.as_view(), name="video-project-list-create"),
    path("video-projects/<int:id>/storyboard/", VideoProjectStoryboardView.as_view(), name="video-project-storyboard"),
    path("video-projects/<int:id>/storyboard/ai/", VideoProjectAiStoryboardView.as_view(), name="video-project-ai-storyboard"),
    path("video-projects/<int:id>/storyboard/jobs/", VideoProjectStoryboardJobView.as_view(), name="video-project-storyboard-job-create"),
    path("video-projects/<int:id>/storyboard/jobs/latest/", VideoProjectLatestStoryboardJobView.as_view(), name="video-project-storyboard-job-latest"),
    path("video-projects/<int:id>/scenes/<int:scene_id>/", VideoSceneDetailView.as_view(), name="video-scene-detail"),
    path("video-projects/<int:id>/", VideoProjectDetailView.as_view(), name="video-project-detail"),
    path("video-generation-jobs/<int:id>/", VideoGenerationJobDetailView.as_view(), name="video-generation-job-detail"),
    path("video-generation-jobs/<int:id>/retry/", VideoGenerationJobRetryView.as_view(), name="video-generation-job-retry"),
    path("admin/video-projects/", AdminVideoProjectListView.as_view(), name="admin-video-project-list"),
    path("admin/video-projects/<int:id>/", AdminVideoProjectDetailView.as_view(), name="admin-video-project-detail"),
]
