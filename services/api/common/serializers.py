from urllib.parse import urlparse

from rest_framework import serializers

from common.models import AuditLog


DEFAULT_AI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_AI_MODEL = "gpt-4o-mini"


class AuditLogReviewerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    nickname = serializers.CharField(read_only=True)


class AuditLogSerializer(serializers.ModelSerializer):
    reviewer = AuditLogReviewerSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "content_type",
            "object_id",
            "reviewer",
            "action",
            "from_status",
            "to_status",
            "reason",
            "created_at",
        )


class AiChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=("user", "assistant"))
    content = serializers.CharField(min_length=1, max_length=2000, trim_whitespace=True)


class AiChatContextSerializer(serializers.Serializer):
    novel_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    novel_description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    author_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    category_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    chapter_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    chapter_excerpt = serializers.CharField(max_length=4000, required=False, allow_blank=True)


class AiChatRequestSerializer(serializers.Serializer):
    api_key = serializers.CharField(min_length=1, max_length=500, trim_whitespace=True, write_only=True)
    api_url = serializers.URLField(max_length=500, required=False, default=DEFAULT_AI_API_URL)
    model = serializers.CharField(max_length=100, required=False, default=DEFAULT_AI_MODEL, allow_blank=False)
    messages = AiChatMessageSerializer(many=True)
    context = AiChatContextSerializer(required=False, default=dict)

    def validate_api_url(self, value):
        parsed = urlparse(value)
        if parsed.scheme != "https":
            raise serializers.ValidationError("API 地址必须使用 https。")
        if not parsed.netloc:
            raise serializers.ValidationError("API 地址不合法。")
        return value.rstrip("/")

    def validate_messages(self, value):
        if not value:
            raise serializers.ValidationError("消息不能为空。")
        if len(value) > 20:
            raise serializers.ValidationError("单次最多携带 20 条上下文消息。")
        return value
