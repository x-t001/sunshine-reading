import base64
import hashlib
import ipaddress
import json
import re
import socket
import ssl
import time
from copy import deepcopy
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings
from rest_framework.exceptions import ValidationError

from .agent_workflow import (
    WORKFLOW_VERSION,
    build_visual_world_model,
    merge_production_plan_repair_reports,
    repair_production_plan,
)


IMAGE_JOB_TYPE = "image_assets"
VIDEO_JOB_TYPE = "video_clips"
AUDIO_JOB_TYPE = "narration_audio"
SHOT_DIRECTOR_BATCH_SIZE = 6
IMAGE_MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
VIDEO_REFERENCE_IMAGE_MIME_TYPES = ("image/jpeg", "image/png")
VIDEO_MIME_EXTENSIONS = {
    "video/mp4": ".mp4",
}
COGVIDEOX_3_SIZES = {
    "1280x720",
    "720x1280",
    "1024x1024",
    "1920x1080",
    "1080x1920",
    "2048x1080",
    "3840x2160",
}
COGVIDEOX_LEGACY_SIZES = {
    "720x480",
    "1024x1024",
    "1280x960",
    "960x1280",
    "1920x1080",
    "1080x1920",
    "2048x1080",
    "3840x2160",
}
GLM_ERROR_MESSAGES = {
    "1113": "GLM 账户已欠费，请充值后重试。",
    "1210": "GLM 调用参数有误，请检查当前模型的接口契约。",
    "1211": "GLM 模型不存在，请检查模型编码。",
    "1212": "当前 GLM 模型不支持此调用方式。",
    "1213": "GLM 请求缺少必填字段。",
    "1214": "GLM 请求字段取值不合法，请检查当前模型支持的分辨率、帧率和参数组合。",
    "1215": "GLM 请求包含不能同时设置的字段，请检查当前模型的接口契约。",
    "1301": "GLM 内容安全策略拦截了当前分镜提示词或生成结果，请调整画面描述后重试。",
    "1302": "GLM 账户已达到速率限制，请稍后再试。",
    "1305": "GLM 当前访问量过大，请稍后再试。",
    "1308": "GLM 使用额度已达上限，请在额度重置后重试。",
    "1309": "GLM 套餐已到期，请续订或改用标准 API Key。",
    "1310": "GLM 周期使用额度已达上限，请在额度重置后重试。",
    "1311": "当前 GLM 套餐尚未开放该模型权限。",
    "1313": "GLM 账户因公平使用策略受到频率限制，请检查账户状态。",
    "1314": "GLM 企业套餐已失效，请联系企业管理员。",
    "1315": "当前 API Key 类型不支持此调用，请更换标准开放平台 API Key。",
    "1316": "GLM 使用额度已达上限且账户余额不足，请充值或等待额度重置。",
    "1317": "GLM 使用额度已达上限且账户余额不足，请充值或等待额度重置。",
    "1318": "GLM 使用额度或子账号消费额度已达上限，请联系管理员。",
    "1319": "GLM 使用额度或子账号消费额度已达上限，请联系管理员。",
    "1320": "GLM 使用额度或企业消费额度已达上限，请联系管理员。",
    "1321": "GLM 使用额度或企业消费额度已达上限，请联系管理员。",
}
VIDEO_CLIP_PROMPT_PREFIX = "影视化故事演绎，非血腥历史动作场面，无人员受伤特写，适合全年龄观看。"
VIDEO_CLIP_PROMPT_REPLACEMENTS = (
    ("无数箭矢扎入草人身中", "密集羽箭穿过雾气，钉在无生命的草束表面"),
    ("箭矢刺入草人", "羽箭钉在无生命的草束表面"),
    ("弓弩手放箭", "守军朝无人船阵齐射"),
    ("面色阴沉", "神情严肃"),
    ("突然擂鼓呐喊", "战鼓骤响，士兵齐声呼喊"),
    ("声震江面", "声响回荡在江面"),
    ("密谋", "商议"),
    ("阴谋", "谋略"),
    ("突袭", "雾中快速逼近"),
    ("弓弩手", "守军射手"),
    ("放箭", "齐射"),
    ("箭矢", "羽箭"),
    ("刺入", "钉在无生命的草束表面"),
    ("扎入", "钉在无生命的草束表面"),
    ("呐喊", "齐声呼喊"),
)


def get_video_ai_provider_config():
    api_url = settings.VIDEO_AI_API_URL
    api_key = settings.VIDEO_AI_API_KEY
    model = settings.VIDEO_AI_MODEL
    parsed_url = urlparse(api_url)
    configured = bool(api_key and model and parsed_url.scheme == "https" and parsed_url.netloc)
    return {
        "configured": configured,
        "api_url": api_url,
        "api_key": api_key,
        "model": model,
        "timeout_seconds": settings.VIDEO_AI_TIMEOUT_SECONDS,
        "planning_timeout_seconds": settings.VIDEO_AI_PLANNING_TIMEOUT_SECONDS,
        "directing_timeout_seconds": settings.VIDEO_AI_DIRECTING_TIMEOUT_SECONDS,
        "thinking_type": settings.VIDEO_AI_THINKING_TYPE,
    }


def get_video_ai_capabilities():
    config = get_video_ai_provider_config()
    image_config = get_video_asset_provider_config(IMAGE_JOB_TYPE)
    video_config = get_video_asset_provider_config(VIDEO_JOB_TYPE)
    audio_config = get_video_asset_provider_config(AUDIO_JOB_TYPE)
    asr_config = get_video_audio_transcription_config()
    return {
        "ai_storyboard_configured": config["configured"],
        "ai_storyboard_model": config["model"] if config["configured"] else "",
        "ai_agent_workflow_available": True,
        "ai_agent_workflow_version": WORKFLOW_VERSION,
        "local_storyboard_available": True,
        "durable_storyboard_jobs_available": True,
        "asset_jobs_available": True,
        "image_assets_configured": image_config["configured"],
        "image_assets_model": image_config["model"] if image_config["configured"] else "",
        "image_assets_size": image_config["size"],
        "image_assets_continuity_workflow": True,
        "image_assets_reference_mode": "text_only_canonical_anchors",
        "image_assets_visual_review_mode": "manual_required",
        "image_assets_daily_job_limit": settings.VIDEO_IMAGE_DAILY_JOB_LIMIT,
        "visual_review_available": True,
        "visual_regeneration_daily_scene_limit": settings.VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT,
        "visual_regeneration_per_scene_limit": settings.VIDEO_VISUAL_REGENERATION_PER_SCENE_LIMIT,
        "video_clips_configured": video_config["configured"],
        "video_clips_model": video_config["model"] if video_config["configured"] else "",
        "video_clips_size": video_config["size"],
        "video_clips_duration_seconds": video_config["duration_seconds"],
        "video_clips_fps": video_config["fps"],
        "video_clips_with_audio": video_config["with_audio"],
        "video_clips_reference_frame_enabled": video_config["use_scene_image"],
        "video_clips_previous_tail_frame_enabled": settings.VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME,
        "video_clips_reference_frame_mode": (
            "previous_tail_then_scene_image_base64"
            if settings.VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME and video_config["use_scene_image"]
            else (
                "previous_tail_base64"
                if settings.VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME
                else ("scene_image_base64" if video_config["use_scene_image"] else "disabled")
            )
        ),
        "video_clips_daily_job_limit": settings.VIDEO_CLIP_DAILY_JOB_LIMIT,
        "narration_audio_configured": audio_config["configured"],
        "narration_audio_model": audio_config["model"] if audio_config["configured"] else "",
        "narration_audio_voice": audio_config["voice"],
        "narration_audio_quality_gate": True,
        "narration_audio_asr_configured": asr_config["configured"],
        "narration_audio_asr_model": asr_config["model"] if asr_config["configured"] else "",
        "narration_audio_asr_min_similarity": asr_config["minimum_similarity"],
        "narration_audio_manual_review": True,
        "narration_audio_daily_job_limit": settings.VIDEO_TTS_DAILY_JOB_LIMIT,
    }


def _is_valid_https_url(value):
    parsed_url = urlparse(value)
    if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        return False
    try:
        address = ipaddress.ip_address(parsed_url.hostname)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved)


