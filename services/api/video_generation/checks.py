from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security)
def check_video_ai_provider_settings(app_configs, **kwargs):
    api_key = settings.VIDEO_AI_API_KEY
    if not api_key:
        return []

    errors = []
    api_url = settings.VIDEO_AI_API_URL
    parsed_url = urlparse(api_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        errors.append(
            Error(
                "VIDEO_AI_API_URL must be an absolute HTTPS URL when VIDEO_AI_API_KEY is configured.",
                hint="Set the provider endpoint in the server environment; never put the key in the URL.",
                id="video_generation.E001",
            )
        )

    if not settings.VIDEO_AI_MODEL:
        errors.append(
            Error(
                "VIDEO_AI_MODEL must be configured when VIDEO_AI_API_KEY is configured.",
                hint="Set a provider-supported model name in the server environment.",
                id="video_generation.E002",
            )
        )

    return errors
