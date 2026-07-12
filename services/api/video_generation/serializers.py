import re

from rest_framework import serializers

from chapters.models import Chapter
from users.permissions import is_admin_user

from .models import VideoGenerationJob, VideoProject, VideoScene


UNSAFE_TEXT_PATTERNS = (
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*/\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"\bon\w+\s*=", re.IGNORECASE),
    re.compile(r"<\s*(iframe|object|embed)", re.IGNORECASE),
)


class VideoProjectOwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    nickname = serializers.CharField(read_only=True)


class VideoSceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoScene
        fields = (
            "id",
            "scene_no",
            "title",
            "visual_prompt",
            "narration_text",
            "subtitle_text",
            "duration_seconds",
            "camera_direction",
            "mood",
            "status",
            "failure_reason",
            "created_at",
            "updated_at",
        )


class VideoProjectListSerializer(serializers.ModelSerializer):
    owner = VideoProjectOwnerSerializer(read_only=True)
    source_novel_id = serializers.IntegerField(read_only=True, allow_null=True)
    source_chapter_id = serializers.IntegerField(read_only=True, allow_null=True)
    scene_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VideoProject
        fields = (
            "id",
            "owner",
            "source_type",
            "source_novel_id",
            "source_chapter_id",
            "source_title",
            "title",
            "style_preset",
            "duration_target",
            "aspect_ratio",
            "status",
            "failure_reason",
            "scene_count",
            "created_at",
            "updated_at",
            "deleted_at",
        )


class VideoProjectDetailSerializer(VideoProjectListSerializer):
    scenes = VideoSceneSerializer(many=True, read_only=True)

    class Meta(VideoProjectListSerializer.Meta):
        fields = VideoProjectListSerializer.Meta.fields + (
            "summary",
            "input_text",
            "source_excerpt_hash",
            "scenes",
        )


class VideoProjectQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source_type = serializers.ChoiceField(choices=VideoProject.SourceType.choices, required=False)
    status = serializers.ChoiceField(choices=VideoProject.Status.choices, required=False)


class AdminVideoProjectQuerySerializer(VideoProjectQuerySerializer):
    owner_id = serializers.IntegerField(min_value=1, required=False)
    include_deleted = serializers.BooleanField(required=False, default=False)


class VideoProjectCreateSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=VideoProject.SourceType.choices, required=False, default=VideoProject.SourceType.TEXT)
    input_text = serializers.CharField(min_length=500, max_length=3000, trim_whitespace=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    style_preset = serializers.CharField(max_length=64, required=False, default="cinematic_story", allow_blank=False)
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)
    aspect_ratio = serializers.ChoiceField(choices=("9:16",), required=False, default="9:16")

    def validate_input_text(self, value):
        for pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                raise serializers.ValidationError("Input text contains unsafe HTML or script content.")
        return value

    def validate(self, attrs):
        if attrs["source_type"] != VideoProject.SourceType.TEXT:
            raise serializers.ValidationError({"source_type": ["Only pasted text projects are supported in this iteration."]})
        return attrs


class VideoProjectStoryboardSerializer(serializers.Serializer):
    scene_count = serializers.IntegerField(min_value=4, max_value=8, required=False)


class VideoSourceChapterQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)


class VideoSourceChapterSerializer(serializers.ModelSerializer):
    novel_id = serializers.IntegerField(read_only=True)
    novel_title = serializers.CharField(source="novel.title", read_only=True)
    source_access = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            "id",
            "novel_id",
            "novel_title",
            "title",
            "chapter_number",
            "word_count",
            "status",
            "audit_status",
            "source_access",
            "published_at",
            "updated_at",
        )

    def get_source_access(self, obj):
        user = self.context.get("user")
        if is_admin_user(user):
            return "admin"
        if obj.novel.author_id == getattr(user, "id", None):
            return "owned"
        return "public"


