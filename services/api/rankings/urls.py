from django.urls import path

from .views import (
    AdminRankingItemDetailView,
    AdminRankingItemListCreateView,
    AdminRankingTypeDetailView,
    AdminRankingTypeListCreateView,
    AdminRankingTypeStatusView,
    RankingListView,
)

app_name = "rankings"

urlpatterns = [
    path("rankings/", RankingListView.as_view(), name="ranking-list"),
    path("admin/ranking-types/", AdminRankingTypeListCreateView.as_view(), name="admin-ranking-type-list-create"),
    path("admin/ranking-types/<int:id>/status/", AdminRankingTypeStatusView.as_view(), name="admin-ranking-type-status"),
    path("admin/ranking-types/<int:id>/", AdminRankingTypeDetailView.as_view(), name="admin-ranking-type-detail"),
    path("admin/ranking-items/", AdminRankingItemListCreateView.as_view(), name="admin-ranking-item-list-create"),
    path("admin/ranking-items/<int:id>/", AdminRankingItemDetailView.as_view(), name="admin-ranking-item-detail"),
]
