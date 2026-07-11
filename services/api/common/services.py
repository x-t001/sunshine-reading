import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rest_framework.exceptions import ValidationError

from .models import AuditLog


AI_CHAT_TIMEOUT_SECONDS = 30


def _format_audit_reason(reason):
    if reason is None:
        return ""
    if isinstance(reason, str):
        return reason
    return json.dumps(reason, ensure_ascii=False, default=str)


def create_operation_audit_log(*, content_type, object_id, actor=None, action, from_status="", to_status="", reason=""):
    if object_id is None:
        return None

    return AuditLog.objects.create(
        content_type=content_type,
        object_id=object_id,
        reviewer=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        from_status=str(from_status or ""),
        to_status=str(to_status or ""),
        reason=_format_audit_reason(reason),
    )


def _trim_text(value, limit):
    if not value:
        return ""
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _build_system_prompt(context):
    lines = [
        "你是阳光阅读的小说智能助手。",
        "请优先依据当前提供的小说和章节上下文回答。",
        "如果上下文不足以确定答案，请明确说明无法从当前内容判断，不要编造剧情。",
        "回答使用中文，保持清晰、简洁、适合读者阅读。",
        "",
        "当前上下文：",
    ]

    context_mapping = [
        ("小说标题", context.get("novel_title")),
        ("作者", context.get("author_name")),
        ("分类", context.get("category_name")),
        ("小说简介", _trim_text(context.get("novel_description"), 1200)),
        ("当前章节", context.get("chapter_title")),
        ("章节摘录", _trim_text(context.get("chapter_excerpt"), 3000)),
    ]
    for label, value in context_mapping:
        if value:
            lines.append(f"{label}：{value}")

    return "\n".join(lines)


def _extract_upstream_error(error):
    try:
        body = error.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""

    if not body:
        return f"大模型接口请求失败，HTTP {error.code}。"

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return f"大模型接口请求失败，HTTP {error.code}。"

    detail = payload.get("error")
    if isinstance(detail, dict):
        return detail.get("message") or f"大模型接口请求失败，HTTP {error.code}。"
    if isinstance(detail, str):
        return detail
    return f"大模型接口请求失败，HTTP {error.code}。"


def call_ai_chat_completion(*, api_url, api_key, model, messages, context):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _build_system_prompt(context or {})},
            *messages,
        ],
        "temperature": 0.7,
        "stream": False,
    }

    request = Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=AI_CHAT_TIMEOUT_SECONDS) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        raise ValidationError(_extract_upstream_error(error))
    except URLError:
        raise ValidationError("无法连接大模型接口，请检查 API 地址和网络。")
    except TimeoutError:
        raise ValidationError("大模型接口响应超时，请稍后重试。")

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError:
        raise ValidationError("大模型接口返回了无法解析的响应。")

    choices = result.get("choices") or []
    if not choices:
        raise ValidationError("大模型接口未返回可用回答。")

    message = choices[0].get("message") or {}
    answer = message.get("content")
    if not answer:
        raise ValidationError("大模型接口返回内容为空。")

    return {
        "answer": answer,
        "model": result.get("model") or model,
        "usage": result.get("usage"),
    }
