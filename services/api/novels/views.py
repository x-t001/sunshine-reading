from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import get_enabled_categories, get_public_novel_by_id, get_public_novels
from .serializers import (
    CategorySerializer,
    NovelDetailSerializer,
    NovelListSerializer,
    NovelRatingInputSerializer,
    NovelRatingSummarySerializer,
)
from .services import build_rating_summary, delete_rating, submit_or_update_rating


class CategoryListView(APIView):
    def get(self, request):
        serializer = CategorySerializer(get_enabled_categories(), many=True)
        return success_response(serializer.data)


class NovelListView(APIView):
    def get(self, request):
        paginator = PublicPageNumberPagination()
        queryset = get_public_novels(request.query_params)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = NovelListSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))


class NovelDetailView(APIView):
    def get(self, request, id):
        novel = get_public_novel_by_id(id)
        if novel is None:
            raise NotFound("Novel not found.")

        serializer = NovelDetailSerializer(novel)
        return success_response(serializer.data)


class NovelRatingSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, novel_id):
        novel = get_public_novel_by_id(novel_id)
        if novel is None:
            raise NotFound("Novel not found.")

        serializer = NovelRatingSummarySerializer(build_rating_summary(novel, request.user))
        return success_response(serializer.data)


class NovelRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, novel_id):
        serializer = NovelRatingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = submit_or_update_rating(
            user=request.user,
            novel_id=novel_id,
            score=serializer.validated_data["score"],
            comment=serializer.validated_data.get("comment", ""),
        )
        return success_response(NovelRatingSummarySerializer(data).data)

    def delete(self, request, novel_id):
        data = delete_rating(user=request.user, novel_id=novel_id)
        return success_response(NovelRatingSummarySerializer(data).data)