def get_video_audio_transcription_config():
    api_url = settings.VIDEO_ASR_API_URL
    api_key = settings.VIDEO_ASR_API_KEY
    model = settings.VIDEO_ASR_MODEL
    return {
        "configured": bool(
            settings.VIDEO_ASR_ENABLED
            and api_key
            and re.fullmatch(r"[A-Za-z0-9._-]{1,120}", model)
            and _is_valid_https_url(api_url)
        ),
        "api_url": api_url,
        "api_key": api_key,
        "model": model,
        "timeout_seconds": settings.VIDEO_ASR_TIMEOUT_SECONDS,
        "minimum_similarity": settings.VIDEO_ASR_MIN_SIMILARITY,
        "max_file_bytes": min(25 * 1024 * 1024, settings.VIDEO_ASSET_MAX_FILE_BYTES),
    }


def get_video_asset_provider_config(job_type):
    if job_type == IMAGE_JOB_TYPE:
        api_url = settings.VIDEO_IMAGE_API_URL
        api_key = settings.VIDEO_IMAGE_API_KEY
        model = settings.VIDEO_IMAGE_MODEL
        return {
            "asset_type": "image",
            "provider": "glm",
            "configured": bool(api_key and model and _is_valid_https_url(api_url)),
            "api_url": api_url,
            "api_key": api_key,
            "model": model,
            "size": settings.VIDEO_IMAGE_SIZE,
            "timeout_seconds": settings.VIDEO_IMAGE_TIMEOUT_SECONDS,
            "max_file_bytes": settings.VIDEO_ASSET_MAX_FILE_BYTES,
            "daily_job_limit": settings.VIDEO_IMAGE_DAILY_JOB_LIMIT,
        }
    if job_type == VIDEO_JOB_TYPE:
        api_url = settings.VIDEO_CLIP_API_URL
        result_api_url = settings.VIDEO_CLIP_RESULT_API_URL
        api_key = settings.VIDEO_CLIP_API_KEY
        model = settings.VIDEO_CLIP_MODEL
        size = settings.VIDEO_CLIP_SIZE
        supports_duration = model == "cogvideox-3"
        allowed_sizes = (
            COGVIDEOX_3_SIZES
            if supports_duration
            else COGVIDEOX_LEGACY_SIZES if model in {"cogvideox-2", "cogvideox-flash"} else set()
        )
        result_probe_url = result_api_url.replace("{task_id}", "probe")
        return {
            "asset_type": "video",
            "provider": "glm",
            "configured": bool(
                api_key
                and model
                and "{task_id}" in result_api_url
                and _is_valid_https_url(api_url)
                and _is_valid_https_url(result_probe_url)
                and size in allowed_sizes
            ),
            "api_url": api_url,
            "result_api_url": result_api_url,
            "api_key": api_key,
            "model": model,
            "size": size,
            "duration_seconds": settings.VIDEO_CLIP_DURATION_SECONDS if supports_duration else 5,
            "supports_duration": supports_duration,
            "fps": settings.VIDEO_CLIP_FPS,
            "with_audio": settings.VIDEO_CLIP_WITH_AUDIO,
            "use_scene_image": settings.VIDEO_CLIP_USE_SCENE_IMAGE,
            "reference_image_max_file_bytes": settings.VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES,
            "request_timeout_seconds": settings.VIDEO_CLIP_REQUEST_TIMEOUT_SECONDS,
            "poll_interval_seconds": settings.VIDEO_CLIP_POLL_INTERVAL_SECONDS,
            "max_wait_seconds": settings.VIDEO_CLIP_MAX_WAIT_SECONDS,
            "max_file_bytes": settings.VIDEO_CLIP_MAX_FILE_BYTES,
            "daily_job_limit": settings.VIDEO_CLIP_DAILY_JOB_LIMIT,
        }
    if job_type == AUDIO_JOB_TYPE:
        api_url = settings.VIDEO_TTS_API_URL
        api_key = settings.VIDEO_TTS_API_KEY
        model = settings.VIDEO_TTS_MODEL
        return {
            "asset_type": "audio",
            "provider": "glm",
            "configured": bool(api_key and model and _is_valid_https_url(api_url)),
            "api_url": api_url,
            "api_key": api_key,
            "model": model,
            "voice": settings.VIDEO_TTS_VOICE,
            "speed": settings.VIDEO_TTS_SPEED,
            "volume": settings.VIDEO_TTS_VOLUME,
            "timeout_seconds": settings.VIDEO_TTS_TIMEOUT_SECONDS,
            "max_file_bytes": settings.VIDEO_ASSET_MAX_FILE_BYTES,
            "daily_job_limit": settings.VIDEO_TTS_DAILY_JOB_LIMIT,
        }
    raise ValidationError("Unsupported video asset job type.")


def _read_limited_binary(response, max_file_bytes, error_message):
    content_length = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
    if content_length:
        try:
            if int(content_length) > max_file_bytes:
                raise ValidationError(error_message)
        except ValueError:
            pass
    content = response.read(max_file_bytes + 1)
    if not content or len(content) > max_file_bytes:
        raise ValidationError(error_message)
    return content


def _response_content_type(response):
    if not getattr(response, "headers", None):
        return ""
    return (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()


def _read_glm_error_code(error):
    try:
        response_body = error.read(16 * 1024)
    except (AttributeError, OSError):
        return ""
    if not response_body:
        return ""
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    error_payload = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error_payload, dict):
        return ""
    error_code = str(error_payload.get("code") or "").strip()
    return error_code if re.fullmatch(r"[A-Za-z0-9_-]{1,32}", error_code) else ""


def _glm_http_error_message(error, operation):
    error_code = _read_glm_error_code(error)
    message = GLM_ERROR_MESSAGES.get(error_code)
    if not message:
        if error.code == 429:
            message = "GLM 返回额度或频率限制，请检查账户余额、模型权限和调用频率后重试。"
        elif error.code == 401:
            message = "GLM API Key 无效或已过期，请检查服务端配置。"
        elif error.code == 403:
            message = "GLM API Key 没有当前模型的访问权限。"
        elif error.code == 400:
            message = "GLM 拒绝了请求参数，请检查模型配置。"
        elif error.code >= 500:
            message = "GLM 服务暂时不可用，请稍后重试。"
        else:
            message = "GLM 请求失败，请稍后重试。"
    code_suffix = f"，业务错误码 {error_code}" if error_code else ""
    return f"{operation}失败：{message}（HTTP {error.code}{code_suffix}）"


def _infer_image_mime_type(content):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _infer_video_mime_type(content):
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return "video/mp4"
    return ""


def _build_video_clip_prompt(scene):
    prompt_adapter = (scene.agent_metadata or {}).get("prompt_adapter") or {}
    adapted_prompt = prompt_adapter.get("video_prompt") or ""
    prompt_parts = (adapted_prompt or scene.visual_prompt, scene.camera_direction, scene.mood)
    original_prompt = " ".join(" ".join(part.split()) for part in prompt_parts if part).strip()
    if not original_prompt:
        original_prompt = "竖屏电影感故事镜头，主体动作自然，光线真实，构图稳定"

    safe_prompt = original_prompt
    for source_text, replacement_text in VIDEO_CLIP_PROMPT_REPLACEMENTS:
        safe_prompt = safe_prompt.replace(source_text, replacement_text)
    safe_prompt = " ".join(safe_prompt.split())
    return f"{VIDEO_CLIP_PROMPT_PREFIX}{safe_prompt}"[:512], safe_prompt != original_prompt


