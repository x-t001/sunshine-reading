import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parents[1]

load_dotenv(PROJECT_ROOT / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-env")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"

allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [item.strip() for item in allowed_hosts.split(",") if item.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "common",
    "users",
    "novels",
    "chapters",
    "bookshelf",
    "comments",
    "rankings",
    "search",
    "video_generation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://sunshine_user:sunshine_password@localhost:5432/sunshine_reading",
)
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_ROOT = PROJECT_ROOT / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

cors_allow_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOWED_ORIGINS = [item.strip() for item in cors_allow_origins.split(",") if item.strip()]

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "sunshine-reading")

VIDEO_AI_API_URL = os.getenv("VIDEO_AI_API_URL", "").strip().rstrip("/")
VIDEO_AI_API_KEY = os.getenv("VIDEO_AI_API_KEY", "").strip()
VIDEO_AI_MODEL = os.getenv("VIDEO_AI_MODEL", "gpt-4o-mini").strip()
VIDEO_AI_TIMEOUT_SECONDS = max(5, int(os.getenv("VIDEO_AI_TIMEOUT_SECONDS", "60")))
VIDEO_AI_PLANNING_TIMEOUT_SECONDS = max(
    VIDEO_AI_TIMEOUT_SECONDS,
    int(os.getenv("VIDEO_AI_PLANNING_TIMEOUT_SECONDS", "180")),
)
VIDEO_AI_DIRECTING_TIMEOUT_SECONDS = max(
    VIDEO_AI_TIMEOUT_SECONDS,
    int(os.getenv("VIDEO_AI_DIRECTING_TIMEOUT_SECONDS", "180")),
)
VIDEO_AI_THINKING_TYPE = os.getenv("VIDEO_AI_THINKING_TYPE", "").strip().lower()
if VIDEO_AI_THINKING_TYPE not in ("", "enabled", "disabled"):
    VIDEO_AI_THINKING_TYPE = ""
