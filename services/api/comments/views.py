from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import get_chapter_comments, get_normal_comment, get_novel_comments
from .serializers import CommentSerializer, CreateCommentSerializer
from .services import create_comment, delete_comment


class NovelCommentListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, novel_id):
        queryset = get_novel_comments(novel_id)
        paginator = PublicPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CommentSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request, novel_id):
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = create_comment(
            user=request.user,
            novel_id=novel_id,
            content=serializer.validated_data["content"],
            parent_id=serializer.validated_data.get("parent_id"),
            chapter_id=serializer.validated_data.get("chapter_id"),
        )
        return success_response(CommentSerializer(comment).data)


class ChapterCommentListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, chapter_id):
        queryset = get_chapter_comments(chapter_id)
        paginator = PublicPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CommentSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))


class CommentDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, comment_id):
        comment = get_normal_comment(comment_id)
        if comment is None:
            raise NotFound("Comment not found.")
        return success_response(CommentSerializer(comment).data)

    def delete(self, request, comment_id):
        delete_comment(user=request.user, comment_id=comment_id)
        return success_response()
