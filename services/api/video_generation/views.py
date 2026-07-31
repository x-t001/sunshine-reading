from django.http import FileResponse
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from users.permissions import IsAdminUser, IsAuthenticatedAndNotBanned

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .models import VideoGenerationJob
from .selectors import (
    get_admin_video_project_by_id,
    get_admin_video_projects,
    get_latest_video_generation_job,
    get_user_video_projects,
    get_video_generation_job_for_user,
    get_video_asset_for_user,
    get_video_project_for_user,
    get_video_source_chapter_range_for_user,
    get_video_source_chapter_for_user,
    get_video_source_chapters,
    get_video_source_novel_for_user,
    get_video_source_novels,
)
from .serializers import (
    AdminVideoProjectQuerySerializer,
    VideoAudioReviewSerializer,
    VideoAssetJobCreateSerializer,
    VideoVisualReviewSerializer,
    VideoProjectCreateSerializer,
    VideoProjectChapterCreateSerializer,
    VideoProjectDetailSerializer,
    VideoProjectListSerializer,
    VideoProjectNovelCreateSerializer,
    VideoProjectQuerySerializer,
    VideoRenderJobCreateSerializer,
    VideoProjectStoryboardSerializer,
    VideoGenerationJobSerializer,
    VideoAssetSerializer,
    VideoSceneSerializer,
    VideoSceneUpdateSerializer,
    VideoStoryDraftSerializer,
    VideoSourceChapterQuerySerializer,
    VideoSourceChapterSerializer,
    VideoSourceNovelQuerySerializer,
    VideoSourceNovelSerializer,
)
from .services import (
    create_text_video_project,
    create_ai_storyboard_job,
    create_chapter_video_project,
    create_novel_video_project,
    create_video_asset_job,
    create_video_render_job,
    generate_ai_storyboard_for_project,
    generate_project_subtitle_asset,
    generate_story_draft,
    generate_storyboard_for_project,
    get_video_generation_capabilities,
    get_video_asset_download_path,
    retry_video_generation_job,
    review_video_audio_asset,
    review_video_visual_asset,
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


class VideoSourceNovelListView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get(self, request):
        query_serializer = VideoSourceNovelQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        paginator = PublicPageNumberPagination()
        queryset = get_video_source_novels(request.user, query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VideoSourceNovelSerializer(page, many=True, context={"user": request.user})
        return success_response(paginator.get_paginated_data(serializer.data))


class VideoProjectNovelCreateView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def post(self, request):
        serializer = VideoProjectNovelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        novel = get_video_source_novel_for_user(request.user, data["novel_id"])
        if novel is None:
            raise NotFound("Novel source not found.")
        chapters = get_video_source_chapter_range_for_user(
            request.user,
            novel,
            data["start_chapter_number"],
            data["end_chapter_number"],
        )
        project = create_novel_video_project(request.user, novel, chapters, data)
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
        return success_response(get_video_generation_capabilities(request.user))


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


class VideoProjectAssetJobView(VideoProjectDetailView):
    job_type = None

    def post(self, request, id):
        project = self.get_object(request, id)
        serializer = VideoAssetJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_video_asset_job(project, self.job_type, serializer.validated_data, actor=request.user)
        return success_response(VideoGenerationJobSerializer(job).data)

    def get(self, request, id):
        project = self.get_object(request, id)
        job = get_latest_video_generation_job(project, self.job_type)
        return success_response(VideoGenerationJobSerializer(job).data if job else {})


class VideoProjectImageAssetJobView(VideoProjectAssetJobView):
    job_type = VideoGenerationJob.JobType.IMAGE_ASSETS


class VideoProjectVideoClipJobView(VideoProjectAssetJobView):
    job_type = VideoGenerationJob.JobType.VIDEO_CLIPS


class VideoProjectNarrationAudioJobView(VideoProjectAssetJobView):
    job_type = VideoGenerationJob.JobType.NARRATION_AUDIO


class VideoProjectRenderJobView(VideoProjectDetailView):
    def post(self, request, id):
        project = self.get_object(request, id)
        serializer = VideoRenderJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_video_render_job(project, serializer.validated_data, actor=request.user)
        return success_response(VideoGenerationJobSerializer(job).data)

    def get(self, request, id):
        project = self.get_object(request, id)
        job = get_latest_video_generation_job(project, VideoGenerationJob.JobType.RENDER)
        return success_response(VideoGenerationJobSerializer(job).data if job else {})


class VideoProjectSubtitleAssetView(VideoProjectDetailView):
    def post(self, request, id):
        project = self.get_object(request, id)
        asset = generate_project_subtitle_asset(project, actor=request.user)
        return success_response(VideoAssetSerializer(asset).data)


class VideoAssetDownloadView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get(self, request, id):
        asset = get_video_asset_for_user(request.user, id)
        if asset is None:
            raise NotFound("Video asset not found.")
        target_path = get_video_asset_download_path(asset)
        return FileResponse(
            target_path.open("rb"),
            as_attachment=True,
            filename=asset.file_name or target_path.name,
            content_type=asset.mime_type or "application/octet-stream",
        )


class VideoAssetAudioReviewView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def patch(self, request, id):
        asset = get_video_asset_for_user(request.user, id)
        if asset is None:
            raise NotFound("Video asset not found.")
        serializer = VideoAudioReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = review_video_audio_asset(
            asset,
            serializer.validated_data["decision"],
            actor=request.user,
        )
        return success_response(VideoAssetSerializer(asset).data)


class VideoAssetVisualReviewView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def patch(self, request, id):
        asset = get_video_asset_for_user(request.user, id)
        if asset is None:
            raise NotFound("Video asset not found.")
        serializer = VideoVisualReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = review_video_visual_asset(
            asset,
            serializer.validated_data["decision"],
            serializer.validated_data["issue_codes"],
            serializer.validated_data["note"],
            actor=request.user,
        )
        return success_response(VideoAssetSerializer(asset).data)


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
        job = retry_video_generation_job(self.get_object(request, id), actor=request.user)
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
