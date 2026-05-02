from rest_framework import serializers

from chapters.serializers import ChapterCatalogSerializer
from novels.serializers import NovelListSerializer

from .models import Bookshelf, ReadingHistory


class BookshelfItemSerializer(serializers.ModelSerializer):
    novel = NovelListSerializer(read_only=True)
    last_read_chapter = ChapterCatalogSerializer(read_only=True)
    joined_at = serializers.DateTimeField(source="created_at", read_only=True)
    reading_progress = serializers.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        model = Bookshelf
        fields = (
            "id",
            "novel",
            "last_read_chapter",
            "reading_progress",
            "joined_at",
            "last_read_at",
        )


class AddBookshelfSerializer(serializers.Serializer):
    novel_id = serializers.IntegerField(min_value=1)


class BookshelfCheckSerializer(serializers.Serializer):
    novel_id = serializers.IntegerField(min_value=1)


class ReadingHistorySerializer(serializers.ModelSerializer):
    novel = NovelListSerializer(read_only=True)
    chapter = ChapterCatalogSerializer(read_only=True)

    class Meta:
        model = ReadingHistory
        fields = (
            "id",
            "novel",
            "chapter",
            "reading_position",
            "read_at",
        )


class ReportReadingHistorySerializer(serializers.Serializer):
    novel_id = serializers.IntegerField(min_value=1)
    chapter_id = serializers.IntegerField(min_value=1)
    reading_position = serializers.IntegerField(min_value=0, max_value=999)
