from django.urls import path

from .views import (
    AuthorChapterDetailView,
    AuthorChapterSubmitView,
    AuthorNovelChapterListCreateView,
    ChapterDetailView,
    NovelChapterListView,
)

app_name = "chapters"

urlpatterns = [
    path("novels/<int:novel_id>/chapters/", NovelChapterListView.as_view(), name="novel-chapter-list"),
    path("chapters/<int:id>/", ChapterDetailView.as_view(), name="chapter-detail"),
    path(
        "author/novels/<int:novel_id>/chapters/",
        AuthorNovelChapterListCreateView.as_view(),
        name="author-novel-chapter-list-create",
    ),
    path("author/chapters/<int:id>/", AuthorChapterDetailView.as_view(), name="author-chapter-detail"),
    path("author/chapters/<int:id>/submit/", AuthorChapterSubmitView.as_view(), name="author-chapter-submit"),
]
