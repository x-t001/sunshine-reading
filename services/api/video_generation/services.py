import hashlib
import logging
import math
import os
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log

from .agent_workflow import (
    build_scene_agent_metadata,
    build_visual_continuity_plan,
    build_visual_world_model,
    build_workflow_record,
    mark_workflow_stale,
)
from .audio_quality import (
    analyze_wav_audio,
    build_pending_speech_quality_report,
    build_speech_quality_report,
)
from .models import VideoAsset, VideoGenerationJob, VideoProject, VideoScene
from .providers import (
    call_video_ai_storyboard,
    call_video_audio_transcription,
    call_video_clip_asset,
    call_video_image_asset,
    call_video_narration_asset,
    get_video_ai_capabilities,
    get_video_ai_provider_config,
    get_video_audio_transcription_config,
    get_video_asset_provider_config,
)
from .rendering import (
    SceneRenderInput,
    VideoRenderError,
    extract_video_tail_frame,
    get_local_render_capabilities,
    render_video_project,
)
from .serializers import UNSAFE_TEXT_PATTERNS, VideoAiStoryboardResultSerializer


logger = logging.getLogger(__name__)


STORYBOARD_ALLOWED_STATUSES = (
    VideoProject.Status.DRAFT,
    VideoProject.Status.FAILED,
    VideoProject.Status.STORYBOARD_READY,
    VideoProject.Status.COMPLETED,
)
STORYBOARD_EDITABLE_STATUSES = (VideoProject.Status.STORYBOARD_READY, VideoProject.Status.COMPLETED)
ASSET_ALLOWED_STATUSES = (VideoProject.Status.STORYBOARD_READY, VideoProject.Status.COMPLETED)
SUBTITLE_SOURCE_FIELDS = {"title", "narration_text", "subtitle_text", "duration_seconds"}
IMAGE_SOURCE_FIELDS = {"title", "visual_prompt", "camera_direction", "mood"}
VIDEO_SOURCE_FIELDS = IMAGE_SOURCE_FIELDS
AUDIO_SOURCE_FIELDS = {"title", "narration_text", "subtitle_text", "duration_seconds"}
ASSET_JOB_TYPES = (
    VideoGenerationJob.JobType.IMAGE_ASSETS,
    VideoGenerationJob.JobType.VIDEO_CLIPS,
    VideoGenerationJob.JobType.NARRATION_AUDIO,
)
VISUAL_ASSET_JOB_TYPES = (
    VideoGenerationJob.JobType.IMAGE_ASSETS,
    VideoGenerationJob.JobType.VIDEO_CLIPS,
)
MEDIA_JOB_TYPES = (*ASSET_JOB_TYPES, VideoGenerationJob.JobType.RENDER)
ASSET_TYPE_BY_JOB_TYPE = {
    VideoGenerationJob.JobType.IMAGE_ASSETS: VideoAsset.AssetType.IMAGE,
    VideoGenerationJob.JobType.VIDEO_CLIPS: VideoAsset.AssetType.VIDEO,
    VideoGenerationJob.JobType.NARRATION_AUDIO: VideoAsset.AssetType.AUDIO,
}
ASSET_PROVIDER_BY_JOB_TYPE = {
    VideoGenerationJob.JobType.IMAGE_ASSETS: call_video_image_asset,
    VideoGenerationJob.JobType.NARRATION_AUDIO: call_video_narration_asset,
}
VIDEO_REFERENCE_IMAGE_MIME_TYPES = ("image/jpeg", "image/png")
CAMERA_DIRECTIONS = (
    "缓慢推进，突出环境和人物关系",
    "中景跟拍，跟随主要行动",
    "近景特写，强调情绪变化",
    "低角度仰拍，制造压迫或高光感",
    "横向移镜，展示场景转换",
    "快速切入，形成节奏转折",
    "俯拍建立空间，随后切到人物",
    "定格式收束，留下悬念",
)
MOODS = ("铺垫", "悬念", "紧张", "转折", "温暖", "高燃", "沉静", "余韵")
GENRE_LABELS = {
    "fantasy": "东方幻想",
    "urban": "都市现实",
    "romance": "情感成长",
    "sci_fi": "科幻想象",
    "mystery": "悬疑推理",
    "history": "历史传奇",
}
TONE_LABELS = {
    "cinematic": "电影感",
    "warm": "温暖治愈",
    "suspense": "悬念紧张",
    "high_energy": "高燃爽感",
    "sad": "克制伤感",
}
MAX_NOVEL_SOURCE_CHAPTERS = 10
MAX_NOVEL_SOURCE_SNAPSHOT_LENGTH = 6000


def _mark_project_subtitle_assets_stale(project, actor, reason):
    assets = list(
        VideoAsset.objects.select_for_update().filter(
            project=project,
            asset_type=VideoAsset.AssetType.SUBTITLE,
            status=VideoAsset.Status.READY,
        )
    )
    for asset in assets:
        from_status = asset.status
        asset.status = VideoAsset.Status.STALE
        asset.failure_reason = "分镜已更新，请重新生成字幕。"
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.VIDEO_PROJECT,
            object_id=project.id,
            actor=actor,
            action=AuditLog.Action.UPDATE,
            from_status=from_status,
            to_status=asset.status,
            reason={
                "asset_id": asset.id,
                "asset_type": asset.asset_type,
                "event": "asset_invalidated",
                "source": reason,
            },
        )


def _mark_project_final_video_stale(project, actor, reason):
    assets = list(
        VideoAsset.objects.select_for_update().filter(
            project=project,
            asset_type=VideoAsset.AssetType.FINAL_VIDEO,
            status=VideoAsset.Status.READY,
        )
    )
    for asset in assets:
        from_status = asset.status
        asset.status = VideoAsset.Status.STALE
        asset.failure_reason = "项目素材已更新，请重新渲染成片。"
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.VIDEO_PROJECT,
            object_id=project.id,
            actor=actor,
            action=AuditLog.Action.UPDATE,
            from_status=from_status,
            to_status=asset.status,
            reason={
                "asset_id": asset.id,
                "asset_type": asset.asset_type,
                "event": "asset_invalidated",
                "source": reason,
            },
        )
    if project.status == VideoProject.Status.COMPLETED:
        project.status = VideoProject.Status.STORYBOARD_READY
        project.failure_reason = ""
        project.save(update_fields=["status", "failure_reason", "updated_at"])


def _mark_scene_assets_stale(project, scene, changed_fields, actor):
    affected_types = []
    if IMAGE_SOURCE_FIELDS.intersection(changed_fields):
        affected_types.append(VideoAsset.AssetType.IMAGE)
    if VIDEO_SOURCE_FIELDS.intersection(changed_fields):
        affected_types.append(VideoAsset.AssetType.VIDEO)
    if AUDIO_SOURCE_FIELDS.intersection(changed_fields):
        affected_types.append(VideoAsset.AssetType.AUDIO)
    if not affected_types:
        return

    assets = list(
        VideoAsset.objects.select_for_update().filter(
            project=project,
            scene=scene,
            asset_type__in=affected_types,
            status=VideoAsset.Status.READY,
        )
    )
    for asset in assets:
        from_status = asset.status
        asset.status = VideoAsset.Status.STALE
        asset.failure_reason = "分镜内容已更新，请重新生成素材。"
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.VIDEO_PROJECT,
            object_id=project.id,
            actor=actor,
            action=AuditLog.Action.UPDATE,
            from_status=from_status,
            to_status=asset.status,
            reason={
                "asset_id": asset.id,
                "asset_type": asset.asset_type,
                "scene_id": scene.id,
                "event": "asset_invalidated",
                "source": "scene_updated",
            },
        )


def _format_srt_timestamp(total_seconds):
    total_milliseconds = max(0, int(round(total_seconds * 1000)))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _normalize_subtitle_text(value):
    lines = []
    for line in re.split(r"\r?\n", (value or "").strip()):
        normalized_line = re.sub(r"\s+", " ", line).strip()
        if normalized_line:
            lines.append(normalized_line)
    return "\n".join(lines)


