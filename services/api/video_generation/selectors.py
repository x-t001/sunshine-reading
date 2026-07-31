from django.db.models import Count, Max, Min, Q

from chapters.models import Chapter
from chapters.selectors import get_public_chapter_by_id
from novels.models import Novel
from users.permissions import is_admin_user

from .models import VideoAsset, VideoGenerationJob, VideoProject


def _with_related_project_data(queryset):
    return queryset.select_related("owner", "source_novel", "source_chapter").annotate(scene_count=Count("scenes", distinct=True))


def _apply_project_filters(queryset, params):
    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(title__icontains=keyword) | Q(source_title__icontains=keyword) | Q(summary__icontains=keyword))

    source_type = params.get("source_type")
    if source_type:
        queryset = queryset.filter(source_type=source_type)

    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status)

    return queryset


def get_user_video_projects(user, params):
    queryset = _with_related_project_data(VideoProject.objects.filter(owner=user, deleted_at__isnull=True))
    return _apply_project_filters(queryset, params).order_by("-created_at", "-id")


def get_video_project_for_user(user, project_id):
    queryset = _with_related_project_data(
        VideoProject.objects.prefetch_related("scenes", "assets").filter(id=project_id, deleted_at__isnull=True)
    )
    if not is_admin_user(user):
        queryset = queryset.filter(owner=user)
    return queryset.first()


def get_admin_video_projects(params):
    queryset = _with_related_project_data(VideoProject.objects.all())

    if not params.get("include_deleted"):
        queryset = queryset.filter(deleted_at__isnull=True)

    owner_id = params.get("owner_id")
    if owner_id:
        queryset = queryset.filter(owner_id=owner_id)

    return _apply_project_filters(queryset, params).order_by("-created_at", "-id")


def get_admin_video_project_by_id(project_id):
    return _with_related_project_data(VideoProject.objects.prefetch_related("scenes", "assets").filter(id=project_id)).first()


def get_video_asset_for_user(user, asset_id):
    queryset = VideoAsset.objects.select_related("project", "project__owner", "scene").filter(
        id=asset_id,
        project__deleted_at__isnull=True,
    )
    if not is_admin_user(user):
        queryset = queryset.filter(project__owner=user)
    return queryset.first()


def get_video_generation_job_for_user(user, job_id):
    queryset = VideoGenerationJob.objects.select_related("project", "project__owner", "requested_by").filter(
        id=job_id,
        project__deleted_at__isnull=True,
    )
    if not is_admin_user(user):
        queryset = queryset.filter(project__owner=user)
    return queryset.first()


def get_latest_video_generation_job(project, job_type=VideoGenerationJob.JobType.AI_STORYBOARD):
    return (
        VideoGenerationJob.objects.select_related("project", "requested_by")
        .filter(project=project, job_type=job_type)
        .order_by("-created_at", "-id")
        .first()
    )


def get_video_source_chapters(user, params):
    queryset = Chapter.objects.select_related("novel", "novel__author")
    if not is_admin_user(user):
        public_filter = Q(
            novel__audit_status="approved",
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
        ) & ~Q(novel__status="removed")
        queryset = queryset.filter(public_filter | Q(novel__author=user))

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(title__icontains=keyword) | Q(novel__title__icontains=keyword))
    return queryset.distinct().order_by("novel__title", "chapter_number", "id")


def get_video_source_chapter_for_user(user, chapter_id):
    if is_admin_user(user):
        return Chapter.objects.select_related("novel", "novel__author").filter(id=chapter_id).first()

    owned_chapter = (
        Chapter.objects.select_related("novel", "novel__author")
        .filter(id=chapter_id, novel__author=user)
        .first()
    )
    return owned_chapter or get_public_chapter_by_id(chapter_id)


def get_video_source_novels(user, params):
    queryset = Novel.objects.select_related("author")
    if is_admin_user(user):
        queryset = queryset.annotate(
            accessible_chapter_count=Count("chapters", distinct=True),
            first_chapter_number=Min("chapters__chapter_number"),
            last_chapter_number=Max("chapters__chapter_number"),
        )
    else:
        public_novel_filter = Q(audit_status=Novel.AuditStatus.APPROVED) & ~Q(status=Novel.Status.REMOVED)
        accessible_chapter_filter = Q(author=user) | (
            public_novel_filter
            & Q(
                chapters__status=Chapter.Status.PUBLISHED,
                chapters__audit_status=Chapter.AuditStatus.APPROVED,
            )
        )
        queryset = queryset.filter(Q(author=user) | public_novel_filter).annotate(
            accessible_chapter_count=Count("chapters", filter=accessible_chapter_filter, distinct=True),
            first_chapter_number=Min("chapters__chapter_number", filter=accessible_chapter_filter),
            last_chapter_number=Max("chapters__chapter_number", filter=accessible_chapter_filter),
        )

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(author__username__icontains=keyword)
            | Q(author__nickname__icontains=keyword)
        )
    return queryset.filter(accessible_chapter_count__gt=0).order_by("title", "id")


def get_video_source_novel_for_user(user, novel_id):
    return get_video_source_novels(user, {}).filter(id=novel_id).first()


def get_video_source_chapter_range_for_user(user, novel, start_chapter_number, end_chapter_number):
    queryset = Chapter.objects.select_related("novel", "novel__author").filter(
        novel=novel,
        chapter_number__gte=start_chapter_number,
        chapter_number__lte=end_chapter_number,
    )
    if is_admin_user(user) or novel.author_id == getattr(user, "id", None):
        return queryset.order_by("chapter_number", "id")

    return queryset.filter(
        novel__audit_status=Novel.AuditStatus.APPROVED,
        status=Chapter.Status.PUBLISHED,
        audit_status=Chapter.AuditStatus.APPROVED,
    ).exclude(novel__status=Novel.Status.REMOVED).order_by("chapter_number", "id")
