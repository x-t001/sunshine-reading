from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from users.permissions import IsAdminUser, IsAuthenticatedAndNotBanned

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import (
    get_admin_video_project_by_id,
    get_admin_video_projects,
    get_user_video_projects,
    get_video_project_for_user,
)
from .serializers import (
    AdminVideoProjectQuerySerializer,
    VideoProjectCreateSerializer,
    VideoProjectDetailSerializer,
    VideoProjectListSerializer,
    VideoProjectQuerySerializer,
)
from .services import create_text_video_project, soft_delete_video_project


class VideoProjectListCreateView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get(self, request):
        query_serializer = VideoProjectQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        paginator = PublicPageNumberPagination()
        queryset = get_user_video_projects(request.user, query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VideoProjectListSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request):
        serializer = VideoProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = create_text_video_project(request.user, serializer.validated_data)
        project = get_video_project_for_user(request.user, project.id)
        return success_response(VideoProjectDetailSerializer(project).data)


class VideoProjectDetailView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get_object(self, request, id):
        project = get_video_project_for_user(request.user, id)
        if project is None:
            raise NotFound("Video project not found.")
        return project

    def get(self, request, id):
        project = self.get_object(request, id)
        return success_response(VideoProjectDetailSerializer(project).data)

    def delete(self, request, id):
        project = self.get_object(request, id)
        soft_delete_video_project(project, actor=request.user)
        return success_response({})


class AdminVideoProjectListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query_serializer = AdminVideoProjectQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        paginator = PublicPageNumberPagination()
        queryset = get_admin_video_projects(query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VideoProjectListSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))


class AdminVideoProjectDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, id):
        project = get_admin_video_project_by_id(id)
        if project is None:
            raise NotFound("Video project not found.")
        return success_response(VideoProjectDetailSerializer(project).data)
