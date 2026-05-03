from rest_framework import serializers

from novels.serializers import NovelListSerializer

from .models import Chapter


class ChapterCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = (
            "id",
            "title",
            "chapter_number",
            "word_count",
            "is_free",
            "published_at",
        )


class ChapterDetailSerializer(serializers.ModelSerializer):
    novel = NovelListSerializer(read_only=True)
    previous_chapter_id = serializers.IntegerField(read_only=True)
    next_chapter_id = serializers.IntegerField(read_only=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        model = Chapter
        fields = (
            "id",
            "title",
            "chapter_number",
            "content",
            "word_count",
            "is_free",
            "price",
            "published_at",
            "novel",
            "previous_chapter_id",
            "next_chapter_id",
        )


class AuthorChapterListSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        model = Chapter
        fields = (
            "id",
            "title",
            "chapter_number",
            "word_count",
            "is_free",
            "price",
            "status",
            "audit_status",
            "published_at",
            "created_at",
            "updated_at",
        )


class AuthorChapterDetailSerializer(AuthorChapterListSerializer):
    novel_id = serializers.IntegerField(source="novel.id", read_only=True)
    novel_title = serializers.CharField(source="novel.title", read_only=True)

    class Meta(AuthorChapterListSerializer.Meta):
        fields = AuthorChapterListSerializer.Meta.fields + ("novel_id", "novel_title", "content")


class AuthorChapterCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    chapter_number = serializers.IntegerField(min_value=1)
    content = serializers.CharField(allow_blank=False)
    is_free = serializers.BooleanField(required=False, default=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0, required=False, default="0.00")


class AuthorChapterUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    chapter_number = serializers.IntegerField(min_value=1, required=False)
    content = serializers.CharField(allow_blank=False, required=False)
    is_free = serializers.BooleanField(required=False)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0, required=False)
    status = serializers.ChoiceField(choices=Chapter.Status.choices, required=False)


class AuthorChapterSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ("id", "status", "audit_status")
