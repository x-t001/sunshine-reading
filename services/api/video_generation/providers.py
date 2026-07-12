import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.exceptions import ValidationError


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
    }


def get_video_ai_capabilities():
    config = get_video_ai_provider_config()
    return {
        "ai_storyboard_configured": config["configured"],
        "ai_storyboard_model": config["model"] if config["configured"] else "",
        "local_storyboard_available": True,
        "durable_storyboard_jobs_available": True,
    }


def _build_storyboard_messages(project, scene_count):
    system_prompt = (
        "你是短视频导演和分镜师。请把用户提供的故事改写成适合竖屏 9:16 短视频的结构化分镜。"
        "只返回 JSON 对象，不要使用 Markdown。根对象必须包含 summary 和 scenes。"
        "scenes 必须是数组，每个元素必须包含 title、visual_prompt、narration_text、subtitle_text、"
        "duration_seconds、camera_direction、mood。画面提示词应包含主体、环境、动作、光线和构图，"
        "避免抽象描述。旁白和字幕使用中文，字幕保持简短。"
    )
    user_prompt = (
        f"项目标题：{project.title}\n"
        f"目标时长：{project.duration_target} 秒\n"
        f"分镜数量：{scene_count}\n"
        f"视觉风格：{project.style_preset}\n"
        f"故事正文：\n{project.input_text}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_upstream_error(error):
    return f"AI 分镜服务请求失败，HTTP {error.code}。"


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


def call_video_ai_storyboard(project, scene_count):
    config = get_video_ai_provider_config()
    if not config["configured"]:
        raise ValidationError("服务端尚未配置 AI 分镜服务。")

    payload = {
        "model": config["model"],
        "messages": _build_storyboard_messages(project, scene_count),
        "temperature": 0.7,
        "stream": False,
        "response_format": {"type": "json_object"},
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
        raise ValidationError(_extract_upstream_error(error))
    except URLError:
        raise ValidationError("无法连接 AI 分镜服务，请稍后重试。")
    except TimeoutError:
        raise ValidationError("AI 分镜服务响应超时，请稍后重试。")
    except UnicodeDecodeError:
        raise ValidationError("AI 分镜服务返回了无法解析的响应。")

    try:
        result = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValidationError("AI 分镜服务返回了无法解析的响应。")

    choices = result.get("choices") or []
    if not choices:
        raise ValidationError("AI 分镜服务未返回可用结果。")
    content = (choices[0].get("message") or {}).get("content")
    if not content:
        raise ValidationError("AI 分镜服务返回内容为空。")

    return {
        "storyboard": _parse_json_content(content),
        "model": result.get("model") or config["model"],
        "usage": result.get("usage") or {},
    }
