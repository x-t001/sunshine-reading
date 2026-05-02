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
