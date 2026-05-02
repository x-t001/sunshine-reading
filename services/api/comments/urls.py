from django.urls import path

from .views import ChapterCommentListView, CommentDetailView, NovelCommentListCreateView

urlpatterns = [
    path("novels/<int:novel_id>/comments/", NovelCommentListCreateView.as_view(), name="novel-comments"),
    path("chapters/<int:chapter_id>/comments/", ChapterCommentListView.as_view(), name="chapter-comments"),
    path("comments/<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
]
