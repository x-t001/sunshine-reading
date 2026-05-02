from django.urls import path

from .views import ChapterDetailView, NovelChapterListView

app_name = "chapters"

urlpatterns = [
    path("novels/<int:novel_id>/chapters/", NovelChapterListView.as_view(), name="novel-chapter-list"),
    path("chapters/<int:id>/", ChapterDetailView.as_view(), name="chapter-detail"),
]
