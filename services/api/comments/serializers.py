from rest_framework import serializers

from .models import Comment


class CommentUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    nickname = serializers.CharField(read_only=True)
    avatar = serializers.CharField(read_only=True)


class CommentReplySerializer(serializers.ModelSerializer):
    user = CommentUserSerializer(read_only=True)
    novel_id = serializers.IntegerField(read_only=True)
    parent_id = serializers.IntegerField(read_only=True)
    chapter_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Comment
        fields = (
            "id",
            "user",
            "novel_id",
            "chapter_id",
            "parent_id",
            "content",
            "like_count",
            "created_at",
            "updated_at",
        )


class CommentSerializer(CommentReplySerializer):
    replies = serializers.SerializerMethodField()

    class Meta(CommentReplySerializer.Meta):
        fields = CommentReplySerializer.Meta.fields + ("replies",)

    def get_replies(self, obj):
        replies = getattr(obj, "normal_replies", None)
        if replies is None:
            replies = obj.replies.filter(status=Comment.Status.NORMAL).select_related("user").order_by("created_at")
        return CommentReplySerializer(replies[:3], many=True).data


class CreateCommentSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=1000, trim_whitespace=True)
    parent_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    chapter_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
