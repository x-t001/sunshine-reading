from django.urls import path

from .views import RankingListView

app_name = "rankings"

urlpatterns = [
    path("rankings/", RankingListView.as_view(), name="ranking-list"),
]
