from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import (
    get_user_bookshelf,
    get_user_reading_history,
    is_novel_in_user_bookshelf,
)
from .serializers import (
    AddBookshelfSerializer,
    BookshelfCheckSerializer,
    BookshelfItemSerializer,
    ReadingHistorySerializer,
    ReportReadingHistorySerializer,
)
from .services import (
    add_novel_to_bookshelf,
    remove_novel_from_bookshelf,
    report_reading_history,
)


class IsBookshelfUserAllowed(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("Authentication required.")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("User is banned.")
        return True


class BookshelfView(APIView):
    permission_classes = [IsBookshelfUserAllowed]

    def get(self, request):
        queryset = get_user_bookshelf(request.user)
        paginator = PublicPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BookshelfItemSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request):
        serializer = AddBookshelfSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = add_novel_to_bookshelf(
            user=request.user,
            novel_id=serializer.validated_data["novel_id"],
        )
        return success_response(BookshelfItemSerializer(entry).data)


class BookshelfDeleteView(APIView):
    permission_classes = [IsBookshelfUserAllowed]

    def delete(self, request, novel_id):
        remove_novel_from_bookshelf(user=request.user, novel_id=novel_id)
        return success_response()


class BookshelfCheckView(APIView):
    permission_classes = [IsBookshelfUserAllowed]

    def get(self, request):
        serializer = BookshelfCheckSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        in_bookshelf = is_novel_in_user_bookshelf(
            user=request.user,
            novel_id=serializer.validated_data["novel_id"],
        )
        return success_response({"in_bookshelf": in_bookshelf})


class ReadingHistoryView(APIView):
    permission_classes = [IsBookshelfUserAllowed]

    def get(self, request):
        queryset = get_user_reading_history(request.user)
        paginator = PublicPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ReadingHistorySerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request):
        serializer = ReportReadingHistorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        history = report_reading_history(
            user=request.user,
            novel_id=serializer.validated_data["novel_id"],
            chapter_id=serializer.validated_data["chapter_id"],
            reading_position=serializer.validated_data["reading_position"],
        )
        return success_response(ReadingHistorySerializer(history).data)