def call_video_image_asset(scene):
    config = get_video_asset_provider_config(IMAGE_JOB_TYPE)
    if not config["configured"]:
        raise ValidationError("服务端尚未配置镜头画面生成服务。")

    agent_metadata = scene.agent_metadata or {}
    prompt_adapter = agent_metadata.get("prompt_adapter") or {}
    visual_plan = agent_metadata.get("visual_plan") or {}
    adapted_prompt = prompt_adapter.get("image_prompt") or ""
    prompt = " ".join((adapted_prompt or scene.visual_prompt or scene.title or "竖屏电影感故事画面").split())[:1000]
    payload = {
        "model": config["model"],
        "prompt": prompt,
        "size": config["size"],
        "watermark_enabled": True,
    }
    request = Request(
        config["api_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config["timeout_seconds"]) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        raise ValidationError(_glm_http_error_message(error, "镜头画面生成"))
    except URLError:
        raise ValidationError("无法连接镜头画面生成服务，请稍后重试。")
    except TimeoutError:
        raise ValidationError("镜头画面生成服务响应超时，请稍后重试。")
    except UnicodeDecodeError:
        raise ValidationError("镜头画面生成服务返回了无法解析的响应。")

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError:
        raise ValidationError("镜头画面生成服务返回了无法解析的响应。")
    result_items = result.get("data") if isinstance(result, dict) else None
    image_url = (
        result_items[0].get("url")
        if isinstance(result_items, list) and result_items and isinstance(result_items[0], dict)
        else ""
    )
    if not image_url or not _is_valid_https_url(image_url):
        raise ValidationError("镜头画面生成服务未返回安全的图片地址。")

    download_request = Request(image_url, headers={"Accept": "image/*"}, method="GET")
    try:
        with urlopen(download_request, timeout=config["timeout_seconds"]) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else image_url
            if not _is_valid_https_url(final_url):
                raise ValidationError("镜头画面下载地址不安全。")
            content = _read_limited_binary(response, config["max_file_bytes"], "镜头画面文件超过大小限制。")
            response_mime_type = _response_content_type(response)
            mime_type = (
                response_mime_type
                if response_mime_type in IMAGE_MIME_EXTENSIONS
                else _infer_image_mime_type(content)
            )
    except HTTPError as error:
        raise ValidationError(f"镜头画面文件下载失败，HTTP {error.code}。")
    except URLError:
        raise ValidationError("无法下载镜头画面文件，请稍后重试。")
    except TimeoutError:
        raise ValidationError("镜头画面文件下载超时，请稍后重试。")

    if mime_type not in IMAGE_MIME_EXTENSIONS:
        raise ValidationError("镜头画面服务返回了不支持的文件格式。")
    return {
        "content": content,
        "mime_type": mime_type,
        "extension": IMAGE_MIME_EXTENSIONS[mime_type],
        "provider": config["provider"],
        "provider_asset_id": hashlib.sha256(image_url.encode("utf-8")).hexdigest(),
        "model": config["model"],
        "metadata": {
            "size": config["size"],
            "prompt_length": len(prompt),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "prompt_strategy": prompt_adapter.get("strategy") or "scene_prompt",
            "prompt_adapter_version": prompt_adapter.get("version") or "",
            "anchor_fingerprint": prompt_adapter.get("anchor_fingerprint") or "",
            "continuity_group_id": visual_plan.get("continuity_group_id") or "",
            "relationship_to_previous": visual_plan.get("relationship_to_previous") or "",
            "inherits_from_scene_no": visual_plan.get("inherits_from_scene_no"),
            "reference_mode": "text_only_canonical_anchors",
            "visual_review": {
                "status": "pending",
                "mode": "manual_required",
                "reason": "image_understanding_not_configured",
                "required_checks": [
                    "角色身份与服装",
                    "场景地标与光源方向",
                    "道具外观与状态",
                    "构图轴线与屏幕方向",
                ],
            },
            "content_filter": (result.get("content_filter") or []) if isinstance(result, dict) else [],
        },
    }


def _build_video_reference_data_url(reference_frame, max_file_bytes):
    if not reference_frame:
        return ""
    content = reference_frame.get("content")
    mime_type = reference_frame.get("mime_type")
    if not isinstance(content, bytes) or not content:
        raise ValidationError("短视频参考帧文件为空。")
    if len(content) > max_file_bytes:
        raise ValidationError("短视频参考帧文件超过 5MB 限制。")
    inferred_mime_type = _infer_image_mime_type(content)
    if mime_type not in VIDEO_REFERENCE_IMAGE_MIME_TYPES or inferred_mime_type != mime_type:
        raise ValidationError("短视频参考帧必须是有效的 PNG 或 JPEG 文件。")
    encoded_content = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded_content}"


def _provider_network_error_message(error, service_label):
    reason = getattr(error, "reason", error)
    winerror = getattr(reason, "winerror", None)
    if isinstance(reason, (TimeoutError, socket.timeout)) or winerror == 10060:
        return f"{service_label}连接超时，请检查 Worker 网络或代理后重试。"
    if isinstance(reason, socket.gaierror):
        return f"{service_label}域名解析失败，请检查 Worker 的 DNS 配置。"
    if isinstance(reason, ssl.SSLCertVerificationError):
        return f"{service_label}TLS 证书校验失败，请检查系统时间、代理证书和证书链。"
    if isinstance(reason, ssl.SSLError):
        return f"{service_label}TLS 握手失败，请检查代理和 TLS 配置。"
    if isinstance(reason, ConnectionRefusedError) or winerror == 10061:
        return f"{service_label}连接被拒绝，请检查 Worker 所在环境的代理、网络隔离和防火墙。"
    if winerror in {10051, 10065}:
        return f"{service_label}网络不可达，请检查 Worker 所在环境的网络路由和代理。"
    return f"无法连接{service_label}，请检查 Worker 所在环境的网络、代理和防火墙后重试。"


def call_video_clip_asset(
    scene,
    reference_frame=None,
    reference_fallback_reasons=None,
    resume_task_id="",
    on_task_created=None,
):
    config = get_video_asset_provider_config(VIDEO_JOB_TYPE)
    if not config["configured"]:
        raise ValidationError("服务端尚未配置短视频画面生成服务。")

    prompt, prompt_safety_adjusted = _build_video_clip_prompt(scene)
    agent_metadata = scene.agent_metadata or {}
    prompt_adapter = agent_metadata.get("prompt_adapter") or {}
    frame_policy = prompt_adapter.get("frame_policy") or {}
    continuity_contract = agent_metadata.get("continuity_contract") or {}
    payload = {
        "model": config["model"],
        "prompt": prompt,
        "size": config["size"],
        "fps": config["fps"],
        "with_audio": config["with_audio"],
        "watermark_enabled": True,
    }
    if config["supports_duration"]:
        payload["duration"] = config["duration_seconds"]
    reference_data_url = _build_video_reference_data_url(
        reference_frame,
        config["reference_image_max_file_bytes"],
    )
    if reference_data_url:
        payload["image_url"] = reference_data_url
    task_id = str(resume_task_id or "").strip()
    resumed_provider_task = bool(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id))
    if not resumed_provider_task:
        request = Request(
            config["api_url"],
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=config["request_timeout_seconds"]) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            raise ValidationError(_glm_http_error_message(error, "短视频画面生成"))
        except URLError as error:
            raise ValidationError(_provider_network_error_message(error, "短视频画面生成服务"))
        except TimeoutError:
            raise ValidationError("短视频画面生成服务响应超时，请稍后重试。")
        except UnicodeDecodeError:
            raise ValidationError("短视频画面生成服务返回了无法解析的响应。")

        try:
            task_result = json.loads(response_body)
        except json.JSONDecodeError:
            raise ValidationError("短视频画面生成服务返回了无法解析的响应。")
        task_id = str(task_result.get("id") or "").strip() if isinstance(task_result, dict) else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", task_id):
            raise ValidationError("短视频画面生成服务未返回有效的任务编号。")
        if callable(on_task_created):
            on_task_created(task_id, config["model"])
    else:
        task_result = {
            "id": task_id,
            "model": config["model"],
            "task_status": "PROCESSING",
        }

    result_url = config["result_api_url"].replace("{task_id}", quote(task_id, safe=""))
    if not _is_valid_https_url(result_url):
        raise ValidationError("短视频画面结果查询地址不安全。")
    deadline = time.monotonic() + config["max_wait_seconds"]
    poll_count = 0
    poll_error_count = 0
    last_poll_error_message = ""
    while True:
        status = str(task_result.get("task_status") or "PROCESSING").strip().upper()
        if status == "SUCCESS":
            break
        if status in {"FAIL", "FAILED", "CANCELED", "CANCELLED"}:
            raise ValidationError("短视频画面生成任务执行失败，请检查提示词或稍后重试。")
        if status not in {"PROCESSING", "PENDING", "QUEUED", "RUNNING"}:
            raise ValidationError("短视频画面生成服务返回了未知的任务状态。")
        if time.monotonic() >= deadline:
            if last_poll_error_message:
                raise ValidationError(f"{last_poll_error_message}；异步结果查询已达到等待上限。")
            raise ValidationError("短视频画面生成任务等待超时，请稍后重试。")

        time.sleep(config["poll_interval_seconds"])
        poll_count += 1
        poll_request = Request(
            result_url,
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(poll_request, timeout=config["request_timeout_seconds"]) as response:
                task_result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            error_message = _glm_http_error_message(error, "短视频画面结果查询")
            if error.code == 429 or error.code >= 500:
                poll_error_count += 1
                last_poll_error_message = error_message
                continue
            raise ValidationError(error_message)
        except URLError as error:
            poll_error_count += 1
            last_poll_error_message = _provider_network_error_message(
                error,
                "短视频画面结果查询服务",
            )
            continue
        except TimeoutError:
            poll_error_count += 1
            last_poll_error_message = "短视频画面结果查询超时，请检查 Worker 网络后重试。"
            continue
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("短视频画面结果查询返回了无法解析的响应。")
        if not isinstance(task_result, dict):
            raise ValidationError("短视频画面结果查询返回的数据结构不正确。")
        last_poll_error_message = ""

    result_items = task_result.get("video_result") if isinstance(task_result, dict) else None
    video_url = (
        result_items[0].get("url")
        if isinstance(result_items, list) and result_items and isinstance(result_items[0], dict)
        else ""
    )
    if not video_url or not _is_valid_https_url(video_url):
        raise ValidationError("短视频画面生成服务未返回安全的视频地址。")

    download_request = Request(video_url, headers={"Accept": "video/mp4"}, method="GET")
    try:
        with urlopen(download_request, timeout=config["request_timeout_seconds"]) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else video_url
            if not _is_valid_https_url(final_url):
                raise ValidationError("短视频画面下载地址不安全。")
            content = _read_limited_binary(response, config["max_file_bytes"], "短视频画面文件超过大小限制。")
            response_mime_type = _response_content_type(response)
            mime_type = (
                response_mime_type
                if response_mime_type in VIDEO_MIME_EXTENSIONS
                else _infer_video_mime_type(content)
            )
    except HTTPError as error:
        raise ValidationError(f"短视频画面文件下载失败，HTTP {error.code}。")
    except URLError as error:
        raise ValidationError(_provider_network_error_message(error, "短视频画面文件下载服务"))
    except TimeoutError:
        raise ValidationError("短视频画面文件下载超时，请稍后重试。")

    if mime_type not in VIDEO_MIME_EXTENSIONS or _infer_video_mime_type(content) != "video/mp4":
        raise ValidationError("短视频画面服务返回了无效的 MP4 文件。")
    return {
        "content": content,
        "mime_type": mime_type,
        "extension": VIDEO_MIME_EXTENSIONS[mime_type],
        "provider": config["provider"],
        "provider_asset_id": task_id,
        "model": str(task_result.get("model") or config["model"]),
        "metadata": {
            "size": config["size"],
            "duration_seconds": config["duration_seconds"],
            "fps": config["fps"],
            "prompt_length": len(prompt),
            "prompt_safety_adjusted": prompt_safety_adjusted,
            "poll_count": poll_count,
            "poll_error_count": poll_error_count,
            "resumed_provider_task": resumed_provider_task,
            "with_audio": config["with_audio"],
            "visual_review": {
                "status": "pending",
                "mode": "manual_required",
                "reason": "video_understanding_not_configured",
                "required_checks": [
                    "角色身份与服装",
                    "场景与道具连续性",
                    "肢体结构与接触关系",
                    "运动方向与物理合理性",
                ],
            },
            "reference_frame_used": bool(reference_data_url),
            "reference_frame_mode": (
                reference_frame.get("mode") or "scene_image_base64"
                if reference_data_url
                else "text_to_video"
            ),
            "reference_frame_asset_id": reference_frame.get("asset_id") if reference_frame else None,
            "reference_frame_source_scene_no": (
                reference_frame.get("source_scene_no") if reference_frame else None
            ),
            "reference_frame_sha256": reference_frame.get("sha256") if reference_frame else "",
            "reference_frame_fallback_reason": (
                (reference_fallback_reasons or [""])[-1]
                if not reference_data_url
                else ((reference_fallback_reasons or [""])[0])
            ),
            "reference_frame_fallback_reasons": list(reference_fallback_reasons or []),
            "target_render_fps": frame_policy.get("target_fps"),
            "frame_rate_mode": frame_policy.get("mode") or "",
            "continuity_contract_version": continuity_contract.get("version") or "",
        },
    }
    request = Request(
        config["api_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config["timeout_seconds"]) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        raise ValidationError(_glm_http_error_message(error, "镜头画面生成"))
    except URLError:
        raise ValidationError("无法连接镜头画面生成服务，请稍后重试。")
    except TimeoutError:
        raise ValidationError("镜头画面生成服务响应超时，请稍后重试。")
    except UnicodeDecodeError:
        raise ValidationError("镜头画面生成服务返回了无法解析的响应。")

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError:
        raise ValidationError("镜头画面生成服务返回了无法解析的响应。")
    result_items = result.get("data") if isinstance(result, dict) else None
    image_url = (
        result_items[0].get("url")
        if isinstance(result_items, list) and result_items and isinstance(result_items[0], dict)
        else ""
    )
    if not image_url or not _is_valid_https_url(image_url):
        raise ValidationError("镜头画面生成服务未返回安全的图片地址。")

    download_request = Request(image_url, headers={"Accept": "image/*"}, method="GET")
    try:
        with urlopen(download_request, timeout=config["timeout_seconds"]) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else image_url
            if not _is_valid_https_url(final_url):
                raise ValidationError("镜头画面下载地址不安全。")
            content = _read_limited_binary(response, config["max_file_bytes"], "镜头画面文件超过大小限制。")
            response_mime_type = _response_content_type(response)
            mime_type = (
                response_mime_type
                if response_mime_type in IMAGE_MIME_EXTENSIONS
                else _infer_image_mime_type(content)
            )
    except HTTPError as error:
        raise ValidationError(f"镜头画面文件下载失败，HTTP {error.code}。")
    except URLError:
        raise ValidationError("无法下载镜头画面文件，请稍后重试。")
    except TimeoutError:
        raise ValidationError("镜头画面文件下载超时，请稍后重试。")

    if mime_type not in IMAGE_MIME_EXTENSIONS:
        raise ValidationError("镜头画面服务返回了不支持的文件格式。")
    return {
        "content": content,
        "mime_type": mime_type,
        "extension": IMAGE_MIME_EXTENSIONS[mime_type],
        "provider": config["provider"],
        "provider_asset_id": hashlib.sha256(image_url.encode("utf-8")).hexdigest(),
        "model": config["model"],
        "metadata": {
            "size": config["size"],
            "prompt_length": len(prompt),
            "content_filter": (result.get("content_filter") or []) if isinstance(result, dict) else [],
        },
    }


def call_video_narration_asset(scene):
    config = get_video_asset_provider_config(AUDIO_JOB_TYPE)
    if not config["configured"]:
        raise ValidationError("服务端尚未配置旁白配音服务。")

    agent_metadata = scene.agent_metadata or {}
    has_planned_script = "audio_script" in agent_metadata
    audio_script = agent_metadata.get("audio_script") or {}
    planned_text = audio_script.get("text") or ""
    source_text = planned_text if has_planned_script else (scene.narration_text or scene.subtitle_text or scene.title)
    input_text = " ".join(source_text.split())[:1024]
    if not input_text:
        raise ValidationError({"narration_text": ["Scene narration text is required for audio generation."]})
    payload = {
        "model": config["model"],
        "input": input_text,
        "voice": config["voice"],
        "speed": config["speed"],
        "volume": config["volume"],
        "response_format": "wav",
        "stream": False,
        "watermark_enabled": True,
    }
    request = Request(
        config["api_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config["timeout_seconds"]) as response:
            content = _read_limited_binary(response, config["max_file_bytes"], "旁白配音文件超过大小限制。")
            mime_type = _response_content_type(response) or "audio/wav"
    except HTTPError as error:
        raise ValidationError(_glm_http_error_message(error, "旁白配音"))
    except URLError:
        raise ValidationError("无法连接旁白配音服务，请稍后重试。")
    except TimeoutError:
        raise ValidationError("旁白配音服务响应超时，请稍后重试。")

    if mime_type not in ("audio/wav", "audio/x-wav") or not (content.startswith(b"RIFF") and content[8:12] == b"WAVE"):
        raise ValidationError("旁白配音服务返回了无效的 WAV 文件。")
    return {
        "content": content,
        "mime_type": "audio/wav",
        "extension": ".wav",
        "provider": config["provider"],
        "provider_asset_id": "",
        "model": config["model"],
        "metadata": {
            "voice": config["voice"],
            "speed": config["speed"],
            "volume": config["volume"],
            "input_length": len(input_text),
            "script_source": "agent_workflow" if has_planned_script else "scene_fallback",
            "speaker_id": audio_script.get("speaker_id") or "",
            "emotion": audio_script.get("emotion") or "",
            "planned_voice_profile_id": audio_script.get("voice_profile_id") or "",
            "target_duration_ms": audio_script.get("target_duration_ms") or 0,
        },
    }


def _build_audio_transcription_multipart(content, model):
    boundary = f"SunshineReading{uuid4().hex}"
    body = b"".join(
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\n{model}\r\n".encode("utf-8"),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"stream\"\r\n\r\nfalse\r\n".encode("ascii"),
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                "filename=\"narration.wav\"\r\nContent-Type: audio/wav\r\n\r\n"
            ).encode("ascii"),
            content,
            f"\r\n--{boundary}--\r\n".encode("ascii"),
        )
    )
    return body, boundary


def call_video_audio_transcription(content):
    config = get_video_audio_transcription_config()
    if not config["configured"]:
        raise ValidationError("服务端尚未配置旁白 ASR 语义质检服务。")
    if not content or len(content) > config["max_file_bytes"]:
        raise ValidationError("旁白音频超过 ASR 的 25MB 文件限制。")

    request_body, boundary = _build_audio_transcription_multipart(content, config["model"])
    request = Request(
        config["api_url"],
        data=request_body,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config["timeout_seconds"]) as response:
            response_body = _read_limited_binary(
                response,
                1024 * 1024,
                "旁白 ASR 语义质检响应超过大小限制。",
            ).decode("utf-8")
    except HTTPError as error:
        raise ValidationError(_glm_http_error_message(error, "旁白 ASR 语义质检"))
    except URLError:
        raise ValidationError("无法连接旁白 ASR 语义质检服务，请人工试听确认。")
    except TimeoutError:
        raise ValidationError("旁白 ASR 语义质检服务响应超时，请人工试听确认。")
    except UnicodeDecodeError:
        raise ValidationError("旁白 ASR 语义质检服务返回了无法解析的响应。")

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError:
        raise ValidationError("旁白 ASR 语义质检服务返回了无法解析的响应。")
    if not isinstance(result, dict):
        raise ValidationError("旁白 ASR 语义质检服务返回的数据结构不正确。")
    transcript = str(result.get("text") or "").strip()
    if not transcript:
        raise ValidationError("旁白 ASR 语义质检服务未返回有效转写文本。")
    return {
        "provider_asset_id": str(result.get("id") or "")[:255],
        "model": str(result.get("model") or config["model"])[:120],
        "text": transcript[:2000],
    }


def _build_story_architect_messages(project, scene_count):
    preferred_spoken_characters = max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 4)
    hard_max_spoken_characters = max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 5)
    system_prompt = (
        "你是短视频制作设定总编，内部依次执行剧情、角色、形象、场景、道具和台词拆解。"
        "忠实理解原文后，只返回一个 JSON 对象，不要使用 Markdown。根对象必须包含 logline、theme、"
        "visual_style、characters、character_looks、locations、props、dialogue_units、continuity_rules、beats。"
        "所有实体 id 必须全局唯一，只能使用小写字母、数字和下划线，并分别使用 char_、look_、loc_、"
        "prop_、line_ 前缀。characters 每项包含 id、name、story_role、identity、appearance、behavior、"
        "voice_profile_id；appearance 只写稳定的年龄、体态、脸型、五官和发型，不写服装。"
        "character_looks 每项包含 id、character_id、label、wardrobe、hair_makeup、signature_features、"
        "color_palette、reference_prompt；每个角色至少一个形象版本。"
        "locations 每项包含 id、name、geography、visual_anchor、time_of_day、weather、lighting、"
        "color_palette、reference_prompt。props 每项包含 id、name、owner_character_id、visual_anchor、"
        "initial_state、continuity_rule、reference_prompt，无归属时 owner_character_id 为空字符串。"
        "dialogue_units 每项包含 id、beat_no、kind、speaker_id、text、subtitle_text、emotion、pause_after_ms、"
        "target_duration_ms、voice_profile_id；kind 只能是 narration 或 dialogue，旁白 speaker_id 必须为 narrator。"
        "dialogue_units 的 beat_no 只能引用输入指定的节拍范围，禁止创建额外台词单元或额外节拍。"
        "每个节拍可引用 0-4 个台词单元，所有非空单元必须属于同一名说话者；静默节拍使用空的"
        "dialogue_unit_ids，且不得超过总节拍数的三分之一。短句按每秒不超过五个汉字的自然语速设计，"
        "并确保这些单元的 target_duration_ms 与 pause_after_ms 合计不超过单段视频时长。"
        "beats 每项包含 beat_no、purpose、action、outcome、location_id、character_ids、look_ids、prop_ids、"
        "dialogue_unit_ids；每个出镜角色必须引用且只引用一个对应形象，台词必须完整归属对应节拍。"
        "每个节拍只能包含一个时间、一个地点和一个核心动作，节拍之间必须有明确因果。"
        "不得改变人物动机、事件结果、角色关系或关键道具，不得把计划成功改写成失败。"
    )
    user_prompt = (
        f"项目标题：{project.title}\n"
        f"目标时长：{project.duration_target} 秒\n"
        f"原子镜头/节拍数量：{scene_count}\n"
        f"硬性约束：必须恰好返回 {scene_count} 个 beats；所有 dialogue_units.beat_no 必须在 1 到 {scene_count} 内。\n"
        f"台词时长约束：同一 beat 的所有 target_duration_ms 与 pause_after_ms 合计不得超过 "
        f"{settings.VIDEO_CLIP_DURATION_SECONDS * 1000} 毫秒。\n"
        f"台词字数约束：同一 beat 的所有 text 去除空白后连同标点建议不超过 "
        f"{preferred_spoken_characters} 个字符，绝对不得超过 {hard_max_spoken_characters} 个字符。\n"
        "形象覆盖约束：characters 中每个角色必须至少在 character_looks.character_id 中出现一次；"
        "beats.look_ids 只能引用已经定义的形象，并为每个出镜角色引用且只引用一个形象。\n"
        f"单段视频模型时长：{settings.VIDEO_CLIP_DURATION_SECONDS} 秒\n"
        f"视觉风格：{project.style_preset}\n"
        f"故事正文：\n{project.input_text}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _collect_validation_error_codes(value):
    if isinstance(value, dict):
        return {
            code
            for item in value.values()
            for code in _collect_validation_error_codes(item)
        }
    if isinstance(value, (list, tuple)):
        return {code for item in value for code in _collect_validation_error_codes(item)}
    code = getattr(value, "code", None)
    return {code} if code else set()


def _has_only_dialogue_budget_errors(validation_errors):
    error_codes = _collect_validation_error_codes(validation_errors)
    return bool(error_codes) and error_codes <= {
        "dialogue_text_too_long",
        "dialogue_timing_overflow",
    }


def _build_dialogue_budget_diagnostics(production_plan):
    clip_duration_ms = settings.VIDEO_CLIP_DURATION_SECONDS * 1000
    hard_max_characters = max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 5)
    preferred_characters = max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 4)
    dialogue_units_by_beat = {}
    for unit in production_plan.get("dialogue_units") or []:
        if not isinstance(unit, dict):
            continue
        beat_no = unit.get("beat_no")
        if not isinstance(beat_no, int) or isinstance(beat_no, bool):
            continue
        dialogue_units_by_beat.setdefault(beat_no, []).append(unit)

    diagnostics = []
    for beat_no, dialogue_units in sorted(dialogue_units_by_beat.items()):
        text_character_count = sum(
            len("".join(str(unit.get("text") or "").split()))
            for unit in dialogue_units
        )
        timing_values = [
            (unit.get("target_duration_ms"), unit.get("pause_after_ms"))
            for unit in dialogue_units
        ]
        timing_is_numeric = all(
            isinstance(target_duration_ms, int)
            and not isinstance(target_duration_ms, bool)
            and isinstance(pause_after_ms, int)
            and not isinstance(pause_after_ms, bool)
            for target_duration_ms, pause_after_ms in timing_values
        )
        planned_duration_ms = (
            sum(target_duration_ms + pause_after_ms for target_duration_ms, pause_after_ms in timing_values)
            if timing_is_numeric
            else None
        )
        if (
            text_character_count <= hard_max_characters
            and (planned_duration_ms is None or planned_duration_ms <= clip_duration_ms)
        ):
            continue
        diagnostics.append(
            {
                "beat_no": beat_no,
                "dialogue_unit_ids": [unit.get("id") for unit in dialogue_units],
                "actual_text_characters": text_character_count,
                "preferred_text_characters": preferred_characters,
                "hard_max_text_characters": hard_max_characters,
                "planned_duration_ms": planned_duration_ms,
                "hard_max_duration_ms": clip_duration_ms,
            }
        )
    return diagnostics