class VideoProjectChapterCreateSerializer(serializers.Serializer):
    chapter_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    style_preset = serializers.CharField(max_length=64, required=False, default="cinematic_story", allow_blank=False)
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)
    aspect_ratio = serializers.ChoiceField(choices=("9:16",), required=False, default="9:16")


class VideoGenerationJobSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = VideoGenerationJob
        fields = (
            "id",
            "project_id",
            "job_type",
            "status",
            "provider",
            "model_name",
            "request_payload",
            "attempt_count",
            "max_attempts",
            "can_retry",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_can_retry(self, obj):
        return obj.status == VideoGenerationJob.Status.FAILED and obj.attempt_count < obj.max_attempts


class VideoAiStoryboardSceneSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, trim_whitespace=True)
    visual_prompt = serializers.CharField(max_length=2000, trim_whitespace=True)
    narration_text = serializers.CharField(max_length=2000, allow_blank=True, trim_whitespace=True)
    subtitle_text = serializers.CharField(max_length=500, allow_blank=True, trim_whitespace=True)
    duration_seconds = serializers.IntegerField(min_value=1, max_value=30)
    camera_direction = serializers.CharField(max_length=200, allow_blank=True, trim_whitespace=True)
    mood = serializers.CharField(max_length=100, allow_blank=True, trim_whitespace=True)

    def validate(self, attrs):
        for field_name, value in attrs.items():
            if not isinstance(value, str):
                continue
            for pattern in UNSAFE_TEXT_PATTERNS:
                if pattern.search(value):
                    raise serializers.ValidationError({field_name: ["AI scene contains unsafe HTML or script content."]})
        return attrs


class VideoAiStoryboardResultSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)
    scenes = VideoAiStoryboardSceneSerializer(many=True)

    def validate_summary(self, value):
        for pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                raise serializers.ValidationError("AI summary contains unsafe HTML or script content.")
        return value

    def validate_scenes(self, value):
        expected_scene_count = self.context.get("expected_scene_count")
        if expected_scene_count is not None and len(value) != expected_scene_count:
            raise serializers.ValidationError(f"AI storyboard must contain exactly {expected_scene_count} scenes.")
        return value


class VideoSceneUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    visual_prompt = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    narration_text = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    subtitle_text = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)
    duration_seconds = serializers.IntegerField(min_value=1, max_value=30, required=False)
    camera_direction = serializers.CharField(max_length=200, required=False, allow_blank=True, trim_whitespace=True)
    mood = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one editable scene field is required.")

        for field_name in ("title", "visual_prompt", "narration_text", "subtitle_text", "camera_direction", "mood"):
            value = attrs.get(field_name)
            if value is None:
                continue
            for pattern in UNSAFE_TEXT_PATTERNS:
                if pattern.search(value):
                    raise serializers.ValidationError({field_name: ["Field contains unsafe HTML or script content."]})
        return attrs


class VideoStoryDraftSerializer(serializers.Serializer):
    GENRE_CHOICES = (
        ("fantasy", "Fantasy"),
        ("urban", "Urban"),
        ("romance", "Romance"),
        ("sci_fi", "Sci-fi"),
        ("mystery", "Mystery"),
        ("history", "History"),
    )
    TONE_CHOICES = (
        ("cinematic", "Cinematic"),
        ("warm", "Warm"),
        ("suspense", "Suspense"),
        ("high_energy", "High energy"),
        ("sad", "Sad"),
    )

    prompt = serializers.CharField(min_length=10, max_length=300, trim_whitespace=True)
    protagonist = serializers.CharField(max_length=80, required=False, allow_blank=True, trim_whitespace=True)
    key_conflict = serializers.CharField(max_length=160, required=False, allow_blank=True, trim_whitespace=True)
    genre = serializers.ChoiceField(choices=GENRE_CHOICES, required=False, default="fantasy")
    tone = serializers.ChoiceField(choices=TONE_CHOICES, required=False, default="cinematic")
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)

    def validate_prompt(self, value):
        for pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                raise serializers.ValidationError("Prompt contains unsafe HTML or script content.")
        return value
