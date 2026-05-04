from django.urls import path

from .views import (
    AdminChapterApproveView,
    AdminChapterDetailView,
    AdminChapterRejectView,
    AdminPendingChapterListView,
    AuthorChapterDetailView,
    AuthorChapterSubmitView,
    AuthorNovelChapterListCreateView,
    ChapterDetailView,
    NovelChapterListView,
    ReviewerChapterApproveView,
    ReviewerChapterClaimView,
    ReviewerChapterDetailView,
    ReviewerChapterRejectView,
    ReviewerPendingChapterListView,
    ReviewerReviewingChapterListView,
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
    path("admin/chapters/pending/", AdminPendingChapterListView.as_view(), name="admin-chapter-pending-list"),
    path("admin/chapters/<int:id>/", AdminChapterDetailView.as_view(), name="admin-chapter-detail"),
    path("admin/chapters/<int:id>/approve/", AdminChapterApproveView.as_view(), name="admin-chapter-approve"),
    path("admin/chapters/<int:id>/reject/", AdminChapterRejectView.as_view(), name="admin-chapter-reject"),
    path("reviewer/chapters/pending/", ReviewerPendingChapterListView.as_view(), name="reviewer-chapter-pending-list"),
    path("reviewer/chapters/reviewing/", ReviewerReviewingChapterListView.as_view(), name="reviewer-chapter-reviewing-list"),
    path("reviewer/chapters/<int:id>/", ReviewerChapterDetailView.as_view(), name="reviewer-chapter-detail"),
    path("reviewer/chapters/<int:id>/claim/", ReviewerChapterClaimView.as_view(), name="reviewer-chapter-claim"),
    path("reviewer/chapters/<int:id>/approve/", ReviewerChapterApproveView.as_view(), name="reviewer-chapter-approve"),
    path("reviewer/chapters/<int:id>/reject/", ReviewerChapterRejectView.as_view(), name="reviewer-chapter-reject"),
]
