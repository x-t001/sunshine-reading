from rest_framework import serializers

from .models import Category, Novel


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source="parent_id", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "sort_order")


class NovelAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    nickname = serializers.CharField(read_only=True)


class NovelCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class NovelListSerializer(serializers.ModelSerializer):
    author = NovelAuthorSerializer(read_only=True)
    category = NovelCategorySerializer(read_only=True)
    rating_score = serializers.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        model = Novel
        fields = (
            "id",
            "title",
            "author",
            "category",
            "cover",
            "description",
            "status",
            "word_count",
            "view_count",
            "collect_count",
            "comment_count",
            "rating_score",
            "latest_chapter_title",
            "latest_chapter_updated_at",
            "is_featured",
            "created_at",
            "updated_at",
        )


class NovelDetailSerializer(NovelListSerializer):
    class Meta(NovelListSerializer.Meta):
        fields = NovelListSerializer.Meta.fields + ("audit_status",)
