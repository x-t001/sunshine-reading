import hashlib
import math
import re
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log

from .models import VideoGenerationJob, VideoProject, VideoScene
from .providers import call_video_ai_storyboard, get_video_ai_capabilities, get_video_ai_provider_config
from .serializers import UNSAFE_TEXT_PATTERNS, VideoAiStoryboardResultSerializer


STORYBOARD_ALLOWED_STATUSES = (
    VideoProject.Status.DRAFT,
    VideoProject.Status.FAILED,
    VideoProject.Status.STORYBOARD_READY,
)
STORYBOARD_EDITABLE_STATUSES = (VideoProject.Status.STORYBOARD_READY,)
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


def get_video_generation_capabilities():
    return get_video_ai_capabilities()


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
        return 4
    if duration_target <= 45:
        return 5
    if duration_target <= 60:
        return 6
    return 8


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
    source_text = (chapter.content or "").strip()
    if len(source_text) < 100:
        raise ValidationError({"chapter_id": ["Chapter content must contain at least 100 characters."]})
    for pattern in UNSAFE_TEXT_PATTERNS:
        if pattern.search(source_text):
            raise ValidationError({"chapter_id": ["Chapter content contains unsafe HTML or script content."]})

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
def generate_storyboard_for_project(project, data, actor=None):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_ALLOWED_STATUSES:
        raise ValidationError({"status": ["Storyboard can only be generated from draft, failed, or storyboard-ready projects."]})

    story_text = _normalize_story_text(project.input_text)
    if not story_text:
        raise ValidationError({"input_text": ["Text-sourced video project has no input text."]})

    scene_count = data.get("scene_count") or _default_scene_count(project.duration_target)
    units = _split_story_units(story_text)
    chunks = _chunk_units(units, scene_count)
    durations = _scene_durations(project.duration_target, scene_count)

    from_status = project.status
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
    project.save(update_fields=["summary", "status", "failure_reason", "updated_at"])
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


def _validation_error_message(error):
    detail = getattr(error, "detail", error)
    if isinstance(detail, dict):
        for value in detail.values():
            return _validation_error_message(value)
    if isinstance(detail, (list, tuple)):
        return _validation_error_message(detail[0]) if detail else "AI storyboard generation failed."
    return str(detail)[:500]


@transaction.atomic
def _begin_ai_storyboard_generation(project, actor, model):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_ALLOWED_STATUSES:
        raise ValidationError({"status": ["AI storyboard can only be generated from draft, failed, or storyboard-ready projects."]})
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
            status=VideoScene.Status.READY,
        )

    project.summary = storyboard.get("summary") or _story_summary(project.input_text)
    project.status = VideoProject.Status.STORYBOARD_READY
    project.failure_reason = ""
    project.save(update_fields=["summary", "status", "failure_reason", "updated_at"])
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
            context={"expected_scene_count": scene_count},
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
def retry_ai_storyboard_job(job, actor=None):
    project_id = VideoGenerationJob.objects.only("project_id").get(id=job.id).project_id
    project = VideoProject.objects.select_for_update().get(id=project_id)
    job = VideoGenerationJob.objects.select_for_update().get(id=job.id)
    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if job.status != VideoGenerationJob.Status.FAILED:
        raise ValidationError({"status": ["Only failed jobs can be retried."]})
    if job.attempt_count >= job.max_attempts:
        raise ValidationError({"attempt_count": ["This job has reached its retry limit."]})
    if project.status not in STORYBOARD_ALLOWED_STATUSES:
        raise ValidationError({"status": ["The video project is not ready for another AI storyboard attempt."]})
    if not get_video_ai_provider_config()["configured"]:
        raise ValidationError("服务端尚未配置 AI 分镜服务。")
    if VideoGenerationJob.objects.filter(
        project=project,
        job_type=job.job_type,
        status__in=(VideoGenerationJob.Status.QUEUED, VideoGenerationJob.Status.RUNNING),
    ).exclude(id=job.id).exists():
        raise ValidationError({"job": ["Another AI storyboard job is already active for this project."]})

    from_status = job.status
    job.status = VideoGenerationJob.Status.QUEUED
    job.error_message = ""
    job.started_at = None
    job.finished_at = None
    job.requested_by = actor if getattr(actor, "is_authenticated", False) else job.requested_by
    job.save(update_fields=["status", "error_message", "started_at", "finished_at", "requested_by", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_JOB,
        object_id=job.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=from_status,
        to_status=job.status,
        reason={"project_id": project.id, "attempt_count": job.attempt_count},
    )
    return job


def recover_stale_video_generation_jobs():
    stale_before = timezone.now() - timedelta(seconds=settings.VIDEO_JOB_STALE_SECONDS)
    stale_job_ids = list(VideoGenerationJob.objects.filter(
        status=VideoGenerationJob.Status.RUNNING,
        started_at__lt=stale_before,
    ).values_list("id", flat=True))
    return sum(1 for job_id in stale_job_ids if _recover_stale_video_generation_job(job_id, stale_before))


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
    if project.status == VideoProject.Status.ANALYZING:
        _fail_ai_storyboard_generation(
            project.id,
            "AI 分镜任务执行超时，已重新排队。",
            job.requested_by,
            job.model_name,
        )
    if job.attempt_count < job.max_attempts:
        job.status = VideoGenerationJob.Status.QUEUED
        job.error_message = ""
        job.started_at = None
        job.finished_at = None
    else:
        job.status = VideoGenerationJob.Status.FAILED
        job.error_message = "AI 分镜任务执行超时，且已达到重试上限。"
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


def process_video_generation_job(job):
    try:
        if job.job_type != VideoGenerationJob.JobType.AI_STORYBOARD:
            raise ValidationError("Unsupported video generation job type.")
        generate_ai_storyboard_for_project(job.project, job.request_payload, actor=job.requested_by)
    except ValidationError as error:
        return _finish_video_generation_job(job.id, VideoGenerationJob.Status.FAILED, _validation_error_message(error))
    except Exception:
        return _finish_video_generation_job(job.id, VideoGenerationJob.Status.FAILED, "AI 分镜任务执行失败，请稍后重试。")
    return _finish_video_generation_job(job.id, VideoGenerationJob.Status.SUCCEEDED)


@transaction.atomic
def update_video_scene(project, scene, data, actor=None):
    project = VideoProject.objects.select_for_update().get(id=project.id)
    scene = VideoScene.objects.select_for_update().get(id=scene.id, project=project)

    if project.deleted_at is not None:
        raise ValidationError({"project": ["Video project has been deleted."]})
    if project.status not in STORYBOARD_EDITABLE_STATUSES:
        raise ValidationError({"status": ["Scenes can only be edited after the storyboard is ready."]})

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
        scene.save(update_fields=[*changed_fields, "updated_at"])

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
