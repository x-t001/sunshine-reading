from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from users.permissions import IsAdminUser, IsAuthenticatedAndNotBanned

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import (
    get_admin_video_project_by_id,
    get_admin_video_projects,
    get_latest_video_generation_job,
    get_user_video_projects,
    get_video_generation_job_for_user,
    get_video_project_for_user,
    get_video_source_chapter_for_user,
    get_video_source_chapters,
)
from .serializers import (
    AdminVideoProjectQuerySerializer,
    VideoProjectCreateSerializer,
    VideoProjectChapterCreateSerializer,
    VideoProjectDetailSerializer,
    VideoProjectListSerializer,
    VideoProjectQuerySerializer,
    VideoProjectStoryboardSerializer,
    VideoGenerationJobSerializer,
    VideoSceneSerializer,
    VideoSceneUpdateSerializer,
    VideoStoryDraftSerializer,
    VideoSourceChapterQuerySerializer,
    VideoSourceChapterSerializer,
)
from .services import (
    create_text_video_project,
    create_ai_storyboard_job,
    create_chapter_video_project,
    generate_ai_storyboard_for_project,
    generate_story_draft,
    generate_storyboard_for_project,
    get_video_generation_capabilities,
    retry_ai_storyboard_job,
    soft_delete_video_project,
    update_video_scene,
)


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


class VideoSourceChapterListView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get(self, request):
        query_serializer = VideoSourceChapterQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        paginator = PublicPageNumberPagination()
        queryset = get_video_source_chapters(request.user, query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VideoSourceChapterSerializer(page, many=True, context={"user": request.user})
        return success_response(paginator.get_paginated_data(serializer.data))


class VideoProjectChapterCreateView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def post(self, request):
        serializer = VideoProjectChapterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chapter = get_video_source_chapter_for_user(request.user, serializer.validated_data["chapter_id"])
        if chapter is None:
            raise NotFound("Chapter source not found.")
        project = create_chapter_video_project(request.user, chapter, serializer.validated_data)
        project = get_video_project_for_user(request.user, project.id)
        return success_response(VideoProjectDetailSerializer(project).data)


class VideoStoryDraftView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def post(self, request):
        serializer = VideoStoryDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(generate_story_draft(serializer.validated_data))


class VideoProjectCapabilitiesView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get(self, request):
        return success_response(get_video_generation_capabilities())


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


class VideoProjectStoryboardView(VideoProjectDetailView):
    def post(self, request, id):
        project = self.get_object(request, id)
        serializer = VideoProjectStoryboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        generate_storyboard_for_project(project, serializer.validated_data, actor=request.user)
        project = self.get_object(request, id)
        return success_response(VideoProjectDetailSerializer(project).data)


class VideoProjectAiStoryboardView(VideoProjectDetailView):
    def post(self, request, id):
        project = self.get_object(request, id)
        serializer = VideoProjectStoryboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        generate_ai_storyboard_for_project(project, serializer.validated_data, actor=request.user)
        project = self.get_object(request, id)
        return success_response(VideoProjectDetailSerializer(project).data)


class VideoProjectStoryboardJobView(VideoProjectDetailView):
    def post(self, request, id):
        project = self.get_object(request, id)
        serializer = VideoProjectStoryboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_ai_storyboard_job(project, serializer.validated_data, actor=request.user)
        return success_response(VideoGenerationJobSerializer(job).data)


class VideoProjectLatestStoryboardJobView(VideoProjectDetailView):
    def get(self, request, id):
        project = self.get_object(request, id)
        job = get_latest_video_generation_job(project)
        return success_response(VideoGenerationJobSerializer(job).data if job else {})


class VideoGenerationJobDetailView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get_object(self, request, id):
        job = get_video_generation_job_for_user(request.user, id)
        if job is None:
            raise NotFound("Video generation job not found.")
        return job

    def get(self, request, id):
        return success_response(VideoGenerationJobSerializer(self.get_object(request, id)).data)


class VideoGenerationJobRetryView(VideoGenerationJobDetailView):
    def post(self, request, id):
        job = retry_ai_storyboard_job(self.get_object(request, id), actor=request.user)
        return success_response(VideoGenerationJobSerializer(job).data)


class VideoSceneDetailView(VideoProjectDetailView):
    def patch(self, request, id, scene_id):
        project = self.get_object(request, id)
        scene = project.scenes.filter(id=scene_id).first()
        if scene is None:
            raise NotFound("Video scene not found.")

        serializer = VideoSceneUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        scene = update_video_scene(project, scene, serializer.validated_data, actor=request.user)
        return success_response(VideoSceneSerializer(scene).data)


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