def _build_dialogue_repair_messages(project, scene_count, production_plan, validation_errors):
    preferred_spoken_characters = max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 4)
    hard_max_spoken_characters = max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 5)
    system_prompt = (
        "你是短视频台词预算精编 Agent。输入只包含超限节拍及其台词。只返回一个 JSON 对象，不要返回解释或"
        "Markdown；根对象只能包含 dialogue_units。dialogue_units 必须恰好覆盖输入要求修复的全部台词 ID，"
        "每项只能包含 id、text、subtitle_text、target_duration_ms、pause_after_ms，不得新增、删除、遗漏或"
        "改写 ID。精简台词时保留该节拍的关键事实、人物意图、因果结果和语气，不得添加输入不存在的信息。"
        "每个 beat 的所有 text 去除空白后连同标点必须满足给定字符预算，subtitle_text 与精简后的 text 语义"
        "一致；同一 beat 的 target_duration_ms 与 pause_after_ms 合计必须满足时长预算。输出前逐个 beat"
        "重新计数，禁止仅修改时长来掩盖正文过长。"
    )
    error_text = json.dumps(validation_errors, ensure_ascii=False, default=str)
    if len(error_text) > 3000:
        error_text = f"{error_text[:3000]}（其余错误已截断）"
    diagnostics = _build_dialogue_budget_diagnostics(production_plan)
    repair_beat_numbers = {item["beat_no"] for item in diagnostics}
    repair_dialogue_ids = {
        dialogue_unit_id
        for item in diagnostics
        for dialogue_unit_id in item["dialogue_unit_ids"]
    }
    repair_context = {
        "logline": production_plan.get("logline"),
        "theme": production_plan.get("theme"),
        "beats": [
            beat
            for beat in production_plan.get("beats") or []
            if isinstance(beat, dict) and beat.get("beat_no") in repair_beat_numbers
        ],
        "dialogue_units": [
            unit
            for unit in production_plan.get("dialogue_units") or []
            if isinstance(unit, dict) and unit.get("id") in repair_dialogue_ids
        ],
    }
    user_prompt = (
        f"项目标题：{project.title}\n"
        f"节拍数量：{scene_count}\n"
        f"单镜时长：{settings.VIDEO_CLIP_DURATION_SECONDS} 秒\n"
        f"每个 beat 建议最多 {preferred_spoken_characters} 个字符，硬上限 "
        f"{hard_max_spoken_characters} 个字符；字符统计去除空白但包含标点。\n"
        f"每个 beat 的计划发声与停顿合计硬上限：{settings.VIDEO_CLIP_DURATION_SECONDS * 1000} 毫秒。\n"
        f"超限诊断：\n{json.dumps(diagnostics, ensure_ascii=False)}\n"
        f"服务端校验错误：\n{error_text}\n"
        f"待精编上下文：\n{json.dumps(repair_context, ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _apply_dialogue_repair_payload(production_plan, repair_payload):
    diagnostics = _build_dialogue_budget_diagnostics(production_plan)
    expected_ids = {
        dialogue_unit_id
        for item in diagnostics
        for dialogue_unit_id in item["dialogue_unit_ids"]
        if isinstance(dialogue_unit_id, str)
    }
    repaired_units = repair_payload.get("dialogue_units") if isinstance(repair_payload, dict) else None
    if not expected_ids or not isinstance(repaired_units, list):
        raise ValidationError("台词预算精编 Agent 返回的数据结构不正确。")

    required_fields = {
        "id",
        "text",
        "subtitle_text",
        "target_duration_ms",
        "pause_after_ms",
    }
    if any(not isinstance(unit, dict) or set(unit) != required_fields for unit in repaired_units):
        raise ValidationError("台词预算精编 Agent 返回了未授权字段或缺少必填字段。")
    repaired_unit_by_id = {unit["id"]: unit for unit in repaired_units if isinstance(unit.get("id"), str)}
    if len(repaired_unit_by_id) != len(repaired_units) or set(repaired_unit_by_id) != expected_ids:
        raise ValidationError("台词预算精编 Agent 必须且只能返回全部超限台词单元。")

    merged_plan = deepcopy(production_plan)
    for dialogue_unit in merged_plan.get("dialogue_units") or []:
        repair = repaired_unit_by_id.get(dialogue_unit.get("id")) if isinstance(dialogue_unit, dict) else None
        if not repair:
            continue
        for field_name in required_fields - {"id"}:
            dialogue_unit[field_name] = repair[field_name]
    return merged_plan


def _build_schema_repair_messages(project, scene_count, production_plan, validation_errors):
    system_prompt = (
        "你是短视频制作设定结构修复 Agent。输入是一份未通过服务端契约校验的制作设定。"
        "只做通过契约所必需的最小修复，保持原有故事事实、人物动机、事件顺序、事件结果、角色关系、"
        "视觉风格和关键道具不变。只返回修复后的完整 JSON 根对象，不要返回补丁、解释或 Markdown。"
        "根对象必须包含 logline、theme、visual_style、characters、character_looks、locations、props、"
        "dialogue_units、continuity_rules、beats。必须恰好包含指定数量的 beats，beat_no 从 1 连续递增；"
        "缺少节拍时只能依据相邻节拍的因果关系拆分已有事件，不得虚构新剧情，禁止保留多余节拍。"
        "dialogue_units.beat_no 必须落在有效节拍范围，beats.dialogue_unit_ids 必须完整且只引用归属该节拍的"
        "台词。每个角色至少定义一个 character_looks 形象版本；每个节拍中的 location_id、character_ids、"
        "look_ids、prop_ids 和 dialogue_unit_ids 只能引用已定义实体，且每个出镜角色必须且只能引用一个"
        "对应形象。每个节拍只保留一个时间、一个地点和一个核心动作。修复所有给出的校验错误后再输出。"
    )
    error_text = json.dumps(validation_errors, ensure_ascii=False, default=str)
    if len(error_text) > 3000:
        error_text = f"{error_text[:3000]}（其余错误已截断）"
    user_prompt = (
        f"项目标题：{project.title}\n"
        f"目标总时长：{project.duration_target} 秒\n"
        f"硬性节拍数量：{scene_count}\n"
        f"单段视频模型时长：{settings.VIDEO_CLIP_DURATION_SECONDS} 秒\n"
        f"台词时长硬约束：同一 beat 的所有 target_duration_ms 与 pause_after_ms 合计不得超过 "
        f"{settings.VIDEO_CLIP_DURATION_SECONDS * 1000} 毫秒。\n"
        f"台词字数硬约束：同一 beat 的所有 text 去除空白后连同标点不得超过 "
        f"{max(8, settings.VIDEO_CLIP_DURATION_SECONDS * 5)} 个字符。\n"
        f"服务端校验错误：\n{error_text}\n"
        f"待修复制作设定：\n{json.dumps(production_plan, ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _build_shot_batch_plan(production_plan, beats, visual_world_model=None):
    character_ids = {
        character_id
        for beat in beats
        for character_id in (beat.get("character_ids") or [])
    }
    look_ids = {
        look_id
        for beat in beats
        for look_id in (beat.get("look_ids") or [])
    }
    location_ids = {beat.get("location_id") for beat in beats if beat.get("location_id")}
    prop_ids = {
        prop_id
        for beat in beats
        for prop_id in (beat.get("prop_ids") or [])
    }
    dialogue_unit_ids = {
        dialogue_unit_id
        for beat in beats
        for dialogue_unit_id in (beat.get("dialogue_unit_ids") or [])
    }
    dialogue_units = [
        item
        for item in production_plan.get("dialogue_units") or []
        if item.get("id") in dialogue_unit_ids
    ]
    character_ids.update(
        item.get("speaker_id")
        for item in dialogue_units
        if item.get("speaker_id") and item.get("speaker_id") != "narrator"
    )
    props = [
        item
        for item in production_plan.get("props") or []
        if item.get("id") in prop_ids
    ]
    character_ids.update(
        item.get("owner_character_id")
        for item in props
        if item.get("owner_character_id")
    )
    visual_world_model = visual_world_model or build_visual_world_model(production_plan)
    return {
        "logline": production_plan.get("logline"),
        "theme": production_plan.get("theme"),
        "visual_style": production_plan.get("visual_style"),
        "characters": [
            item
            for item in production_plan.get("characters") or []
            if item.get("id") in character_ids
        ],
        "character_looks": [
            item
            for item in production_plan.get("character_looks") or []
            if item.get("id") in look_ids
        ],
        "locations": [
            item
            for item in production_plan.get("locations") or []
            if item.get("id") in location_ids
        ],
        "props": props,
        "dialogue_units": dialogue_units,
        "continuity_rules": production_plan.get("continuity_rules") or [],
        "visual_models": {
            "characters": [
                item
                for item in visual_world_model.get("character_models") or []
                if item.get("look_id") in look_ids
            ],
            "scenes": [
                item
                for item in visual_world_model.get("scene_models") or []
                if item.get("location_id") in location_ids
            ],
            "physical_rules": visual_world_model.get("physical_rules") or [],
            "logic_rules": visual_world_model.get("logic_rules") or [],
        },
        "beats": beats,
    }


def _build_previous_scene_context(scene):
    if not scene:
        return {}
    return {
        field_name: scene.get(field_name)
        for field_name in (
            "end_state",
            "continuity_anchor",
            "transition_out",
            "location_id",
            "character_ids",
            "look_ids",
            "prop_states",
        )
    }


def _build_shot_director_messages(project, scene_count, batch_plan, previous_scene_context=None):
    beats = batch_plan.get("beats") or []
    batch_scene_count = len(beats)
    first_beat_no = beats[0]["beat_no"]
    last_beat_no = beats[-1]["beat_no"]
    system_prompt = (
        "你是竖屏短视频原子镜头导演。当前只处理全片的一个连续批次。严格依据剧情架构和连续性设定，"
        "按输入 beats 的顺序把每个节拍转成一个可独立生成、"
        "又能与前后镜衔接的原子镜头。只返回 JSON 对象，不要使用 Markdown。"
        "根对象必须包含 summary 和 scenes；不得新增、删除、合并或重排节拍。scenes 数量必须与当前批次"
        "节拍数量完全一致，每项必须包含 "
        "title、visual_prompt、narration_text、subtitle_text、duration_seconds、camera_direction、mood、"
        "story_function、location_id、character_ids、look_ids、prop_states、dialogue_unit_ids、start_state、"
        "end_state、continuity_anchor、transition_out、motion_prompt。prop_states 每项必须包含 prop_id 和 state。"
        "location_id、character_ids、look_ids、prop_states 中的 prop_id、dialogue_unit_ids 必须与对应节拍完全一致。"
        "narration_text 必须按 dialogue_unit_ids 顺序原样拼接 text，单元间用一个空格；subtitle_text 必须按顺序"
        "原样拼接 subtitle_text，单元间用换行；静默节拍的 narration_text 和 subtitle_text 必须为空字符串，"
        "不得省略、改写或补写非静默节拍的台词。"
        "每镜只允许一个地点、一个连续动作和一种运镜，不得在同一镜头中写随后切到、与此同时或另一地点。"
        "visual_prompt 必须包含具体主体、环境、动作、光线、构图和可见细节；motion_prompt 只描述可观察动作。"
        "相邻镜头的 start_state 必须承接上一镜 end_state。当前批次不是全片末批时，末镜 transition_out 也必须"
        "说明下一批首镜可复用的动作、视线、道具或环境。输入提供上一批末镜状态时，当前首镜必须从该状态继续。"
        "每镜必须绑定输入 visual_models 中对应的人物模型卡和场景空间模型：年龄、脸型、体态、发型、服装、"
        "标志特征、地理方向、前后景、光照和调色不得漂移。人物肢体数量与关节方向必须正常，双脚、坐姿和"
        "手持道具必须有合理支撑与接触；禁止人物、衣物、道具或环境表面互相穿透。动作必须符合重力、惯性和"
        "当前 start_state，不得无因悬空、瞬移、复制实体、改变道具状态或倒置事件因果。"
        "角色名称、形象版本、服装、道具状态、地点和光线必须复用制作设定，不得自行替换。"
    )
    previous_context_text = (
        json.dumps(previous_scene_context, ensure_ascii=False)
        if previous_scene_context
        else "无；这是全片第一批，请依据第一个节拍建立初始状态。"
    )
    user_prompt = (
        f"项目标题：{project.title}\n"
        f"目标总时长：{project.duration_target} 秒\n"
        f"全片镜头总数：{scene_count}\n"
        f"当前批次镜头范围：{first_beat_no}-{last_beat_no} / {scene_count}\n"
        f"当前批次必须恰好返回 {batch_scene_count} 个 scenes，并与输入的 {batch_scene_count} 个 beats 一一对应。\n"
        f"建议单镜时长：{settings.VIDEO_CLIP_DURATION_SECONDS} 秒\n"
        f"上一批末镜连续性状态：\n{previous_context_text}\n"
        f"当前批次制作设定：\n{json.dumps(batch_plan, ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _build_shot_batch_repair_messages(
    project,
    scene_count,
    batch_plan,
    previous_scene_context,
    validation_errors,
    invalid_payload,
):
    base_messages = _build_shot_director_messages(
        project,
        scene_count,
        batch_plan,
        previous_scene_context,
    )
    error_text = json.dumps(validation_errors, ensure_ascii=False, default=str)
    if len(error_text) > 3000:
        error_text = f"{error_text[:3000]}（其余错误已截断）"
    invalid_text = json.dumps(invalid_payload, ensure_ascii=False, default=str)
    if len(invalid_text) > 24000:
        invalid_text = f"{invalid_text[:24000]}（其余无效输出已截断）"
    return [
        {
            "role": "system",
            "content": (
                "你是原子镜头批次契约修复 Agent。只修复当前批次，必须返回修复后的完整 JSON 对象，"
                "不要返回补丁、解释或 Markdown。不得改写输入 beats、台词、实体引用和故事事实。"
                f"{base_messages[0]['content']}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{base_messages[1]['content']}\n"
                f"服务端校验错误：\n{error_text}\n"
                f"当前批次无效输出：\n{invalid_text}"
            ),
        },
    ]


def _validate_shot_batch(payload, expected_scene_count, batch_plan):
    from .serializers import VideoAiStoryboardResultSerializer

    serializer = VideoAiStoryboardResultSerializer(
        data=payload,
        context={
            "expected_scene_count": expected_scene_count,
            "production_plan": batch_plan,
        },
    )
    if not serializer.is_valid():
        return None, serializer.errors
    return serializer.validated_data, {}


def _extract_upstream_error(error):
    return _glm_http_error_message(error, "AI 分镜生成")


def _parse_json_content(content):
    normalized = str(content or "").strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", normalized, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        normalized = fenced_match.group(1).strip()

    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        raise ValidationError("AI 分镜服务返回了无法解析的 JSON。")
    if not isinstance(payload, dict):
        raise ValidationError("AI 分镜服务返回的数据结构不正确。")
    return payload


def _call_video_ai_json(config, messages, temperature, stage_label, timeout_seconds):
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    if config["thinking_type"]:
        payload["thinking"] = {"type": config["thinking_type"]}
    request = Request(
        config["api_url"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        raise ValidationError(_extract_upstream_error(error))
    except URLError:
        raise ValidationError("无法连接 AI 分镜服务，请稍后重试。")
    except TimeoutError:
        raise ValidationError(
            f"{stage_label}在 {timeout_seconds} 秒内未完成，请稍后重试或使用本地生成。"
        )
    except UnicodeDecodeError:
        raise ValidationError(f"{stage_label}返回了无法解析的响应。")

    try:
        result = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError(f"{stage_label}返回了无法解析的响应。")

    choices = result.get("choices") or []
    if not choices:
        raise ValidationError(f"{stage_label}未返回可用结果。")
    content = (choices[0].get("message") or {}).get("content")
    if not content:
        raise ValidationError(f"{stage_label}返回内容为空。")

    return {
        "payload": _parse_json_content(content),
        "model": result.get("model") or config["model"],
        "usage": result.get("usage") or {},
    }


def _merge_usage(*usages):
    merged = {}
    for usage in usages:
        for key, value in (usage or {}).items():
            if isinstance(value, int):
                merged[key] = merged.get(key, 0) + value
    return merged


def call_video_ai_storyboard(project, scene_count):
    from .serializers import VideoAgentProductionPlanSerializer

    config = get_video_ai_provider_config()
    if not config["configured"]:
        raise ValidationError("服务端尚未配置 AI 分镜服务。")

    story_result = _call_video_ai_json(
        config,
        _build_story_architect_messages(project, scene_count),
        0.35,
        "剧情与连续性策划 Agent",
        config["planning_timeout_seconds"],
    )
    repaired_plan, initial_repair_report = repair_production_plan(
        story_result["payload"],
        scene_count,
        settings.VIDEO_CLIP_DURATION_SECONDS,
    )
    validation_context = {
        "expected_scene_count": scene_count,
        "clip_duration_seconds": settings.VIDEO_CLIP_DURATION_SECONDS,
    }
    production_plan_serializer = VideoAgentProductionPlanSerializer(
        data=repaired_plan,
        context=validation_context,
    )
    stage_usage = {"story_architect": story_result["usage"]}
    usage_items = [story_result["usage"]]
    repair_reports = [initial_repair_report]
    schema_repair_call_count = 0
    dialogue_repair_call_count = 0
    production_plan_is_valid = production_plan_serializer.is_valid()

    if not production_plan_is_valid:
        if _has_only_dialogue_budget_errors(production_plan_serializer.errors):
            provider_repair_result = _call_video_ai_json(
                config,
                _build_dialogue_repair_messages(
                    project,
                    scene_count,
                    repaired_plan,
                    production_plan_serializer.errors,
                ),
                0.1,
                "台词预算精编 Agent",
                config["planning_timeout_seconds"],
            )
            repair_stage_id = "dialogue_repair"
            dialogue_repair_call_count = 1
        else:
            provider_repair_result = _call_video_ai_json(
                config,
                _build_schema_repair_messages(
                    project,
                    scene_count,
                    repaired_plan,
                    production_plan_serializer.errors,
                ),
                0.1,
                "制作设定结构修复 Agent",
                config["planning_timeout_seconds"],
            )
            repair_stage_id = "schema_repair"
            schema_repair_call_count = 1

        provider_repaired_plan = (
            _apply_dialogue_repair_payload(repaired_plan, provider_repair_result["payload"])
            if repair_stage_id == "dialogue_repair"
            else provider_repair_result["payload"]
        )
        repaired_plan, provider_repair_report = repair_production_plan(
            provider_repaired_plan,
            scene_count,
            settings.VIDEO_CLIP_DURATION_SECONDS,
        )
        repair_reports.append(provider_repair_report)
        stage_usage[repair_stage_id] = provider_repair_result["usage"]
        usage_items.append(provider_repair_result["usage"])
        production_plan_serializer = VideoAgentProductionPlanSerializer(
            data=repaired_plan,
            context=validation_context,
        )
        production_plan_is_valid = production_plan_serializer.is_valid()

    if (
        not production_plan_is_valid
        and schema_repair_call_count == 1
        and dialogue_repair_call_count == 0
        and _has_only_dialogue_budget_errors(production_plan_serializer.errors)
    ):
        dialogue_repair_result = _call_video_ai_json(
            config,
            _build_dialogue_repair_messages(
                project,
                scene_count,
                repaired_plan,
                production_plan_serializer.errors,
            ),
            0.1,
            "台词预算精编 Agent",
            config["planning_timeout_seconds"],
        )
        dialogue_repaired_plan = _apply_dialogue_repair_payload(
            repaired_plan,
            dialogue_repair_result["payload"],
        )
        repaired_plan, dialogue_repair_report = repair_production_plan(
            dialogue_repaired_plan,
            scene_count,
            settings.VIDEO_CLIP_DURATION_SECONDS,
        )
        repair_reports.append(dialogue_repair_report)
        dialogue_repair_call_count = 1
        stage_usage["dialogue_repair"] = dialogue_repair_result["usage"]
        usage_items.append(dialogue_repair_result["usage"])
        production_plan_serializer = VideoAgentProductionPlanSerializer(
            data=repaired_plan,
            context=validation_context,
        )
        production_plan_is_valid = production_plan_serializer.is_valid()

    if not production_plan_is_valid:
        production_plan_serializer.is_valid(raise_exception=True)

    repair_report = merge_production_plan_repair_reports(
        *repair_reports,
        provider_schema_repair_call_count=schema_repair_call_count,
        provider_dialogue_repair_call_count=dialogue_repair_call_count,
    )
    production_plan = production_plan_serializer.validated_data
    visual_world_model = build_visual_world_model(production_plan, settings.VIDEO_RENDER_FPS)

    storyboard_scenes = []
    storyboard_summary = ""
    shot_model = story_result["model"]
    shot_usages = []
    shot_batch_count = 0
    shot_batch_repair_call_count = 0
    previous_scene_context = {}
    beats = production_plan.get("beats") or []
    for batch_start in range(0, len(beats), SHOT_DIRECTOR_BATCH_SIZE):
        batch_beats = beats[batch_start:batch_start + SHOT_DIRECTOR_BATCH_SIZE]
        batch_plan = _build_shot_batch_plan(production_plan, batch_beats, visual_world_model)
        first_beat_no = batch_beats[0]["beat_no"]
        last_beat_no = batch_beats[-1]["beat_no"]
        shot_result = _call_video_ai_json(
            config,
            _build_shot_director_messages(
                project,
                scene_count,
                batch_plan,
                previous_scene_context,
            ),
            0.35,
            f"原子镜头导演 Agent（{first_beat_no}-{last_beat_no} / {scene_count}）",
            config["directing_timeout_seconds"],
        )
        shot_batch_count += 1
        shot_model = shot_result["model"]
        shot_usages.append(shot_result["usage"])
        usage_items.append(shot_result["usage"])
        validated_batch, batch_errors = _validate_shot_batch(
            shot_result["payload"],
            len(batch_beats),
            batch_plan,
        )

        if batch_errors:
            repair_result = _call_video_ai_json(
                config,
                _build_shot_batch_repair_messages(
                    project,
                    scene_count,
                    batch_plan,
                    previous_scene_context,
                    batch_errors,
                    shot_result["payload"],
                ),
                0.1,
                f"原子镜头批次修复 Agent（{first_beat_no}-{last_beat_no} / {scene_count}）",
                config["directing_timeout_seconds"],
            )
            shot_batch_repair_call_count += 1
            shot_model = repair_result["model"]
            shot_usages.append(repair_result["usage"])
            usage_items.append(repair_result["usage"])
            validated_batch, batch_errors = _validate_shot_batch(
                repair_result["payload"],
                len(batch_beats),
                batch_plan,
            )
            if batch_errors:
                raise ValidationError(batch_errors)

        if not storyboard_summary:
            storyboard_summary = validated_batch.get("summary") or ""
        storyboard_scenes.extend(validated_batch["scenes"])
        previous_scene_context = _build_previous_scene_context(validated_batch["scenes"][-1])

    stage_usage["shot_director"] = _merge_usage(*shot_usages)
    stage_usage["shot_director_batches"] = {
        "batch_size": SHOT_DIRECTOR_BATCH_SIZE,
        "batch_count": shot_batch_count,
        "repair_call_count": shot_batch_repair_call_count,
    }
    return {
        "storyboard": {
            "summary": storyboard_summary or production_plan.get("logline") or "",
            "scenes": storyboard_scenes,
        },
        "production_plan": production_plan,
        "repair_report": repair_report,
        "visual_world_model": visual_world_model,
        "workflow_version": WORKFLOW_VERSION,
        "model": shot_model,
        "usage": _merge_usage(*usage_items),
        "stage_usage": stage_usage,
        "provider_call_count": len(usage_items),
    }
