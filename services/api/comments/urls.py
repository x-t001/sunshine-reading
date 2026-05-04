from django.urls import path

from .views import (
    AdminCommentDetailView,
    AdminCommentListView,
    AdminCommentStatusView,
    ChapterCommentListView,
    CommentDetailView,
    NovelCommentListCreateView,
)

urlpatterns = [
    path("novels/<int:novel_id>/comments/", NovelCommentListCreateView.as_view(), name="novel-comments"),
    path("chapters/<int:chapter_id>/comments/", ChapterCommentListView.as_view(), name="chapter-comments"),
    path("admin/comments/", AdminCommentListView.as_view(), name="admin-comment-list"),
    path("admin/comments/<int:comment_id>/status/", AdminCommentStatusView.as_view(), name="admin-comment-status"),
    path("admin/comments/<int:comment_id>/", AdminCommentDetailView.as_view(), name="admin-comment-detail"),
    path("comments/<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
]
