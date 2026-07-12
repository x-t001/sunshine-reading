from django.contrib import admin

from .models import VideoGenerationJob, VideoProject, VideoScene


class VideoSceneInline(admin.TabularInline):
    model = VideoScene
    extra = 0
    fields = ("scene_no", "title", "duration_seconds", "status", "mood")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "source_type", "status", "duration_target", "aspect_ratio", "created_at")
    list_filter = ("source_type", "status", "aspect_ratio", "created_at")
    search_fields = ("title", "source_title", "owner__username", "owner__nickname")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "deleted_at", "source_excerpt_hash")
    inlines = (VideoSceneInline,)
    fieldsets = (
        ("Project", {"fields": ("owner", "title", "summary", "style_preset", "duration_target", "aspect_ratio")}),
        ("Source", {"fields": ("source_type", "source_novel", "source_chapter", "source_title", "source_excerpt_hash", "input_text")}),
        ("Status", {"fields": ("status", "failure_reason", "deleted_at")}),
        ("Time", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(VideoScene)
class VideoSceneAdmin(admin.ModelAdmin):
    list_display = ("project", "scene_no", "title", "duration_seconds", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("project__title", "title", "visual_prompt", "narration_text", "subtitle_text")
    ordering = ("project", "scene_no")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VideoGenerationJob)
class VideoGenerationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "job_type", "status", "attempt_count", "max_attempts", "model_name", "created_at")
    list_filter = ("job_type", "status", "provider", "created_at")
    search_fields = ("project__title", "project__owner__username", "model_name", "error_message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "started_at", "finished_at")
