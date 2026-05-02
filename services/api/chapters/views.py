from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from common.pagination import PublicPageNumberPagination
from common.response import success_response
from novels.selectors import get_public_novel_by_id

from .selectors import (
    get_adjacent_chapter_ids,
    get_public_chapter_by_id,
    get_public_chapters_for_novel,
)
from .serializers import ChapterCatalogSerializer, ChapterDetailSerializer


class NovelChapterListView(APIView):
    def get(self, request, novel_id):
        if get_public_novel_by_id(novel_id) is None:
            raise NotFound("Novel not found.")

        paginator = PublicPageNumberPagination()
        queryset = get_public_chapters_for_novel(novel_id)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ChapterCatalogSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))


class ChapterDetailView(APIView):
    def get(self, request, id):
        chapter = get_public_chapter_by_id(id)
        if chapter is None:
            raise NotFound("Chapter not found.")

        previous_id, next_id = get_adjacent_chapter_ids(chapter)
        chapter.previous_chapter_id = previous_id
        chapter.next_chapter_id = next_id
        serializer = ChapterDetailSerializer(chapter)
        return success_response(serializer.data)
