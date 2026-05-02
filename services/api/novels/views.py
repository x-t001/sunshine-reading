from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import get_enabled_categories, get_public_novel_by_id, get_public_novels
from .serializers import CategorySerializer, NovelDetailSerializer, NovelListSerializer


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
