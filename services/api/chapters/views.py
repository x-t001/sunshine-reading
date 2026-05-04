from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from users.permissions import IsAuthorOrAdmin, IsStaffAdmin

from common.pagination import PublicPageNumberPagination
from common.response import success_response
from novels.selectors import get_author_novel_by_id, get_public_novel_by_id

from .selectors import (
    get_adjacent_chapter_ids,
    get_admin_chapter_by_id,
    get_admin_pending_chapters,
    get_author_chapter_by_id,
    get_author_chapters_for_novel,
    get_public_chapter_by_id,
    get_public_chapters_for_novel,
)
from .serializers import (
    AdminChapterDetailSerializer,
    AdminChapterListSerializer,
    AdminChapterPendingQuerySerializer,
    AdminChapterRejectInputSerializer,
    AdminChapterReviewSerializer,
    AuthorChapterCreateSerializer,
    AuthorChapterDetailSerializer,
    AuthorChapterListSerializer,
    AuthorChapterSubmitSerializer,
    AuthorChapterUpdateSerializer,
    ChapterCatalogSerializer,
    ChapterDetailSerializer,
)
from .services import (
    approve_chapter_review,
    create_author_chapter,
    delete_author_chapter,
    reject_chapter_review,
    submit_chapter_review,
    update_author_chapter,
)


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


class AuthorNovelChapterListCreateView(APIView):
    permission_classes = [IsAuthorOrAdmin]

    def get_novel(self, request, novel_id):
        novel = get_author_novel_by_id(request.user, novel_id)
        if novel is None:
            raise NotFound("Novel not found.")
        return novel

    def get(self, request, novel_id):
        self.get_novel(request, novel_id)
        paginator = PublicPageNumberPagination()
        queryset = get_author_chapters_for_novel(request.user, novel_id)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AuthorChapterListSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request, novel_id):
        novel = self.get_novel(request, novel_id)
        serializer = AuthorChapterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chapter = create_author_chapter(novel, serializer.validated_data)
        return success_response(AuthorChapterDetailSerializer(chapter).data)


class AuthorChapterDetailView(APIView):
    permission_classes = [IsAuthorOrAdmin]

    def get_object(self, request, id):
        chapter = get_author_chapter_by_id(request.user, id)
        if chapter is None:
            raise NotFound("Chapter not found.")
        return chapter

    def get(self, request, id):
        chapter = self.get_object(request, id)
        return success_response(AuthorChapterDetailSerializer(chapter).data)

    def patch(self, request, id):
        chapter = self.get_object(request, id)
        serializer = AuthorChapterUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chapter = update_author_chapter(chapter, serializer.validated_data)
        return success_response(AuthorChapterDetailSerializer(chapter).data)

    def delete(self, request, id):
        chapter = self.get_object(request, id)
        delete_author_chapter(chapter)
        return success_response({})


class AuthorChapterSubmitView(APIView):
    permission_classes = [IsAuthorOrAdmin]

    def post(self, request, id):
        chapter = get_author_chapter_by_id(request.user, id)
        if chapter is None:
            raise NotFound("Chapter not found.")

        chapter = submit_chapter_review(chapter)
        return success_response(AuthorChapterSubmitSerializer(chapter).data)


class AdminPendingChapterListView(APIView):
    permission_classes = [IsStaffAdmin]

    def get(self, request):
        query_serializer = AdminChapterPendingQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        paginator = PublicPageNumberPagination()
        queryset = get_admin_pending_chapters(query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminChapterListSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))


class AdminChapterDetailView(APIView):
    permission_classes = [IsStaffAdmin]

    def get_object(self, id):
        chapter = get_admin_chapter_by_id(id)
        if chapter is None:
            raise NotFound("Chapter not found.")
        return chapter

    def get(self, request, id):
        chapter = self.get_object(id)
        return success_response(AdminChapterDetailSerializer(chapter).data)


class AdminChapterApproveView(APIView):
    permission_classes = [IsStaffAdmin]

    def post(self, request, id):
        chapter = get_admin_chapter_by_id(id)
        if chapter is None:
            raise NotFound("Chapter not found.")

        chapter = approve_chapter_review(chapter)
        return success_response(AdminChapterReviewSerializer(chapter).data)


class AdminChapterRejectView(APIView):
    permission_classes = [IsStaffAdmin]

    def post(self, request, id):
        chapter = get_admin_chapter_by_id(id)
        if chapter is None:
            raise NotFound("Chapter not found.")

        serializer = AdminChapterRejectInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chapter = reject_chapter_review(chapter, serializer.validated_data.get("reason", ""))
        return success_response(AdminChapterReviewSerializer(chapter).data)