VIDEO_IMAGE_API_URL = os.getenv(
    "VIDEO_IMAGE_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/images/generations",
).strip()
VIDEO_IMAGE_API_KEY = os.getenv("VIDEO_IMAGE_API_KEY", VIDEO_AI_API_KEY).strip()
VIDEO_IMAGE_MODEL = os.getenv("VIDEO_IMAGE_MODEL", "glm-image").strip()
VIDEO_IMAGE_SIZE = os.getenv("VIDEO_IMAGE_SIZE", "960x1728").strip()
VIDEO_IMAGE_TIMEOUT_SECONDS = max(10, int(os.getenv("VIDEO_IMAGE_TIMEOUT_SECONDS", "90")))
VIDEO_IMAGE_DAILY_JOB_LIMIT = max(1, int(os.getenv("VIDEO_IMAGE_DAILY_JOB_LIMIT", "3")))
VIDEO_CLIP_API_URL = os.getenv(
    "VIDEO_CLIP_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/videos/generations",
).strip()
VIDEO_CLIP_RESULT_API_URL = os.getenv(
    "VIDEO_CLIP_RESULT_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/async-result/{task_id}",
).strip()
VIDEO_CLIP_API_KEY = os.getenv("VIDEO_CLIP_API_KEY", VIDEO_AI_API_KEY).strip()
VIDEO_CLIP_MODEL = os.getenv("VIDEO_CLIP_MODEL", "cogvideox-flash").strip()
VIDEO_CLIP_SIZE = os.getenv("VIDEO_CLIP_SIZE", "1080x1920").strip()
VIDEO_CLIP_DURATION_SECONDS = 10 if int(os.getenv("VIDEO_CLIP_DURATION_SECONDS", "5")) == 10 else 5
VIDEO_CLIP_FPS = 60 if int(os.getenv("VIDEO_CLIP_FPS", "30")) == 60 else 30
VIDEO_CLIP_WITH_AUDIO = os.getenv("VIDEO_CLIP_WITH_AUDIO", "false").lower() == "true"
VIDEO_CLIP_USE_SCENE_IMAGE = os.getenv("VIDEO_CLIP_USE_SCENE_IMAGE", "true").lower() == "true"
VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME = (
    os.getenv("VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME", "true").lower() == "true"
)
VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES = min(
    5 * 1024 * 1024,
    max(256 * 1024, int(os.getenv("VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES", str(5 * 1024 * 1024)))),
)
VIDEO_CLIP_TAIL_FRAME_TIMEOUT_SECONDS = max(
    5,
    int(os.getenv("VIDEO_CLIP_TAIL_FRAME_TIMEOUT_SECONDS", "30")),
)
VIDEO_CLIP_REQUEST_TIMEOUT_SECONDS = max(10, int(os.getenv("VIDEO_CLIP_REQUEST_TIMEOUT_SECONDS", "30")))
VIDEO_CLIP_POLL_INTERVAL_SECONDS = max(1, int(os.getenv("VIDEO_CLIP_POLL_INTERVAL_SECONDS", "5")))
VIDEO_CLIP_MAX_WAIT_SECONDS = max(30, int(os.getenv("VIDEO_CLIP_MAX_WAIT_SECONDS", "900")))
VIDEO_CLIP_MAX_FILE_BYTES = min(
    200 * 1024 * 1024,
    max(1024 * 1024, int(os.getenv("VIDEO_CLIP_MAX_FILE_BYTES", str(100 * 1024 * 1024)))),
)
VIDEO_CLIP_DAILY_JOB_LIMIT = max(1, int(os.getenv("VIDEO_CLIP_DAILY_JOB_LIMIT", "1")))
VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT = max(
    1,
    int(os.getenv("VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT", "6")),
)
VIDEO_VISUAL_REGENERATION_PER_SCENE_LIMIT = max(
    1,
    int(os.getenv("VIDEO_VISUAL_REGENERATION_PER_SCENE_LIMIT", "2")),
)
VIDEO_TTS_API_URL = os.getenv(
    "VIDEO_TTS_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/audio/speech",
).strip()
VIDEO_TTS_API_KEY = os.getenv("VIDEO_TTS_API_KEY", VIDEO_AI_API_KEY).strip()
VIDEO_TTS_MODEL = os.getenv("VIDEO_TTS_MODEL", "glm-tts").strip()
VIDEO_TTS_VOICE = os.getenv("VIDEO_TTS_VOICE", "tongtong").strip()
VIDEO_TTS_SPEED = min(2.0, max(0.5, float(os.getenv("VIDEO_TTS_SPEED", "1.0"))))
VIDEO_TTS_VOLUME = min(10.0, max(0.1, float(os.getenv("VIDEO_TTS_VOLUME", "1.0"))))
VIDEO_TTS_TIMEOUT_SECONDS = max(10, int(os.getenv("VIDEO_TTS_TIMEOUT_SECONDS", "90")))
VIDEO_TTS_DAILY_JOB_LIMIT = max(1, int(os.getenv("VIDEO_TTS_DAILY_JOB_LIMIT", "5")))
VIDEO_ASR_ENABLED = os.getenv("VIDEO_ASR_ENABLED", "false").lower() == "true"
VIDEO_ASR_API_URL = os.getenv(
    "VIDEO_ASR_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions",
).strip()
VIDEO_ASR_API_KEY = os.getenv("VIDEO_ASR_API_KEY", VIDEO_TTS_API_KEY).strip()
VIDEO_ASR_MODEL = os.getenv("VIDEO_ASR_MODEL", "glm-asr-2512").strip()
VIDEO_ASR_TIMEOUT_SECONDS = max(10, int(os.getenv("VIDEO_ASR_TIMEOUT_SECONDS", "60")))
VIDEO_ASR_MIN_SIMILARITY = min(1.0, max(0.5, float(os.getenv("VIDEO_ASR_MIN_SIMILARITY", "0.75"))))
VIDEO_ASSET_MAX_FILE_BYTES = min(
    100 * 1024 * 1024,
    max(1024 * 1024, int(os.getenv("VIDEO_ASSET_MAX_FILE_BYTES", str(25 * 1024 * 1024)))),
)
VIDEO_RENDER_ENABLED = os.getenv("VIDEO_RENDER_ENABLED", "true").lower() == "true"
VIDEO_RENDER_WIDTH = min(2160, max(360, int(os.getenv("VIDEO_RENDER_WIDTH", "720"))))
VIDEO_RENDER_HEIGHT = min(3840, max(640, int(os.getenv("VIDEO_RENDER_HEIGHT", "1280"))))
VIDEO_RENDER_FPS = min(60, max(24, int(os.getenv("VIDEO_RENDER_FPS", "30"))))
VIDEO_RENDER_CRF = min(30, max(16, int(os.getenv("VIDEO_RENDER_CRF", "21"))))
VIDEO_RENDER_TIMEOUT_SECONDS = max(60, int(os.getenv("VIDEO_RENDER_TIMEOUT_SECONDS", "600")))
VIDEO_RENDER_MAX_FILE_BYTES = min(
    1024 * 1024 * 1024,
    max(10 * 1024 * 1024, int(os.getenv("VIDEO_RENDER_MAX_FILE_BYTES", str(500 * 1024 * 1024)))),
)
VIDEO_JOB_MAX_ATTEMPTS = min(5, max(1, int(os.getenv("VIDEO_JOB_MAX_ATTEMPTS", "3"))))
VIDEO_JOB_POLL_INTERVAL_SECONDS = max(1, int(os.getenv("VIDEO_JOB_POLL_INTERVAL_SECONDS", "2")))
VIDEO_JOB_STALE_SECONDS = max(60, int(os.getenv("VIDEO_JOB_STALE_SECONDS", "300")))
