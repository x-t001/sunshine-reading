import re

from rest_framework import serializers

from .models import VideoProject, VideoScene


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
