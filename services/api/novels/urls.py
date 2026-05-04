from django.urls import path

from .views import (
    AdminNovelApproveView,
    AdminNovelDetailView,
    AdminNovelRejectView,
    AdminPendingNovelListView,
    AuthorNovelDetailView,
    AuthorNovelListCreateView,
    AuthorNovelSubmitView,
    CategoryListView,
    NovelDetailView,
    NovelListView,
    NovelRatingSummaryView,
    NovelRatingView,
)

app_name = "novels"

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("novels/", NovelListView.as_view(), name="novel-list"),
    path("novels/<int:id>/", NovelDetailView.as_view(), name="novel-detail"),
    path("novels/<int:novel_id>/ratings/summary/", NovelRatingSummaryView.as_view(), name="novel-rating-summary"),
    path("novels/<int:novel_id>/ratings/", NovelRatingView.as_view(), name="novel-rating"),
    path("author/novels/", AuthorNovelListCreateView.as_view(), name="author-novel-list-create"),
    path("author/novels/<int:id>/", AuthorNovelDetailView.as_view(), name="author-novel-detail"),
    path("author/novels/<int:id>/submit/", AuthorNovelSubmitView.as_view(), name="author-novel-submit"),
    path("admin/novels/pending/", AdminPendingNovelListView.as_view(), name="admin-novel-pending-list"),
    path("admin/novels/<int:id>/", AdminNovelDetailView.as_view(), name="admin-novel-detail"),
    path("admin/novels/<int:id>/approve/", AdminNovelApproveView.as_view(), name="admin-novel-approve"),
    path("admin/novels/<int:id>/reject/", AdminNovelRejectView.as_view(), name="admin-novel-reject"),
]
