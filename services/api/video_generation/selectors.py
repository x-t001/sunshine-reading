from django.db.models import Count, Q

from users.permissions import is_admin_user

from .models import VideoProject


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
        VideoProject.objects.prefetch_related("scenes").filter(id=project_id, deleted_at__isnull=True)
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
    return _with_related_project_data(VideoProject.objects.prefetch_related("scenes").filter(id=project_id)).first()
