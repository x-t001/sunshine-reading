from django.urls import path

from .views import (
    BookshelfCheckView,
    BookshelfDeleteView,
    BookshelfView,
    ReadingHistoryView,
)

urlpatterns = [
    path("bookshelf/", BookshelfView.as_view(), name="bookshelf"),
    path("bookshelf/check/", BookshelfCheckView.as_view(), name="bookshelf-check"),
    path(
        "bookshelf/<int:novel_id>/",
        BookshelfDeleteView.as_view(),
        name="bookshelf-delete",
    ),
    path("reading-history/", ReadingHistoryView.as_view(), name="reading-history"),
]