def _resolve_media_path(storage_path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    relative_path = Path(storage_path)
    if not storage_path or relative_path.is_absolute():
        raise NotFound("Video asset file not found.")

    target_path = (media_root / relative_path).resolve()
    try:
        target_path.relative_to(media_root)
    except ValueError:
        raise NotFound("Video asset file not found.")
    return target_path


def _video_tail_frame_storage_path(video_storage_path):
    relative_path = Path(video_storage_path)
    if not video_storage_path or relative_path.is_absolute():
        return ""
    return relative_path.with_name(f"{relative_path.stem}-tail.jpg").as_posix()


def _asset_related_storage_paths(asset_type, storage_path):
    paths = [storage_path] if storage_path else []
    if asset_type == VideoAsset.AssetType.VIDEO and storage_path:
        tail_frame_path = _video_tail_frame_storage_path(storage_path)
        if tail_frame_path:
            paths.append(tail_frame_path)
    return paths


def _load_reference_frame_file(storage_path, *, asset_id, mode, source_scene_no):
    try:
        image_path = _resolve_media_path(storage_path)
    except NotFound:
        return None, "reference_frame_file_missing"
    if not image_path.is_file():
        return None, "reference_frame_file_missing"
    file_size = image_path.stat().st_size
    if file_size <= 0:
        return None, "reference_frame_file_empty"
    if file_size > settings.VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES:
        return None, "reference_frame_file_too_large"
    content = image_path.read_bytes()
    mime_type = "image/png" if content.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg"
    if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        return None, "reference_frame_file_invalid"
    return {
        "asset_id": asset_id,
        "content": content,
        "mime_type": mime_type,
        "sha256": hashlib.sha256(content).hexdigest(),
        "mode": mode,
        "source_scene_no": source_scene_no,
    }, ""


def _load_previous_scene_tail_reference_frame(scene):
    if not settings.VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME or scene.scene_no <= 1:
        return None, ""
    previous_scene = VideoScene.objects.filter(
        project_id=scene.project_id,
        scene_no=scene.scene_no - 1,
    ).first()
    if previous_scene is None:
        return None, "previous_scene_missing"
    video_asset = (
        VideoAsset.objects.filter(
            project_id=scene.project_id,
            scene_id=previous_scene.id,
            asset_type=VideoAsset.AssetType.VIDEO,
            status=VideoAsset.Status.READY,
        )
        .order_by("-updated_at", "-id")
        .first()
    )
    if video_asset is None:
        return None, "previous_video_missing"
    tail_frame = (video_asset.metadata or {}).get("tail_frame") or {}
    if tail_frame.get("status") != "ready":
        return None, tail_frame.get("reason") or "previous_tail_unavailable"
    tail_frame_storage_path = _video_tail_frame_storage_path(video_asset.storage_path)
    if not tail_frame_storage_path:
        return None, "previous_tail_path_invalid"
    return _load_reference_frame_file(
        tail_frame_storage_path,
        asset_id=video_asset.id,
        mode="previous_scene_tail_base64",
        source_scene_no=previous_scene.scene_no,
    )


def _load_scene_video_reference_frame(scene):
    fallback_reasons = []
    tail_reference, tail_fallback_reason = _load_previous_scene_tail_reference_frame(scene)
    if tail_reference is not None:
        return tail_reference, fallback_reasons
    if tail_fallback_reason:
        fallback_reasons.append(tail_fallback_reason)
    if not settings.VIDEO_CLIP_USE_SCENE_IMAGE:
        fallback_reasons.append("scene_image_disabled")
        return None, fallback_reasons
    image_asset = (
        VideoAsset.objects.filter(
            project_id=scene.project_id,
            scene_id=scene.id,
            asset_type=VideoAsset.AssetType.IMAGE,
            status=VideoAsset.Status.READY,
        )
        .order_by("-updated_at", "-id")
        .first()
    )
    if image_asset is None:
        fallback_reasons.append("missing_ready_image")
        return None, fallback_reasons
    if image_asset.mime_type not in VIDEO_REFERENCE_IMAGE_MIME_TYPES:
        fallback_reasons.append("unsupported_image_format")
        return None, fallback_reasons
    image_reference, image_fallback_reason = _load_reference_frame_file(
        image_asset.storage_path,
        asset_id=image_asset.id,
        mode="scene_image_base64",
        source_scene_no=scene.scene_no,
    )
    if image_reference is None:
        fallback_reasons.append(image_fallback_reason)
        return None, fallback_reasons
    return image_reference, fallback_reasons


def _call_scene_asset_provider(job, scene, processing):
    if job.job_type == VideoGenerationJob.JobType.VIDEO_CLIPS:
        reference_frame, fallback_reasons = _load_scene_video_reference_frame(scene)
        return call_video_clip_asset(
            scene,
            reference_frame=reference_frame,
            reference_fallback_reasons=fallback_reasons,
            resume_task_id=processing["resume_provider_task_id"],
            on_task_created=lambda task_id, model: _record_scene_provider_task(
                processing["asset_id"],
                job,
                task_id,
                model,
            ),
        )
    return ASSET_PROVIDER_BY_JOB_TYPE[job.job_type](scene)


def _scene_audio_script_text(scene):
    agent_metadata = scene.agent_metadata or {}
    audio_script = agent_metadata.get("audio_script") or {}
    source_text = (
        audio_script.get("text")
        if "audio_script" in agent_metadata
        else (scene.narration_text or scene.subtitle_text or scene.title)
    )
    return " ".join(str(source_text or "").split())[:1024]


def _scene_requires_asset(job_type, scene):
    return (
        job_type != VideoGenerationJob.JobType.NARRATION_AUDIO
        or bool(_scene_audio_script_text(scene))
    )


def _audio_asset_is_render_approved(asset):
    metadata = asset.metadata or {}
    if (metadata.get("audio_quality") or {}).get("status") != "passed":
        return False
    manual_status = (metadata.get("audio_review") or {}).get("status")
    if manual_status == "rejected":
        return False
    if manual_status == "approved":
        return True
    return (metadata.get("speech_quality") or {}).get("status") == "passed"


def _visual_asset_is_render_approved(asset):
    metadata = asset.metadata if isinstance(asset.metadata, dict) else {}
    visual_review = metadata.get("visual_review")
    return isinstance(visual_review, dict) and visual_review.get("status") == "passed"


def _visual_asset_requires_regeneration(asset):
    metadata = asset.metadata if isinstance(asset.metadata, dict) else {}
    visual_review = metadata.get("visual_review")
    return isinstance(visual_review, dict) and visual_review.get("status") == "rejected"


def _build_scene_speech_quality(scene, content, audio_quality, job):
    config = get_video_audio_transcription_config()
    if not config["configured"]:
        return build_pending_speech_quality_report("asr_not_configured")
    if (
        audio_quality["metrics"].get("duration_seconds", 0) > 30
        or len(content) > config["max_file_bytes"]
    ):
        return build_pending_speech_quality_report("asr_limits_exceeded")
    try:
        transcription = call_video_audio_transcription(content)
    except ValidationError as error:
        logger.warning(
            "Audio ASR quality check unavailable for job %s scene %s: %s",
            job.id,
            scene.id,
            _validation_error_message(error),
        )
        return build_pending_speech_quality_report("asr_request_failed")
    report = build_speech_quality_report(
        _scene_audio_script_text(scene),
        transcription["text"],
        transcription["model"],
        config["minimum_similarity"],
    )
    report["provider_asset_id"] = transcription["provider_asset_id"]
    return report


def get_video_asset_download_path(asset):
    if asset.status != VideoAsset.Status.READY:
        raise ValidationError({"status": ["Video asset is not ready for download."]})
    target_path = _resolve_media_path(asset.storage_path)
    if not target_path.is_file():
        raise NotFound("Video asset file not found.")
    return target_path


@transaction.atomic
def review_video_audio_asset(asset, decision, actor=None):
    asset = (
        VideoAsset.objects.select_for_update()
        .select_related("project")
        .get(id=asset.id)
    )
    if asset.asset_type != VideoAsset.AssetType.AUDIO:
        raise ValidationError({"asset_type": ["只有旁白音频可以执行试听确认。"]})
    if asset.status != VideoAsset.Status.READY:
        raise ValidationError({"status": ["只有已就绪的旁白音频可以执行试听确认。"]})

    metadata = dict(asset.metadata or {})
    if decision == "approved" and (metadata.get("audio_quality") or {}).get("status") != "passed":
        raise ValidationError({"audio_quality": ["旁白必须先通过 WAV 波形质检。"]})
    previous_status = (metadata.get("audio_review") or {}).get("status") or "pending"
    metadata["audio_review"] = {
        "status": decision,
        "reviewer_id": actor.id if getattr(actor, "is_authenticated", False) else None,
        "reviewed_at": timezone.now().isoformat(),
    }
    asset.metadata = metadata
    asset.save(update_fields=["metadata", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=asset.project_id,
        actor=actor,
        action=AuditLog.Action.APPROVE if decision == "approved" else AuditLog.Action.REJECT,
        from_status=previous_status,
        to_status=decision,
        reason={
            "event": "audio_manual_review",
            "asset_id": asset.id,
            "scene_id": asset.scene_id,
            "speech_quality_status": (metadata.get("speech_quality") or {}).get("status") or "not_checked",
        },
    )
    _mark_project_final_video_stale(asset.project, actor, "audio_manual_review_changed")
    return asset


@transaction.atomic
def review_video_visual_asset(asset, decision, issue_codes=None, note="", actor=None):
    asset = (
        VideoAsset.objects.select_for_update()
        .select_related("project")
        .get(id=asset.id)
    )
    if asset.asset_type not in (VideoAsset.AssetType.IMAGE, VideoAsset.AssetType.VIDEO):
        raise ValidationError({"asset_type": ["只有静态分镜图或动态镜头可以执行视觉复核。"]})
    if asset.status != VideoAsset.Status.READY:
        raise ValidationError({"status": ["只有已就绪的画面素材可以执行视觉复核。"]})
    _ensure_no_active_asset_jobs(asset.project)

    metadata = dict(asset.metadata) if isinstance(asset.metadata, dict) else {}
    previous_review = metadata.get("visual_review")
    previous_review = dict(previous_review) if isinstance(previous_review, dict) else {}
    previous_status = previous_review.get("status") or "pending"
    next_status = "passed" if decision == "approved" else "rejected"
    previous_review.update(
        {
            "status": next_status,
            "mode": "manual_required",
            "reason": "manual_review",
            "issue_codes": list(issue_codes or []) if decision == "rejected" else [],
            "note": str(note or "").strip(),
            "reviewer_id": actor.id if getattr(actor, "is_authenticated", False) else None,
            "reviewed_at": timezone.now().isoformat(),
        }
    )
    metadata["visual_review"] = previous_review
    asset.metadata = metadata
    asset.save(update_fields=["metadata", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=asset.project_id,
        actor=actor,
        action=AuditLog.Action.APPROVE if decision == "approved" else AuditLog.Action.REJECT,
        from_status=previous_status,
        to_status=next_status,
        reason={
            "event": "visual_manual_review",
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "scene_id": asset.scene_id,
            "issue_codes": list(issue_codes or []) if decision == "rejected" else [],
        },
    )
    _mark_project_final_video_stale(asset.project, actor, "visual_manual_review_changed")
    return asset


def _write_video_asset_file(storage_path, content):
    target_path = _resolve_media_path(storage_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(f".{target_path.name}.{uuid4().hex}.tmp")
    try:
        temporary_path.write_bytes(content)
        os.replace(temporary_path, target_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return target_path


def _extract_and_store_video_tail_frame(scene, video_storage_path, source_video_sha256):
    if not settings.VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME:
        return {"status": "disabled", "reason": "previous_tail_disabled"}
    if not get_local_render_capabilities()["available"]:
        return {"status": "unavailable", "reason": "ffmpeg_unavailable"}

    tail_frame_storage_path = _video_tail_frame_storage_path(video_storage_path)
    if not tail_frame_storage_path:
        return {"status": "unavailable", "reason": "tail_frame_path_invalid"}
    try:
        result = extract_video_tail_frame(
            _resolve_media_path(video_storage_path),
            timeout_seconds=settings.VIDEO_CLIP_TAIL_FRAME_TIMEOUT_SECONDS,
            max_file_bytes=settings.VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES,
        )
        _write_video_asset_file(tail_frame_storage_path, result["content"])
    except (NotFound, VideoRenderError, OSError) as error:
        _delete_video_asset_files((tail_frame_storage_path,))
        logger.warning(
            "Video tail frame extraction unavailable for scene %s: %s",
            scene.id,
            error,
        )
        return {"status": "unavailable", "reason": "tail_frame_extraction_failed"}

    return {
        "status": "ready",
        "source_scene_no": scene.scene_no,
        "mime_type": result["mime_type"],
        "file_size": result["file_size"],
        "sha256": result["sha256"],
        "source_video_sha256": source_video_sha256,
        "extractor": "ffmpeg",
    }


def _delete_video_asset_files(storage_paths):
    for storage_path in storage_paths:
        if not storage_path:
            continue
        try:
            target_path = _resolve_media_path(storage_path)
        except NotFound:
            continue
        target_path.unlink(missing_ok=True)


def _schedule_video_asset_file_cleanup(storage_paths):
    normalized_paths = tuple(dict.fromkeys(path for path in storage_paths if path))
    if normalized_paths:
        transaction.on_commit(lambda: _delete_video_asset_files(normalized_paths))


def _schedule_scene_asset_cleanup(project):
    assets = VideoAsset.objects.filter(
        project=project,
        scene__isnull=False,
    ).exclude(storage_path="").values_list("asset_type", "storage_path")
    storage_paths = [
        storage_path
        for asset_type, asset_storage_path in assets
        for storage_path in _asset_related_storage_paths(asset_type, asset_storage_path)
    ]
    _schedule_video_asset_file_cleanup(storage_paths)


def _ensure_no_active_asset_jobs(project):
    if VideoGenerationJob.objects.filter(
        project=project,
        job_type__in=MEDIA_JOB_TYPES,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exists():
        raise ValidationError({"job": ["Wait for active asset jobs to finish before changing the storyboard."]})


def _targeted_regeneration_scene_ids(payload):
    if not isinstance(payload, dict) or not payload.get("targeted_regeneration"):
        return []
    scene_ids = payload.get("scene_ids")
    if not isinstance(scene_ids, list):
        return []
    return list(dict.fromkeys(scene_id for scene_id in scene_ids if isinstance(scene_id, int) and scene_id > 0))


def _get_visual_regeneration_usage(user, target_date):
    jobs = VideoGenerationJob.objects.filter(
        requested_by=user,
        job_type__in=VISUAL_ASSET_JOB_TYPES,
        created_at__date=target_date,
    ).values_list("request_payload", flat=True)
    used_scene_count = 0
    scene_counts = {}
    for payload in jobs:
        for scene_id in _targeted_regeneration_scene_ids(payload):
            used_scene_count += 1
            scene_counts[scene_id] = scene_counts.get(scene_id, 0) + 1
    return used_scene_count, scene_counts


def get_video_generation_capabilities(user=None):
    capabilities = get_video_ai_capabilities()
    render_capabilities = get_local_render_capabilities()
    capabilities.update(
        {
            "local_render_available": settings.VIDEO_RENDER_ENABLED and render_capabilities["available"],
            "local_render_engine": render_capabilities["engine"],
            "local_render_size": f"{settings.VIDEO_RENDER_WIDTH}x{settings.VIDEO_RENDER_HEIGHT}",
            "local_render_fps": settings.VIDEO_RENDER_FPS,
            "video_clips_previous_tail_frame_available": (
                settings.VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME and render_capabilities["available"]
            ),
        }
    )
    if not getattr(user, "is_authenticated", False):
        capabilities["image_assets_daily_jobs_remaining"] = 0
        capabilities["video_clips_daily_jobs_remaining"] = 0
        capabilities["narration_audio_daily_jobs_remaining"] = 0
        capabilities["visual_regeneration_daily_scenes_remaining"] = 0
        return capabilities

    today = timezone.localdate()
    visual_jobs = VideoGenerationJob.objects.filter(
        requested_by=user,
        job_type__in=VISUAL_ASSET_JOB_TYPES,
        created_at__date=today,
    ).values("job_type", "request_payload")
    image_job_count = sum(
        1
        for job in visual_jobs
        if job["job_type"] == VideoGenerationJob.JobType.IMAGE_ASSETS
        and not _targeted_regeneration_scene_ids(job["request_payload"])
    )
    video_job_count = sum(
        1
        for job in visual_jobs
        if job["job_type"] == VideoGenerationJob.JobType.VIDEO_CLIPS
        and not _targeted_regeneration_scene_ids(job["request_payload"])
    )
    audio_job_count = VideoGenerationJob.objects.filter(
        requested_by=user,
        job_type=VideoGenerationJob.JobType.NARRATION_AUDIO,
        created_at__date=today,
    ).count()
    capabilities["image_assets_daily_jobs_remaining"] = max(
        0,
        settings.VIDEO_IMAGE_DAILY_JOB_LIMIT - image_job_count,
    )
    capabilities["video_clips_daily_jobs_remaining"] = max(
        0,
        settings.VIDEO_CLIP_DAILY_JOB_LIMIT - video_job_count,
    )
    capabilities["narration_audio_daily_jobs_remaining"] = max(
        0,
        settings.VIDEO_TTS_DAILY_JOB_LIMIT - audio_job_count,
    )
    visual_regeneration_scene_count, _ = _get_visual_regeneration_usage(user, today)
    capabilities["visual_regeneration_daily_scenes_remaining"] = max(
        0,
        settings.VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT - visual_regeneration_scene_count,
    )
    return capabilities


def _derive_title(title, input_text):
    normalized_title = (title or "").strip()
    if normalized_title:
        return normalized_title

    normalized_text = " ".join((input_text or "").split())
    if not normalized_text:
        return "Untitled video project"
    return normalized_text[:60]


def _hash_source_text(input_text):
    return hashlib.sha256((input_text or "").encode("utf-8")).hexdigest()


def _validate_source_text(value, field_name):
    source_text = (value or "").strip()
    if len(source_text) < 100:
        raise ValidationError({field_name: ["Source content must contain at least 100 characters."]})
    for pattern in UNSAFE_TEXT_PATTERNS:
        if pattern.search(source_text):
            raise ValidationError({field_name: ["Source content contains unsafe HTML or script content."]})
    return source_text


def _build_novel_source_snapshot(chapters):
    chapter_sources = []
    for chapter in chapters:
        chapter_sources.append(
            (
                f"第 {chapter.chapter_number} 章 {chapter.title}",
                _validate_source_text(chapter.content, "chapter_range"),
            )
        )

    separator_length = max(0, len(chapter_sources) - 1) * 2
    header_length = sum(len(header) + 1 for header, _ in chapter_sources)
    content_budget = MAX_NOVEL_SOURCE_SNAPSHOT_LENGTH - header_length - separator_length
    per_chapter_budget = max(1, content_budget // len(chapter_sources))
    blocks = [f"{header}\n{content[:per_chapter_budget]}" for header, content in chapter_sources]
    return "\n\n".join(blocks)[:MAX_NOVEL_SOURCE_SNAPSHOT_LENGTH]


def _normalize_story_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def _split_story_units(value):
    text = _normalize_story_text(value)
    if not text:
        return []

    units = [unit.strip(" ，,") for unit in re.split(r"(?<=[。！？!?；;.!])\s*", text) if unit.strip(" ，,")]
    if len(units) >= 2:
        return units

    chunk_size = 90
    return [text[index : index + chunk_size].strip() for index in range(0, len(text), chunk_size) if text[index : index + chunk_size].strip()]


def _chunk_units(units, scene_count):
    if scene_count <= 0:
        return []

    chunks = []
    for index in range(scene_count):
        start = math.floor(index * len(units) / scene_count)
        end = math.floor((index + 1) * len(units) / scene_count)
        if start == end:
            end = min(start + 1, len(units))
        chunks.append("".join(units[start:end]).strip())

    fallback_text = " ".join(units)
    return [chunk or fallback_text for chunk in chunks]


def _trim_text(value, limit):
    text = _normalize_story_text(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _default_scene_count(duration_target):
    if duration_target <= 30:
        return 6
    if duration_target <= 45:
        return 9
    return 12


def _scene_durations(total_duration, scene_count):
    base = max(1, total_duration // scene_count)
    durations = [base for _ in range(scene_count)]
    for index in range(total_duration - base * scene_count):
        durations[index % scene_count] += 1
    return durations


def _scene_title(scene_no, text):
    title = _trim_text(text, 18).strip("。！？!?；;,.， ")
    return title or f"镜头 {scene_no}"


def _story_summary(text):
    summary = _trim_text(text, 180)
    return summary or "短视频分镜草稿"


def _story_title(prompt, genre):
    seed = _trim_text(prompt, 18).strip("。！？!?；;,.， ")
    if not seed:
        return f"{GENRE_LABELS.get(genre, '故事')}短片"
    return f"{seed}：短片剧情"


def _repeat_until_min_length(paragraphs, min_length=520, max_length=2800):
    text = "\n\n".join(paragraphs)
    closing = (
        "结尾不把所有谜底说尽，只让主角在新的选择前停住脚步。画面可以落在一个明确的动作上，"
        "既完成这一段故事，也为后续分镜留下悬念和情绪余波。"
    )
    while len(text) < min_length:
        text = f"{text}\n\n{closing}"
    return text[:max_length].rstrip()


def generate_story_draft(data):
    prompt = _normalize_story_text(data["prompt"])
    genre = data.get("genre", "fantasy")
    tone = data.get("tone", "cinematic")
    protagonist = _normalize_story_text(data.get("protagonist")) or "一个不肯认输的普通人"
    key_conflict = _normalize_story_text(data.get("key_conflict")) or "必须在失去重要之物前完成一次选择"
    genre_label = GENRE_LABELS.get(genre, "故事")
    tone_label = TONE_LABELS.get(tone, "电影感")
    duration_target = data.get("duration_target", 60)
    title = _story_title(prompt, genre)

    paragraphs = [
        f"这是一个偏{genre_label}的{tone_label}短视频故事。故事从“{prompt}”展开，主角是{protagonist}。开场画面要足够直接：熟悉的日常被一个异常细节打破，主角意识到自己已经站在变化的入口。",
        f"第一幕里，主角原本只想维持现状，却被迫面对“{key_conflict}”。外部压力逐步逼近，旁人给出的建议都看似合理，却没有一个真正能替主角承担代价。",
        "第二幕把冲突推高。主角尝试用旧办法解决问题，结果反而暴露更深的秘密：这件事并不是偶然发生，而是和主角过去忽略的一次选择有关。画面可以从安静的近景切到压迫感更强的环境。",
        "中段需要一个清晰转折。主角发现，只要退一步就能保住眼前安全，但那意味着让另一个无辜的人承受后果。这个选择让故事从单纯的事件推进，转向人物内心的真正考验。",
        f"第三幕进入行动段。主角不再等待帮助，而是主动拆解困局。节奏变快，镜头可以围绕关键物件、奔跑路线、对峙眼神和短促对白推进，让{duration_target}秒短片具备明确起伏。",
        "高潮处，主角付出一个可见代价，换来局势反转。胜利不需要过度解释，重点是让观众看见主角和开场时已经不同：他不再只是被事件推着走，而是能承担选择的人。",
        "收束时，危机暂时平息，但新的线索被留下。主角看向远处或握紧关键物件，画面停在一个能继续延展的动作上，既适合生成分镜，也方便后续扩展成系列短视频。",
    ]

    input_text = _repeat_until_min_length(paragraphs)
    return {
        "title": title,
        "summary": _story_summary(input_text),
        "input_text": input_text,
        "duration_target": duration_target,
        "aspect_ratio": "9:16",
        "style_preset": "cinematic_story",
        "genre": genre,
        "tone": tone,
    }


@transaction.atomic
def create_text_video_project(owner, data):
    if data["source_type"] != VideoProject.SourceType.TEXT:
        raise ValidationError({"source_type": ["Only pasted text projects are supported in this iteration."]})

    title = _derive_title(data.get("title"), data["input_text"])
    project = VideoProject.objects.create(
        owner=owner,
        source_type=VideoProject.SourceType.TEXT,
        source_title=title,
        source_excerpt_hash=_hash_source_text(data["input_text"]),
        input_text=data["input_text"],
        title=title,
        style_preset=data.get("style_preset", "cinematic_story"),
        duration_target=data.get("duration_target", 60),
        aspect_ratio=data.get("aspect_ratio", "9:16"),
        status=VideoProject.Status.DRAFT,
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=owner,
        action=AuditLog.Action.CREATE,
        to_status=project.status,
        reason={
            "source_type": project.source_type,
            "title": project.title,
        },
    )
    return project


@transaction.atomic
def create_chapter_video_project(owner, chapter, data):
    source_text = _validate_source_text(chapter.content, "chapter_id")

    input_snapshot = source_text[:3000]
    source_title = f"{chapter.novel.title} · {chapter.title}"
    title = _derive_title(data.get("title"), source_title)
    project = VideoProject.objects.create(
        owner=owner,
        source_type=VideoProject.SourceType.CHAPTER,
        source_novel=chapter.novel,
        source_chapter=chapter,
        source_title=source_title,
        source_excerpt_hash=_hash_source_text(input_snapshot),
        input_text=input_snapshot,
        title=title,
        style_preset=data.get("style_preset", "cinematic_story"),
        duration_target=data.get("duration_target", 60),
        aspect_ratio=data.get("aspect_ratio", "9:16"),
        status=VideoProject.Status.DRAFT,
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=owner,
        action=AuditLog.Action.CREATE,
        to_status=project.status,
        reason={
            "source_type": project.source_type,
            "source_novel_id": chapter.novel_id,
            "source_chapter_id": chapter.id,
            "snapshot_length": len(input_snapshot),
        },
    )
    return project


@transaction.atomic
def create_novel_video_project(owner, novel, chapters, data):
    chapters = list(chapters)
    if not chapters:
        raise ValidationError({"chapter_range": ["At least one accessible chapter is required."]})
    if len(chapters) > MAX_NOVEL_SOURCE_CHAPTERS:
        raise ValidationError({"chapter_range": [f"At most {MAX_NOVEL_SOURCE_CHAPTERS} chapters can be selected."]})
    if any(chapter.novel_id != novel.id for chapter in chapters):
        raise ValidationError({"chapter_range": ["All selected chapters must belong to the source novel."]})

    start_chapter_number = data["start_chapter_number"]
    end_chapter_number = data["end_chapter_number"]
    if chapters[0].chapter_number != start_chapter_number or chapters[-1].chapter_number != end_chapter_number:
        raise NotFound("Novel chapter range not found.")

    input_snapshot = _build_novel_source_snapshot(chapters)
    range_label = (
        f"第 {start_chapter_number} 章"
        if start_chapter_number == end_chapter_number
        else f"第 {start_chapter_number}-{end_chapter_number} 章"
    )
    source_title = f"{novel.title} · {range_label}"
    title = _derive_title(data.get("title"), source_title)
    project = VideoProject.objects.create(
        owner=owner,
        source_type=VideoProject.SourceType.NOVEL,
        source_novel=novel,
        source_title=source_title,
        source_excerpt_hash=_hash_source_text(input_snapshot),
        input_text=input_snapshot,
        title=title,
        style_preset=data.get("style_preset", "cinematic_story"),
        duration_target=data.get("duration_target", 60),
        aspect_ratio=data.get("aspect_ratio", "9:16"),
        status=VideoProject.Status.DRAFT,
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=owner,
        action=AuditLog.Action.CREATE,
        to_status=project.status,
        reason={
            "source_type": project.source_type,
            "source_novel_id": novel.id,
            "source_chapter_ids": [chapter.id for chapter in chapters],
            "start_chapter_number": start_chapter_number,
            "end_chapter_number": end_chapter_number,
            "snapshot_length": len(input_snapshot),
        },
    )
    return project


@transaction.atomic
def generate_storyboard_for_project(project, data, actor=None):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_ALLOWED_STATUSES:
        raise ValidationError({"status": ["Storyboard can only be generated from draft, failed, or storyboard-ready projects."]})
    _ensure_no_active_asset_jobs(project)

    story_text = _normalize_story_text(project.input_text)
    if not story_text:
        raise ValidationError({"input_text": ["Text-sourced video project has no input text."]})

    scene_count = data.get("scene_count") or _default_scene_count(project.duration_target)
    units = _split_story_units(story_text)
    chunks = _chunk_units(units, scene_count)
    durations = _scene_durations(project.duration_target, scene_count)

    from_status = project.status
    _mark_project_subtitle_assets_stale(project, actor, "storyboard_regenerated")
    _mark_project_final_video_stale(project, actor, "storyboard_regenerated")
    _schedule_scene_asset_cleanup(project)
    VideoScene.objects.filter(project=project).delete()
    for index, chunk in enumerate(chunks, start=1):
        mood = MOODS[(index - 1) % len(MOODS)]
        camera_direction = CAMERA_DIRECTIONS[(index - 1) % len(CAMERA_DIRECTIONS)]
        scene_text = _trim_text(chunk, 120)
        VideoScene.objects.create(
            project=project,
            scene_no=index,
            title=_scene_title(index, chunk),
            visual_prompt=f"竖屏 9:16，{mood}氛围，{camera_direction}。画面内容：{scene_text}",
            narration_text=scene_text,
            subtitle_text=_trim_text(chunk, 48),
            duration_seconds=durations[index - 1],
            camera_direction=camera_direction,
            mood=mood,
            status=VideoScene.Status.READY,
        )

    project.summary = _story_summary(story_text)
    project.status = VideoProject.Status.STORYBOARD_READY
    project.failure_reason = ""
    project.agent_workflow = {}
    project.save(update_fields=["summary", "status", "failure_reason", "agent_workflow", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=project.status,
        reason={
            "scene_count": scene_count,
            "generator": "local_storyboard",
        },
    )
    return project


@transaction.atomic
def generate_project_subtitle_asset(project, actor=None):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in ASSET_ALLOWED_STATUSES:
        raise ValidationError({"status": ["Subtitles can only be generated after the storyboard is ready."]})

    scenes = list(VideoScene.objects.filter(project=project).order_by("scene_no", "id"))
    if not scenes:
        raise ValidationError({"scenes": ["Generate the storyboard before creating subtitles."]})

    blocks = []
    elapsed_seconds = 0
    for scene in scenes:
        start_seconds = elapsed_seconds
        elapsed_seconds += scene.duration_seconds
        subtitle_text = _normalize_subtitle_text(scene.subtitle_text or scene.narration_text)
        if not subtitle_text:
            continue
        blocks.append(
            "\n".join(
                (
                    str(len(blocks) + 1),
                    f"{_format_srt_timestamp(start_seconds)} --> {_format_srt_timestamp(elapsed_seconds)}",
                    subtitle_text,
                )
            )
        )

    if not blocks:
        raise ValidationError({"subtitles": ["当前分镜没有可生成的字幕文本。"]})

    content = ("\n\n".join(blocks) + "\n").encode("utf-8")
    storage_path = Path("video_projects", str(project.id), "subtitles", "storyboard.srt").as_posix()
    _write_video_asset_file(storage_path, content)

    asset, created = VideoAsset.objects.update_or_create(
        project=project,
        scene=None,
        asset_type=VideoAsset.AssetType.SUBTITLE,
        defaults={
            "status": VideoAsset.Status.READY,
            "storage_path": storage_path,
            "file_name": "storyboard.srt",
            "mime_type": "application/x-subrip; charset=utf-8",
            "file_size": len(content),
            "provider": "local",
            "provider_asset_id": "",
            "metadata": {
                "format": "srt",
                "scene_count": len(scenes),
                "duration_seconds": elapsed_seconds,
            },
            "failure_reason": "",
        },
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
        to_status=asset.status,
        reason={
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "generator": "local_srt",
            "scene_count": len(scenes),
            "duration_seconds": elapsed_seconds,
            "file_size": asset.file_size,
        },
    )
    _mark_project_final_video_stale(project, actor, "subtitle_regenerated")
    return asset


def _first_validation_error(detail, path=()):
    if isinstance(detail, dict):
        for field_name, value in detail.items():
            return _first_validation_error(value, (*path, str(field_name)))
        return path, "AI storyboard generation failed."

    if isinstance(detail, (list, tuple)):
        for index, value in enumerate(detail):
            if isinstance(value, (dict, list, tuple)):
                if not value:
                    continue
                return _first_validation_error(value, (*path, str(index)))
            return path, str(value)
        return path, "AI storyboard generation failed."

    return path, str(detail)


def _validation_error_message(error):
    path, message = _first_validation_error(getattr(error, "detail", error))
    prefix = ".".join(path)
    return (f"{prefix}: {message}" if prefix else message)[:500]


@transaction.atomic
def _begin_ai_storyboard_generation(project, actor, model):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_ALLOWED_STATUSES:
        raise ValidationError({"status": ["AI storyboard can only be generated from draft, failed, or storyboard-ready projects."]})
    _ensure_no_active_asset_jobs(project)
    if not _normalize_story_text(project.input_text):
        raise ValidationError({"input_text": ["Text-sourced video project has no input text."]})

    from_status = project.status
    project.status = VideoProject.Status.ANALYZING
    project.failure_reason = ""
    project.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=project.status,
        reason={"generator": "provider_storyboard", "model": model},
    )
    return project


@transaction.atomic
def _complete_ai_storyboard_generation(project_id, storyboard, provider_result, actor):
    project = VideoProject.objects.select_for_update().get(id=project_id)
    if project.status != VideoProject.Status.ANALYZING:
        raise ValidationError({"status": ["AI storyboard generation is no longer active."]})

    scenes = storyboard["scenes"]
    durations = [scene["duration_seconds"] for scene in scenes]
    if sum(durations) != project.duration_target:
        durations = _scene_durations(project.duration_target, len(scenes))
    for index, scene_data in enumerate(scenes):
        scene_data["duration_seconds"] = durations[index]

    production_plan = provider_result.get("production_plan") or {}
    visual_world_model = {}
    if production_plan:
        visual_world_model = provider_result.get("visual_world_model") or build_visual_world_model(
            production_plan,
            settings.VIDEO_RENDER_FPS,
        )
        visual_world_model = {
            **visual_world_model,
            "visual_continuity_plan": build_visual_continuity_plan(
                scenes,
                production_plan,
                visual_world_model,
            ),
        }
    agent_workflow = (
        build_workflow_record(
            production_plan,
            scenes,
            project.duration_target,
            settings.VIDEO_CLIP_DURATION_SECONDS,
            provider_result["model"],
            provider_result.get("stage_usage") or {},
            provider_result.get("repair_report") or {},
            provider_call_count=provider_result.get("provider_call_count"),
            visual_world_model=visual_world_model,
            render_fps=settings.VIDEO_RENDER_FPS,
        )
        if production_plan
        else {}
    )

    _mark_project_subtitle_assets_stale(project, actor, "storyboard_regenerated")
    _mark_project_final_video_stale(project, actor, "storyboard_regenerated")
    _schedule_scene_asset_cleanup(project)
    VideoScene.objects.filter(project=project).delete()
    for index, scene_data in enumerate(scenes, start=1):
        VideoScene.objects.create(
            project=project,
            scene_no=index,
            title=scene_data["title"],
            visual_prompt=scene_data["visual_prompt"],
            narration_text=scene_data["narration_text"],
            subtitle_text=scene_data["subtitle_text"],
            duration_seconds=durations[index - 1],
            camera_direction=scene_data["camera_direction"],
            mood=scene_data["mood"],
            agent_metadata=(
                build_scene_agent_metadata(
                    scene_data,
                    production_plan,
                    index,
                    previous_scene_data=scenes[index - 2] if index > 1 else None,
                    visual_world_model=visual_world_model,
                )
                if production_plan
                else {}
            ),
            status=VideoScene.Status.READY,
        )

    project.summary = storyboard.get("summary") or _story_summary(project.input_text)
    project.status = VideoProject.Status.STORYBOARD_READY
    project.failure_reason = ""
    project.agent_workflow = agent_workflow
    project.save(update_fields=["summary", "status", "failure_reason", "agent_workflow", "updated_at"])
    usage = provider_result.get("usage") or {}
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=VideoProject.Status.ANALYZING,
        to_status=project.status,
        reason={
            "generator": "provider_storyboard",
            "model": provider_result["model"],
            "scene_count": len(scenes),
            "total_tokens": usage.get("total_tokens"),
            "provider_call_count": provider_result.get("provider_call_count"),
            "workflow_version": provider_result.get("workflow_version"),
            "quality_score": (agent_workflow.get("quality_report") or {}).get("score"),
        },
    )
    return project


@transaction.atomic
def _fail_ai_storyboard_generation(project_id, error_message, actor, model):
    project = VideoProject.objects.select_for_update().get(id=project_id)
    if project.status != VideoProject.Status.ANALYZING:
        return project

    project.status = VideoProject.Status.FAILED
    project.failure_reason = error_message
    project.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=VideoProject.Status.ANALYZING,
        to_status=project.status,
        reason={"generator": "provider_storyboard", "model": model, "error": error_message},
    )
    return project


def generate_ai_storyboard_for_project(project, data, actor=None):
    config = get_video_ai_provider_config()
    if not config["configured"]:
        raise ValidationError("服务端尚未配置 AI 分镜服务。")

    scene_count = data.get("scene_count") or _default_scene_count(project.duration_target)
    project = _begin_ai_storyboard_generation(project, actor, config["model"])
    try:
        provider_result = call_video_ai_storyboard(project, scene_count)
        serializer = VideoAiStoryboardResultSerializer(
            data=provider_result["storyboard"],
            context={
                "expected_scene_count": scene_count,
                "production_plan": provider_result.get("production_plan") or {},
            },
        )
        serializer.is_valid(raise_exception=True)
        return _complete_ai_storyboard_generation(project.id, serializer.validated_data, provider_result, actor)
    except ValidationError as error:
        _fail_ai_storyboard_generation(project.id, _validation_error_message(error), actor, config["model"])
        raise
    except Exception:
        error_message = "AI 分镜生成失败，请稍后重试。"
        _fail_ai_storyboard_generation(project.id, error_message, actor, config["model"])
        raise ValidationError(error_message)


@transaction.atomic
def create_ai_storyboard_job(project, data, actor=None):
    config = get_video_ai_provider_config()
    if not config["configured"]:
        raise ValidationError("服务端尚未配置 AI 分镜服务。")

    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_ALLOWED_STATUSES:
        raise ValidationError({"status": ["AI storyboard job can only be queued from draft, failed, or storyboard-ready projects."]})
    _ensure_no_active_asset_jobs(project)
    if not _normalize_story_text(project.input_text):
        raise ValidationError({"input_text": ["Text-sourced video project has no input text."]})
    if VideoGenerationJob.objects.filter(
        project=project,
        job_type=VideoGenerationJob.JobType.AI_STORYBOARD,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exists():
        raise ValidationError({"job": ["An AI storyboard job is already queued or running for this project."]})

    scene_count = data.get("scene_count") or _default_scene_count(project.duration_target)
    try:
        with transaction.atomic():
            job = VideoGenerationJob.objects.create(
                project=project,
                requested_by=actor if getattr(actor, "is_authenticated", False) else None,
                job_type=VideoGenerationJob.JobType.AI_STORYBOARD,
                status=VideoGenerationJob.Status.QUEUED,
                provider="openai_compatible",
                model_name=config["model"],
                request_payload={"scene_count": scene_count},
                max_attempts=settings.VIDEO_JOB_MAX_ATTEMPTS,
            )
    except IntegrityError:
        raise ValidationError({"job": ["An AI storyboard job is already queued or running for this project."]})

    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=actor,
        action=AuditLog.Action.CREATE,
        to_status=job.status,
        reason={"project_id": project.id, "job_type": job.job_type, "scene_count": scene_count},
    )
    return job


@transaction.atomic
def create_video_asset_job(project, job_type, data, actor=None):
    if job_type not in ASSET_JOB_TYPES:
        raise ValidationError({"job_type": ["Unsupported video asset job type."]})
    config = get_video_asset_provider_config(job_type)
    if not config["configured"]:
        raise ValidationError("服务端尚未配置对应的短视频素材服务。")

    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in ASSET_ALLOWED_STATUSES:
        raise ValidationError({"status": ["Assets can only be generated after the storyboard is ready."]})

    all_scenes = list(VideoScene.objects.select_for_update().filter(project=project).order_by("scene_no", "id"))
    if not all_scenes:
        raise ValidationError({"scenes": ["Generate the storyboard before creating assets."]})
    if len(all_scenes) > 12:
        raise ValidationError({"scenes": ["A single asset job can process at most 12 scenes."]})
    requested_scene_ids = data.get("scene_ids") or []
    regenerate = data.get("regenerate", False)
    if requested_scene_ids and job_type not in VISUAL_ASSET_JOB_TYPES:
        raise ValidationError({"scene_ids": ["局部重生成当前仅支持静态分镜图和动态镜头。"]})
    if requested_scene_ids and not regenerate:
        raise ValidationError({"regenerate": ["指定 scene_ids 时必须启用 regenerate。"]})
    scene_by_id = {scene.id: scene for scene in all_scenes}
    unknown_scene_ids = [scene_id for scene_id in requested_scene_ids if scene_id not in scene_by_id]
    if unknown_scene_ids:
        raise ValidationError({"scene_ids": ["包含不属于当前项目的分镜。"]})
    scenes = (
        [scene_by_id[scene_id] for scene_id in requested_scene_ids]
        if requested_scene_ids
        else all_scenes
    )
    targeted_regeneration = bool(requested_scene_ids)
    if VideoGenerationJob.objects.filter(
        project=project,
        job_type=job_type,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exists():
        raise ValidationError({"job": ["An asset job of this type is already queued or running for this project."]})

    if getattr(actor, "is_authenticated", False):
        today = timezone.localdate()
        if targeted_regeneration:
            used_scene_count, scene_regeneration_counts = _get_visual_regeneration_usage(actor, today)
            if used_scene_count + len(scenes) > settings.VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT:
                raise ValidationError({"quota": ["今日局部重拍镜头额度已用完。"]})
            exhausted_scene_numbers = [
                scene.scene_no
                for scene in scenes
                if scene_regeneration_counts.get(scene.id, 0)
                >= settings.VIDEO_VISUAL_REGENERATION_PER_SCENE_LIMIT
            ]
            if exhausted_scene_numbers:
                scene_labels = ", ".join(str(scene_no) for scene_no in exhausted_scene_numbers)
                raise ValidationError({"quota": [f"分镜 {scene_labels} 已达到单镜重拍上限。"]})
        else:
            jobs_today = VideoGenerationJob.objects.filter(
                requested_by=actor,
                job_type=job_type,
                created_at__date=today,
            ).values_list("request_payload", flat=True)
            counted_jobs = sum(
                1
                for payload in jobs_today
                if not _targeted_regeneration_scene_ids(payload)
            )
            if counted_jobs >= config["daily_job_limit"]:
                raise ValidationError({"quota": ["The daily asset job limit has been reached."]})

    asset_type = ASSET_TYPE_BY_JOB_TYPE[job_type]
    asset_scenes = [scene for scene in scenes if _scene_requires_asset(job_type, scene)]
    if not asset_scenes:
        raise ValidationError({"scenes": ["当前分镜均为静默镜头，无需生成旁白音频。"]})

    existing_assets = {
        asset.scene_id: asset
        for asset in VideoAsset.objects.select_for_update().filter(
            project=project,
            scene__in=asset_scenes,
            asset_type=asset_type,
        )
    }
    if targeted_regeneration:
        invalid_scene_numbers = [
            scene.scene_no
            for scene in asset_scenes
            if (
                existing_assets.get(scene.id) is None
                or existing_assets[scene.id].status != VideoAsset.Status.READY
                or not _visual_asset_requires_regeneration(existing_assets[scene.id])
            )
        ]
        if invalid_scene_numbers:
            scene_labels = ", ".join(str(scene_no) for scene_no in invalid_scene_numbers)
            raise ValidationError(
                {"scene_ids": [f"分镜 {scene_labels} 必须先在已就绪画面中标记为需要重拍。"]}
            )
    work_required = False
    for scene in asset_scenes:
        asset = existing_assets.get(scene.id)
        if asset is not None and asset.status == VideoAsset.Status.READY and not regenerate:
            continue
        work_required = True
        if asset is None:
            VideoAsset.objects.create(
                project=project,
                scene=scene,
                asset_type=asset_type,
                status=VideoAsset.Status.QUEUED,
                provider=config["provider"],
            )
        elif asset.status != VideoAsset.Status.READY:
            asset.status = VideoAsset.Status.QUEUED
            asset.failure_reason = ""
            asset.provider = config["provider"]
            asset.save(update_fields=["status", "failure_reason", "provider", "updated_at"])
    if not work_required:
        raise ValidationError({"assets": ["All scene assets are ready. Set regenerate to create new versions."]})

    if VideoGenerationJob.objects.filter(
        project=project,
        job_type=VideoGenerationJob.JobType.RENDER,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exists():
        raise ValidationError({"job": ["Wait for the active render job to finish before generating assets."]})
    _mark_project_final_video_stale(project, actor, "scene_asset_regeneration_started")

    try:
        with transaction.atomic():
            job = VideoGenerationJob.objects.create(
                project=project,
                requested_by=actor if getattr(actor, "is_authenticated", False) else None,
                job_type=job_type,
                status=VideoGenerationJob.Status.QUEUED,
                provider=config["provider"],
                model_name=config["model"],
                request_payload={
                    "asset_type": asset_type,
                    "regenerate": regenerate,
                    "scene_ids": requested_scene_ids,
                    "targeted_regeneration": targeted_regeneration,
                },
                max_attempts=settings.VIDEO_JOB_MAX_ATTEMPTS,
            )
    except IntegrityError:
        raise ValidationError({"job": ["An asset job of this type is already queued or running for this project."]})

    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=actor,
        action=AuditLog.Action.CREATE,
        to_status=job.status,
        reason={
            "project_id": project.id,
            "job_type": job.job_type,
            "asset_type": asset_type,
            "scene_count": len(asset_scenes),
            "silent_scene_count": len(scenes) - len(asset_scenes),
            "regenerate": regenerate,
            "targeted_regeneration": targeted_regeneration,
            "scene_ids": requested_scene_ids,
        },
    )
    return job


@transaction.atomic
def create_video_render_job(project, data, actor=None):
    if not settings.VIDEO_RENDER_ENABLED or not get_local_render_capabilities()["available"]:
        raise ValidationError("服务端尚未配置本地成片渲染程序。")

    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in ASSET_ALLOWED_STATUSES:
        raise ValidationError({"status": ["Final video can only be rendered after the storyboard is ready."]})
    if VideoGenerationJob.objects.filter(
        project=project,
        job_type__in=MEDIA_JOB_TYPES,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exists():
        raise ValidationError({"job": ["Wait for active media jobs to finish before rendering the final video."]})

    scenes = list(VideoScene.objects.select_for_update().filter(project=project).order_by("scene_no", "id"))
    if not scenes or len(scenes) > 12:
        raise ValidationError({"scenes": ["Final rendering requires between 1 and 12 storyboard scenes."]})

    ready_assets = list(
        VideoAsset.objects.select_for_update().filter(
            project=project,
            status=VideoAsset.Status.READY,
        )
    )
    visual_scene_ids = {
        asset.scene_id
        for asset in ready_assets
        if asset.scene_id and asset.asset_type in (VideoAsset.AssetType.VIDEO, VideoAsset.AssetType.IMAGE)
        and _visual_asset_is_render_approved(asset)
    }
    missing_scene_numbers = [scene.scene_no for scene in scenes if scene.id not in visual_scene_ids]
    if missing_scene_numbers:
        missing_labels = ", ".join(str(scene_no) for scene_no in missing_scene_numbers)
        raise ValidationError(
            {"visual_review": [f"分镜 {missing_labels} 缺少人工复核通过的动态镜头或静态分镜图。"]}
        )

    include_subtitles = data.get("include_subtitles", True)
    if include_subtitles and not any(
        asset.asset_type == VideoAsset.AssetType.SUBTITLE and asset.scene_id is None for asset in ready_assets
    ):
        raise ValidationError({"subtitles": ["Generate a ready subtitle file before rendering the final video."]})

    include_narration = data.get("include_narration", True)
    if include_narration:
        unverified_audio_scene_ids = {
            asset.scene_id
            for asset in ready_assets
            if asset.asset_type == VideoAsset.AssetType.AUDIO
            and asset.scene_id is not None
            and not _audio_asset_is_render_approved(asset)
        }
        unverified_scene_numbers = [
            scene.scene_no for scene in scenes if scene.id in unverified_audio_scene_ids
        ]
        if unverified_scene_numbers:
            scene_labels = ", ".join(str(scene_no) for scene_no in unverified_scene_numbers)
            raise ValidationError(
                {"audio_quality": [f"分镜 {scene_labels} 的旁白缺少通过的波形及语义确认。"]}
            )

    existing_asset = next(
        (
            asset
            for asset in ready_assets
            if asset.asset_type == VideoAsset.AssetType.FINAL_VIDEO and asset.scene_id is None
        ),
        None,
    )
    regenerate = data.get("regenerate", False)
    if existing_asset is not None and not regenerate:
        raise ValidationError({"assets": ["The final video is ready. Set regenerate to create a new version."]})
    if existing_asset is None:
        existing_asset = VideoAsset.objects.select_for_update().filter(
            project=project,
            scene__isnull=True,
            asset_type=VideoAsset.AssetType.FINAL_VIDEO,
        ).first()
    if existing_asset is None:
        VideoAsset.objects.create(
            project=project,
            scene=None,
            asset_type=VideoAsset.AssetType.FINAL_VIDEO,
            status=VideoAsset.Status.QUEUED,
            provider="local",
        )
    elif existing_asset.status != VideoAsset.Status.READY:
        existing_asset.status = VideoAsset.Status.QUEUED
        existing_asset.failure_reason = ""
        existing_asset.provider = "local"
        existing_asset.save(update_fields=["status", "failure_reason", "provider", "updated_at"])

    request_payload = {
        "regenerate": regenerate,
        "include_narration": include_narration,
        "include_subtitles": include_subtitles,
    }
    try:
        with transaction.atomic():
            job = VideoGenerationJob.objects.create(
                project=project,
                requested_by=actor if getattr(actor, "is_authenticated", False) else None,
                job_type=VideoGenerationJob.JobType.RENDER,
                status=VideoGenerationJob.Status.QUEUED,
                provider="local",
                model_name="ffmpeg",
                request_payload=request_payload,
                max_attempts=settings.VIDEO_JOB_MAX_ATTEMPTS,
            )
    except IntegrityError:
        raise ValidationError({"job": ["A final render job is already queued or running for this project."]})

    project_from_status = project.status
    project.status = VideoProject.Status.RENDERING
    project.failure_reason = ""
    project.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=actor,
        action=AuditLog.Action.CREATE,
        to_status=job.status,
        reason={
            "project_id": project.id,
            "job_type": job.job_type,
            "scene_count": len(scenes),
            **request_payload,
        },
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=project_from_status,
        to_status=project.status,
        reason={"job_id": job.id, "source": "final_render_started"},
    )
    return job


@transaction.atomic
def retry_video_generation_job(job, actor=None):
    project_id = VideoGenerationJob.objects.only("project_id").get(id=job.id).project_id
    project = VideoProject.objects.select_for_update().get(id=project_id)
    job = VideoGenerationJob.objects.select_for_update().get(id=job.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if job.status != VideoGenerationJob.Status.FAILED:
        raise ValidationError({"status": ["Only failed jobs can be retried."]})
    resuming_provider_task = job.can_resume_provider_task
    if job.attempt_count >= job.max_attempts and not resuming_provider_task:
        raise ValidationError({"attempt_count": ["This job has reached its retry limit."]})
    if job.job_type == VideoGenerationJob.JobType.AI_STORYBOARD:
        if project.status not in STORYBOARD_ALLOWED_STATUSES:
            raise ValidationError({"status": ["The video project is not ready for another AI storyboard attempt."]})
        if not get_video_ai_provider_config()["configured"]:
            raise ValidationError("服务端尚未配置 AI 分镜服务。")
    elif job.job_type in ASSET_JOB_TYPES:
        if project.status not in ASSET_ALLOWED_STATUSES:
            raise ValidationError({"status": ["The video project is not ready for another asset attempt."]})
        if not get_video_asset_provider_config(job.job_type)["configured"]:
            raise ValidationError("服务端尚未配置对应的短视频素材服务。")
        asset_type = ASSET_TYPE_BY_JOB_TYPE[job.job_type]
        retry_assets = VideoAsset.objects.filter(
            project=project,
            asset_type=asset_type,
            status__in=(VideoAsset.Status.RUNNING, VideoAsset.Status.FAILED),
        )
        requested_scene_ids = _targeted_regeneration_scene_ids(job.request_payload)
        if requested_scene_ids:
            retry_assets = retry_assets.filter(scene_id__in=requested_scene_ids)
        retry_assets.update(status=VideoAsset.Status.QUEUED, failure_reason="", updated_at=timezone.now())
    elif job.job_type == VideoGenerationJob.JobType.RENDER:
        if project.status not in ASSET_ALLOWED_STATUSES:
            raise ValidationError({"status": ["The video project is not ready for another render attempt."]})
        if not settings.VIDEO_RENDER_ENABLED or not get_local_render_capabilities()["available"]:
            raise ValidationError("服务端尚未配置本地成片渲染程序。")
        VideoAsset.objects.filter(
            project=project,
            scene__isnull=True,
            asset_type=VideoAsset.AssetType.FINAL_VIDEO,
            status__in=(VideoAsset.Status.RUNNING, VideoAsset.Status.FAILED),
        ).update(status=VideoAsset.Status.QUEUED, failure_reason="", updated_at=timezone.now())
    else:
        raise ValidationError({"job_type": ["Unsupported video generation job type."]})
    active_job_types = MEDIA_JOB_TYPES if job.job_type == VideoGenerationJob.JobType.RENDER else (job.job_type,)
    if VideoGenerationJob.objects.filter(
        project=project,
        job_type__in=active_job_types,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exclude(id=job.id).exists():
        raise ValidationError({"job": ["Another AI storyboard job is already active for this project."]})

    from_status = job.status
    previous_attempt_count = job.attempt_count
    if resuming_provider_task and job.attempt_count >= job.max_attempts:
        job.attempt_count = max(0, job.max_attempts - 1)
    job.status = VideoGenerationJob.Status.QUEUED
    job.error_message = ""
    job.started_at = None
    job.finished_at = None
    job.requested_by = actor if getattr(actor, "is_authenticated", False) else job.requested_by
    job.save(
        update_fields=[
            "status",
            "attempt_count",
            "error_message",
            "started_at",
            "finished_at",
            "requested_by",
            "updated_at",
        ]
    )
    if job.job_type == VideoGenerationJob.JobType.RENDER:
        project.status = VideoProject.Status.RENDERING
        project.failure_reason = ""
        project.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=job.status,
        reason={
            "project_id": project.id,
            "attempt_count": job.attempt_count,
            "previous_attempt_count": previous_attempt_count,
            "resuming_provider_task": resuming_provider_task,
        },
    )
    return job


def retry_ai_storyboard_job(job, actor=None):
    return retry_video_generation_job(job, actor=actor)


def recover_stale_video_generation_jobs():
    now = timezone.now()
    video_stale_seconds = max(
        settings.VIDEO_JOB_STALE_SECONDS,
        settings.VIDEO_CLIP_MAX_WAIT_SECONDS * 12 + 300,
    )
    render_stale_seconds = max(settings.VIDEO_JOB_STALE_SECONDS, settings.VIDEO_RENDER_TIMEOUT_SECONDS + 120)
    running_jobs = VideoGenerationJob.objects.filter(
        status=VideoGenerationJob.Status.RUNNING,
        started_at__isnull=False,
    ).values_list("id", "job_type", "started_at")
    recovered_count = 0
    for job_id, job_type, started_at in running_jobs:
        if job_type == VideoGenerationJob.JobType.VIDEO_CLIPS:
            stale_seconds = video_stale_seconds
        elif job_type == VideoGenerationJob.JobType.RENDER:
            stale_seconds = render_stale_seconds
        else:
            stale_seconds = settings.VIDEO_JOB_STALE_SECONDS
        stale_before = now - timedelta(seconds=stale_seconds)
        if started_at < stale_before and _recover_stale_video_generation_job(job_id, stale_before):
            recovered_count += 1
    return recovered_count


@transaction.atomic
def _recover_stale_video_generation_job(job_id, stale_before):
    job_reference = VideoGenerationJob.objects.filter(id=job_id).values("project_id").first()
    if job_reference is None:
        return False
    project = VideoProject.objects.select_for_update().get(id=job_reference["project_id"])
    job = VideoGenerationJob.objects.select_for_update().filter(
        id=job_id,
        status=VideoGenerationJob.Status.RUNNING,
        started_at__lt=stale_before,
    ).first()
    if job is None:
        return False

    from_status = job.status
    if job.job_type == VideoGenerationJob.JobType.AI_STORYBOARD and project.status == VideoProject.Status.ANALYZING:
        _fail_ai_storyboard_generation(
            project.id,
            "AI 分镜任务执行超时，已重新排队。",
            job.requested_by,
            job.model_name,
        )
    will_retry = job.attempt_count < job.max_attempts
    if job.job_type in ASSET_JOB_TYPES:
        asset_type = ASSET_TYPE_BY_JOB_TYPE[job.job_type]
        stale_assets = VideoAsset.objects.filter(
            project=project,
            asset_type=asset_type,
            status=VideoAsset.Status.RUNNING,
        )
        requested_scene_ids = _targeted_regeneration_scene_ids(job.request_payload)
        if requested_scene_ids:
            stale_assets = stale_assets.filter(scene_id__in=requested_scene_ids)
        stale_assets.update(
            status=VideoAsset.Status.QUEUED if will_retry else VideoAsset.Status.FAILED,
            failure_reason="" if will_retry else "素材任务执行超时，且已达到重试上限。",
            updated_at=timezone.now(),
        )
    if job.job_type == VideoGenerationJob.JobType.RENDER:
        VideoAsset.objects.filter(
            project=project,
            scene__isnull=True,
            asset_type=VideoAsset.AssetType.FINAL_VIDEO,
            status=VideoAsset.Status.RUNNING,
        ).update(
            status=VideoAsset.Status.QUEUED if will_retry else VideoAsset.Status.FAILED,
            failure_reason="" if will_retry else "成片渲染超时，且已达到重试上限。",
            updated_at=timezone.now(),
        )
        if not will_retry and project.status == VideoProject.Status.RENDERING:
            project.status = VideoProject.Status.STORYBOARD_READY
            project.failure_reason = "成片渲染超时，且已达到重试上限。"
            project.save(update_fields=["status", "failure_reason", "updated_at"])
    if will_retry:
        job.status = VideoGenerationJob.Status.QUEUED
        job.error_message = ""
        job.started_at = None
        job.finished_at = None
    else:
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = (
            "AI 分镜任务执行超时，且已达到重试上限。"
            if job.job_type == VideoGenerationJob.JobType.AI_STORYBOARD
            else (
                "成片渲染超时，且已达到重试上限。"
                if job.job_type == VideoGenerationJob.JobType.RENDER
                else "素材任务执行超时，且已达到重试上限。"
            )
        )
        job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "started_at", "finished_at", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=job.requested_by,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=job.status,
        reason={"project_id": job.project_id, "recovered_stale_job": True},
    )
    return True


@transaction.atomic
def claim_next_video_generation_job():
    queryset = VideoGenerationJob.objects.filter(
        status=VideoGenerationJob.Status.QUEUED,
        attempt_count__lt=F("max_attempts"),
    ).order_by("created_at", "id")
    if connection.features.has_select_for_update_skip_locked:
        queryset = queryset.select_for_update(skip_locked=True)
    else:
        queryset = queryset.select_for_update()
    job = queryset.first()
    if job is None:
        return None

    from_status = job.status
    job.status = VideoGenerationJob.Status.RUNNING
    job.attempt_count += 1
    job.started_at = timezone.now()
    job.finished_at = None
    job.error_message = ""
    job.save(update_fields=["status", "attempt_count", "started_at", "finished_at", "error_message", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=job.requested_by,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=job.status,
        reason={"project_id": job.project_id, "attempt_count": job.attempt_count},
    )
    return job


@transaction.atomic
def _finish_video_generation_job(job_id, status, error_message=""):
    job = VideoGenerationJob.objects.select_for_update().get(id=job_id)
    if job.status != VideoGenerationJob.Status.RUNNING:
        return job
    from_status = job.status
    job.status = status
    job.error_message = error_message
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=job.requested_by,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=job.status,
        reason={"project_id": job.project_id, "attempt_count": job.attempt_count, "error": error_message},
    )
    return job


@transaction.atomic
def _begin_scene_asset_processing(job, scene, asset_type):
    asset = VideoAsset.objects.select_for_update().get(
        project_id=job.project_id,
        scene_id=scene.id,
        asset_type=asset_type,
    )
    regenerate = bool(job.request_payload.get("regenerate"))
    metadata = dict(asset.metadata) if isinstance(asset.metadata, dict) else {}
    pending_provider_task = metadata.get("pending_provider_task")
    resume_provider_task_id = ""
    if (
        isinstance(pending_provider_task, dict)
        and pending_provider_task.get("job_id") == job.id
        and pending_provider_task.get("provider") == job.provider
        and pending_provider_task.get("model") == job.model_name
    ):
        candidate_task_id = str(pending_provider_task.get("task_id") or "").strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", candidate_task_id):
            resume_provider_task_id = candidate_task_id
    if pending_provider_task and not resume_provider_task_id:
        metadata.pop("pending_provider_task", None)
        asset.metadata = metadata

    if asset.status == VideoAsset.Status.READY:
        if not regenerate or metadata.get("generation_job_id") == job.id:
            if pending_provider_task and not resume_provider_task_id:
                asset.save(update_fields=["metadata", "updated_at"])
            return None
        if pending_provider_task and not resume_provider_task_id:
            asset.save(update_fields=["metadata", "updated_at"])
        return {
            "asset_id": asset.id,
            "had_ready_asset": True,
            "resume_provider_task_id": resume_provider_task_id,
        }

    asset.status = VideoAsset.Status.RUNNING
    asset.failure_reason = ""
    update_fields = ["status", "failure_reason", "updated_at"]
    if pending_provider_task and not resume_provider_task_id:
        update_fields.append("metadata")
    asset.save(update_fields=update_fields)
    return {
        "asset_id": asset.id,
        "had_ready_asset": False,
        "resume_provider_task_id": resume_provider_task_id,
    }


@transaction.atomic
def _record_scene_provider_task(asset_id, job, task_id, model):
    task_id = str(task_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id):
        raise ValidationError("短视频画面生成服务未返回有效的任务编号。")

    asset = VideoAsset.objects.select_for_update().get(id=asset_id)
    metadata = dict(asset.metadata) if isinstance(asset.metadata, dict) else {}
    metadata["pending_provider_task"] = {
        "provider": job.provider,
        "model": str(model or job.model_name),
        "job_id": job.id,
        "task_id": task_id,
        "status": "processing",
        "recorded_at": timezone.now().isoformat(),
    }
    asset.metadata = metadata
    asset.save(update_fields=["metadata", "updated_at"])
    locked_job = VideoGenerationJob.objects.select_for_update().get(id=job.id)
    request_payload = dict(locked_job.request_payload or {})
    request_payload["provider_resume_available"] = True
    locked_job.request_payload = request_payload
    locked_job.save(update_fields=["request_payload", "updated_at"])
    job.request_payload = request_payload


@transaction.atomic
def _complete_scene_asset_processing(asset_id, job, result, storage_path, file_name, metadata):
    asset = VideoAsset.objects.select_for_update().select_related("project").get(id=asset_id)
    if asset.project.deleted_at is not None:
        _schedule_video_asset_file_cleanup((storage_path,))
        raise ValidationError({"project": ["Video project has been deleted."]})

    from_status = asset.status
    previous_storage_path = asset.storage_path
    asset.status = VideoAsset.Status.READY
    asset.storage_path = storage_path
    asset.file_name = file_name
    asset.mime_type = result["mime_type"]
    asset.file_size = len(result["content"])
    asset.provider = result["provider"]
    asset.provider_asset_id = result["provider_asset_id"]
    asset.metadata = metadata
    asset.failure_reason = ""
    asset.save(
        update_fields=[
            "status",
            "storage_path",
            "file_name",
            "mime_type",
            "file_size",
            "provider",
            "provider_asset_id",
            "metadata",
            "failure_reason",
            "updated_at",
        ]
    )
    locked_job = VideoGenerationJob.objects.select_for_update().get(id=job.id)
    request_payload = dict(locked_job.request_payload or {})
    if request_payload.pop("provider_resume_available", None) is not None:
        locked_job.request_payload = request_payload
        locked_job.save(update_fields=["request_payload", "updated_at"])
        job.request_payload = request_payload
    if previous_storage_path and previous_storage_path != storage_path:
        _schedule_video_asset_file_cleanup(
            _asset_related_storage_paths(asset.asset_type, previous_storage_path)
        )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=asset.project_id,
        actor=job.requested_by,
        action=AuditLog.Action.UPDATE,
        from_status=from_status,
        to_status=asset.status,
        reason={
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "scene_id": asset.scene_id,
            "job_id": job.id,
            "model": result["model"],
            "file_size": asset.file_size,
            **(
                {
                    "audio_quality_status": (metadata.get("audio_quality") or {}).get("status"),
                    "speech_quality_status": (metadata.get("speech_quality") or {}).get("status"),
                    "asr_model": (metadata.get("speech_quality") or {}).get("model") or "",
                }
                if asset.asset_type == VideoAsset.AssetType.AUDIO
                else {}
            ),
        },
    )
    _mark_project_final_video_stale(asset.project, job.requested_by, "scene_asset_replaced")
    return asset


@transaction.atomic
def _fail_scene_asset_processing(asset_id, job, error_message, had_ready_asset):
    asset = VideoAsset.objects.select_for_update().filter(id=asset_id).first()
    if asset is None:
        return
    from_status = asset.status
    if had_ready_asset and asset.status == VideoAsset.Status.READY:
        metadata = dict(asset.metadata or {})
        metadata["last_failed_job_id"] = job.id
        asset.metadata = metadata
        asset.save(update_fields=["metadata", "updated_at"])
    else:
        asset.status = VideoAsset.Status.FAILED
        asset.failure_reason = error_message
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=asset.project_id,
        actor=job.requested_by,
        action=AuditLog.Action.UPDATE,
        from_status=from_status,
        to_status=asset.status,
        reason={
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "scene_id": asset.scene_id,
            "job_id": job.id,
            "event": "asset_generation_failed",
            "preserved_previous_asset": had_ready_asset,
            "error": error_message,
        },
    )


def _build_project_render_inputs(project, job):
    scenes = list(VideoScene.objects.filter(project=project).order_by("scene_no", "id"))
    ready_assets = list(
        VideoAsset.objects.filter(project=project, status=VideoAsset.Status.READY).order_by("scene_id", "id")
    )
    assets_by_scene = {}
    for asset in ready_assets:
        if asset.scene_id:
            assets_by_scene.setdefault(asset.scene_id, {})[asset.asset_type] = asset

    include_narration = job.request_payload.get("include_narration", True)
    render_inputs = []
    for scene in scenes:
        scene_assets = assets_by_scene.get(scene.id, {})
        video_asset = scene_assets.get(VideoAsset.AssetType.VIDEO)
        image_asset = scene_assets.get(VideoAsset.AssetType.IMAGE)
        visual_asset = (
            video_asset
            if video_asset is not None and _visual_asset_is_render_approved(video_asset)
            else (
                image_asset
                if image_asset is not None and _visual_asset_is_render_approved(image_asset)
                else None
            )
        )
        if visual_asset is None:
            raise ValidationError(
                {"visual_review": [f"分镜 {scene.scene_no} 缺少人工复核通过的画面素材。"]}
            )
        visual_path = _resolve_media_path(visual_asset.storage_path)
        if not visual_path.is_file():
            raise ValidationError({"assets": [f"Scene {scene.scene_no} visual file is missing."]})

        narration_path = None
        narration_asset = scene_assets.get(VideoAsset.AssetType.AUDIO) if include_narration else None
        if narration_asset is not None:
            if not _audio_asset_is_render_approved(narration_asset):
                raise ValidationError(
                    {"audio_quality": [f"分镜 {scene.scene_no} 的旁白未通过波形及语义确认。"]}
                )
            narration_path = _resolve_media_path(narration_asset.storage_path)
            if not narration_path.is_file():
                narration_path = None
        render_inputs.append(
            SceneRenderInput(
                scene_no=scene.scene_no,
                duration_seconds=scene.duration_seconds,
                visual_path=visual_path,
                visual_type=visual_asset.asset_type,
                narration_path=narration_path,
            )
        )

    subtitle_path = None
    if job.request_payload.get("include_subtitles", True):
        subtitle_asset = next(
            (
                asset
                for asset in ready_assets
                if asset.scene_id is None and asset.asset_type == VideoAsset.AssetType.SUBTITLE
            ),
            None,
        )
        if subtitle_asset is None:
            raise ValidationError({"subtitles": ["The ready subtitle file is missing."]})
        subtitle_path = _resolve_media_path(subtitle_asset.storage_path)
        if not subtitle_path.is_file():
            raise ValidationError({"subtitles": ["The ready subtitle file is missing."]})
    return render_inputs, subtitle_path


@transaction.atomic
def _begin_project_render_processing(job):
    asset = VideoAsset.objects.select_for_update().get(
        project_id=job.project_id,
        scene__isnull=True,
        asset_type=VideoAsset.AssetType.FINAL_VIDEO,
    )
    metadata = asset.metadata or {}
    if asset.status == VideoAsset.Status.READY and metadata.get("generation_job_id") == job.id:
        return None

    previous_status = asset.status if asset.storage_path else None
    if asset.status != VideoAsset.Status.READY:
        asset.status = VideoAsset.Status.RUNNING
        asset.failure_reason = ""
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
    return {"asset_id": asset.id, "previous_status": previous_status}


@transaction.atomic
def _complete_project_render_processing(asset_id, job, storage_path, file_name, metadata):
    asset = VideoAsset.objects.select_for_update().select_related("project").get(id=asset_id)
    project = asset.project
    if project.deleted_at is not None:
        _schedule_video_asset_file_cleanup((storage_path,))
        raise ValidationError({"project": ["Video project has been deleted."]})

    asset_from_status = asset.status
    previous_storage_path = asset.storage_path
    asset.status = VideoAsset.Status.READY
    asset.storage_path = storage_path
    asset.file_name = file_name
    asset.mime_type = "video/mp4"
    asset.file_size = metadata["file_size"]
    asset.provider = "local"
    asset.provider_asset_id = f"render-job-{job.id}"
    asset.metadata = metadata
    asset.failure_reason = ""
    asset.save(
        update_fields=[
            "status",
            "storage_path",
            "file_name",
            "mime_type",
            "file_size",
            "provider",
            "provider_asset_id",
            "metadata",
            "failure_reason",
            "updated_at",
        ]
    )
    if previous_storage_path and previous_storage_path != storage_path:
        _schedule_video_asset_file_cleanup((previous_storage_path,))

    project_from_status = project.status
    project.status = VideoProject.Status.COMPLETED
    project.failure_reason = ""
    project.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=job.requested_by,
        action=AuditLog.Action.UPDATE,
        from_status=asset_from_status,
        to_status=asset.status,
        reason={
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "job_id": job.id,
            "engine": "ffmpeg",
            "file_size": asset.file_size,
            "scene_count": metadata["scene_count"],
        },
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=job.requested_by,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=project_from_status,
        to_status=project.status,
        reason={"job_id": job.id, "source": "final_render_completed"},
    )
    return asset


@transaction.atomic
def _fail_project_render_processing(asset_id, job, error_message, previous_status, storage_path=""):
    asset = VideoAsset.objects.select_for_update().select_related("project").filter(id=asset_id).first()
    if asset is None:
        _schedule_video_asset_file_cleanup((storage_path,))
        return
    project = asset.project
    asset_from_status = asset.status
    if previous_status == VideoAsset.Status.READY and asset.storage_path:
        metadata = dict(asset.metadata or {})
        metadata["last_failed_job_id"] = job.id
        asset.metadata = metadata
        asset.save(update_fields=["metadata", "updated_at"])
    elif previous_status == VideoAsset.Status.STALE and asset.storage_path:
        asset.status = VideoAsset.Status.STALE
        asset.failure_reason = f"原成片已过期，重新渲染失败：{error_message}"
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
    else:
        asset.status = VideoAsset.Status.FAILED
        asset.failure_reason = error_message
        asset.save(update_fields=["status", "failure_reason", "updated_at"])
    _schedule_video_asset_file_cleanup((storage_path,))

    project_from_status = project.status
    if project.status == VideoProject.Status.RENDERING:
        project.status = VideoProject.Status.STORYBOARD_READY
    project.failure_reason = error_message
    project.save(update_fields=["status", "failure_reason", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=job.requested_by,
        action=AuditLog.Action.UPDATE,
        from_status=asset_from_status,
        to_status=asset.status,
        reason={
            "asset_id": asset.id,
            "asset_type": asset.asset_type,
            "job_id": job.id,
            "event": "final_render_failed",
            "preserved_previous_asset": previous_status in (VideoAsset.Status.READY, VideoAsset.Status.STALE),
            "error": error_message,
        },
    )
    if project_from_status != project.status:
        create_operation_audit_log(
            content_type=AuditLog.ContentType.VIDEO_PROJECT,
            object_id=project.id,
            actor=job.requested_by,
            action=AuditLog.Action.STATUS_UPDATE,
            from_status=project_from_status,
            to_status=project.status,
            reason={"job_id": job.id, "source": "final_render_failed"},
        )


def _process_video_render_job(job):
    project = VideoProject.objects.get(id=job.project_id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status != VideoProject.Status.RENDERING:
        raise ValidationError({"status": ["Video project is not ready for final rendering."]})

    processing = _begin_project_render_processing(job)
    if processing is None:
        return
    storage_path = Path(
        "video_projects",
        str(project.id),
        "renders",
        f"final-job-{job.id}.mp4",
    ).as_posix()
    try:
        render_inputs, subtitle_path = _build_project_render_inputs(project, job)
        metadata = render_video_project(
            render_inputs,
            subtitle_path,
            _resolve_media_path(storage_path),
            width=settings.VIDEO_RENDER_WIDTH,
            height=settings.VIDEO_RENDER_HEIGHT,
            fps=settings.VIDEO_RENDER_FPS,
            crf=settings.VIDEO_RENDER_CRF,
            timeout_seconds=settings.VIDEO_RENDER_TIMEOUT_SECONDS,
            max_file_bytes=settings.VIDEO_RENDER_MAX_FILE_BYTES,
        )
        metadata.update({"engine": "ffmpeg", "generation_job_id": job.id})
        _complete_project_render_processing(
            processing["asset_id"],
            job,
            storage_path,
            f"video-project-{project.id}-final.mp4",
            metadata,
        )
    except VideoRenderError as error:
        error_message = str(error)
        _fail_project_render_processing(
            processing["asset_id"],
            job,
            error_message,
            processing["previous_status"],
            storage_path,
        )
        raise ValidationError(error_message)
    except ValidationError as error:
        error_message = _validation_error_message(error)
        _fail_project_render_processing(
            processing["asset_id"],
            job,
            error_message,
            processing["previous_status"],
            storage_path,
        )
        raise
    except Exception:
        logger.exception("Final video render failed for job %s.", job.id)
        error_message = "本地成片文件处理失败，请稍后重试。"
        _fail_project_render_processing(
            processing["asset_id"],
            job,
            error_message,
            processing["previous_status"],
            storage_path,
        )
        raise ValidationError(error_message)


def _process_video_asset_job(job):
    if job.job_type not in ASSET_JOB_TYPES:
        raise ValidationError("Unsupported video asset job type.")
    project = VideoProject.objects.get(id=job.project_id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status != VideoProject.Status.STORYBOARD_READY:
        raise ValidationError({"status": ["Video project is not ready for asset generation."]})

    requested_scene_ids = _targeted_regeneration_scene_ids(job.request_payload)
    scene_queryset = VideoScene.objects.filter(project=project)
    if requested_scene_ids:
        scene_queryset = scene_queryset.filter(id__in=requested_scene_ids)
    scenes = list(scene_queryset.order_by("scene_no", "id"))
    if not scenes or len(scenes) > 12:
        raise ValidationError({"scenes": ["Asset jobs require between 1 and 12 storyboard scenes."]})
    if requested_scene_ids and len(scenes) != len(requested_scene_ids):
        raise ValidationError({"scenes": ["局部重生成任务包含已不存在的分镜。"]})
    asset_type = ASSET_TYPE_BY_JOB_TYPE[job.job_type]

    for scene in scenes:
        if not _scene_requires_asset(job.job_type, scene):
            continue
        processing = _begin_scene_asset_processing(job, scene, asset_type)
        if processing is None:
            continue
        storage_path = ""
        try:
            result = _call_scene_asset_provider(job, scene, processing)
            audio_quality = None
            speech_quality = None
            if asset_type == VideoAsset.AssetType.AUDIO:
                audio_quality = analyze_wav_audio(result["content"], scene.duration_seconds)
                if audio_quality["status"] != "passed":
                    error_messages = [
                        issue["message"]
                        for issue in audio_quality["issues"]
                        if issue["severity"] == "error"
                    ]
                    raise ValidationError(
                        {"audio_quality": error_messages or ["旁白音频未通过质量检查，请重新生成。"]}
                    )
                speech_quality = _build_scene_speech_quality(
                    scene,
                    result["content"],
                    audio_quality,
                    job,
                )
            file_name = f"scene-{scene.scene_no:02d}{result['extension']}"
            storage_path = Path(
                "video_projects",
                str(project.id),
                "scenes",
                f"scene-{scene.scene_no:02d}",
                f"{asset_type}-job-{job.id}{result['extension']}",
            ).as_posix()
            _write_video_asset_file(storage_path, result["content"])
            content_sha256 = hashlib.sha256(result["content"]).hexdigest()
            metadata = {
                **result["metadata"],
                "model": result["model"],
                "scene_no": scene.scene_no,
                "generation_job_id": job.id,
                "sha256": content_sha256,
            }
            if asset_type == VideoAsset.AssetType.VIDEO:
                metadata["tail_frame"] = _extract_and_store_video_tail_frame(
                    scene,
                    storage_path,
                    content_sha256,
                )
            if audio_quality is not None:
                audio_metrics = audio_quality["metrics"]
                metadata.update(
                    {
                        "sample_rate": audio_metrics.get("sample_rate", 0),
                        "channels": audio_metrics.get("channels", 0),
                        "duration_seconds": audio_metrics.get("duration_seconds", 0),
                        "audio_quality": audio_quality,
                        "speech_quality": speech_quality,
                    }
                )
            _complete_scene_asset_processing(
                processing["asset_id"],
                job,
                result,
                storage_path,
                file_name,
                metadata,
            )
        except ValidationError as error:
            if storage_path:
                _delete_video_asset_files(_asset_related_storage_paths(asset_type, storage_path))
            error_message = _validation_error_message(error)
            _fail_scene_asset_processing(
                processing["asset_id"],
                job,
                error_message,
                processing["had_ready_asset"],
            )
            raise
        except Exception:
            if storage_path:
                _delete_video_asset_files(_asset_related_storage_paths(asset_type, storage_path))
            logger.exception(
                "Video asset processing failed for job %s scene %s.",
                job.id,
                scene.id,
            )
            error_message = "素材文件处理失败，请稍后重试。"
            _fail_scene_asset_processing(
                processing["asset_id"],
                job,
                error_message,
                processing["had_ready_asset"],
            )
            raise ValidationError(error_message)


def process_video_generation_job(job):
    try:
        if job.job_type == VideoGenerationJob.JobType.AI_STORYBOARD:
            generate_ai_storyboard_for_project(job.project, job.request_payload, actor=job.requested_by)
        elif job.job_type in ASSET_JOB_TYPES:
            _process_video_asset_job(job)
        elif job.job_type == VideoGenerationJob.JobType.RENDER:
            _process_video_render_job(job)
        else:
            raise ValidationError("Unsupported video generation job type.")
    except ValidationError as error:
        return _finish_video_generation_job(job.id, VideoGenerationJob.Status.FAILED, _validation_error_message(error))
    except Exception:
        error_message = (
            "AI 分镜任务执行失败，请稍后重试。"
            if job.job_type == VideoGenerationJob.JobType.AI_STORYBOARD
            else (
                "成片渲染任务执行失败，请稍后重试。"
                if job.job_type == VideoGenerationJob.JobType.RENDER
                else "短视频素材任务执行失败，请稍后重试。"
            )
        )
        return _finish_video_generation_job(job.id, VideoGenerationJob.Status.FAILED, error_message)
    return _finish_video_generation_job(job.id, VideoGenerationJob.Status.SUCCEEDED)


@transaction.atomic
def update_video_scene(project, scene, data, actor=None):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    scene = VideoScene.objects.select_for_update().get(id=scene.id, project=project)

    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_EDITABLE_STATUSES:
        raise ValidationError({"status": ["Scenes can only be edited after the storyboard is ready."]})
    _ensure_no_active_asset_jobs(project)

    if "duration_seconds" in data:
        current_total = sum(
            VideoScene.objects.filter(project=project).values_list("duration_seconds", flat=True)
        )
        next_total = current_total - scene.duration_seconds + data["duration_seconds"]
        if next_total < 30 or next_total > 90:
            raise ValidationError({"duration_seconds": ["Total storyboard duration must remain between 30 and 90 seconds."]})
        project.duration_target = next_total
        project.save(update_fields=["duration_target", "updated_at"])

    from_status = scene.status
    changed_fields = []
    for field_name, value in data.items():
        if getattr(scene, field_name) == value:
            continue
        setattr(scene, field_name, value)
        changed_fields.append(field_name)

    if scene.status != VideoScene.Status.READY:
        scene.status = VideoScene.Status.READY
        changed_fields.append("status")
    if scene.failure_reason:
        scene.failure_reason = ""
        changed_fields.append("failure_reason")

    if changed_fields:
        edited_fields = set(changed_fields)
        if scene.agent_metadata:
            scene.agent_metadata = {
                **scene.agent_metadata,
                "stale": True,
                "stale_reason": "scene_updated",
            }
            if IMAGE_SOURCE_FIELDS.intersection(edited_fields):
                scene.agent_metadata.pop("prompt_adapter", None)
            if AUDIO_SOURCE_FIELDS.intersection(edited_fields):
                scene.agent_metadata.pop("audio_script", None)
            changed_fields.append("agent_metadata")
        scene.save(update_fields=[*changed_fields, "updated_at"])
        if project.agent_workflow:
            project.agent_workflow = mark_workflow_stale(project.agent_workflow, "scene_updated")
            project.save(update_fields=["agent_workflow", "updated_at"])
        if SUBTITLE_SOURCE_FIELDS.intersection(changed_fields):
            _mark_project_subtitle_assets_stale(project, actor, "scene_updated")
        _mark_scene_assets_stale(project, scene, changed_fields, actor)
        _mark_project_final_video_stale(project, actor, "scene_updated")

    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_SCENE,
        object_id=scene.id,
        actor=actor,
        action=AuditLog.Action.UPDATE,
        from_status=from_status,
        to_status=scene.status,
        reason={
            "project_id": project.id,
            "scene_no": scene.scene_no,
            "changed_fields": changed_fields,
        },
    )
    return scene


@transaction.atomic
def soft_delete_video_project(project, actor=None):
    if project.deleted_at is not None:
        return project

    assets = list(VideoAsset.objects.select_for_update().filter(project=project))
    _schedule_video_asset_file_cleanup(
        storage_path
        for asset in assets
        for storage_path in _asset_related_storage_paths(asset.asset_type, asset.storage_path)
    )
    for asset in assets:
        asset.status = VideoAsset.Status.STALE
        asset.failure_reason = "项目已删除，素材文件已安排清理。"
        asset.save(update_fields=["status", "failure_reason", "updated_at"])

    active_jobs = list(
        VideoGenerationJob.objects.select_for_update().filter(
            project=project,
            status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
        )
    )
    for job in active_jobs:
        job_from_status = job.status
        job.status = VideoGenerationJob.Status.CANCELED
        job.error_message = "Video project was deleted."
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.VIDEO_JOB,
            object_id=job.id,
            actor=actor,
            action=AuditLog.Action.STATUS_UPDATE,
            from_status=job_from_status,
            to_status=job.status,
            reason={"project_id": project.id, "source": "project_deleted"},
        )

    from_status = project.status
    project.mark_deleted()
    project.save(update_fields=["status", "deleted_at", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.DELETE,
        from_status=from_status,
        to_status=project.status,
    )
    return project
