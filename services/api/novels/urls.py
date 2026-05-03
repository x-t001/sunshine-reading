from django.urls import path

from .views import (
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
]
