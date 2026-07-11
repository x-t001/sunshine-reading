from rest_framework import serializers

from novels.models import Novel
from novels.serializers import NovelListSerializer

from .models import RankingItem, RankingType


class RankingItemSerializer(serializers.ModelSerializer):
    novel = NovelListSerializer(read_only=True)
    score = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = RankingItem
        fields = ("rank", "score", "calculated_at", "novel")


class RankingTypeSerializer(serializers.ModelSerializer):
    items = RankingItemSerializer(source="public_items", many=True, read_only=True)

    class Meta:
        model = RankingType
        fields = ("id", "name", "code", "description", "items")


class AdminRankingTypeSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RankingType
        fields = (
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "item_count",
            "created_at",
            "updated_at",
        )


class AdminRankingTypeQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class AdminRankingTypeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    code = serializers.SlugField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_code(self, value):
        if RankingType.objects.filter(code=value).exists():
            raise serializers.ValidationError("Ranking type code already exists.")
        return value


class AdminRankingTypeUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    code = serializers.SlugField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def validate_code(self, value):
        ranking_type = self.context.get("ranking_type")
        queryset = RankingType.objects.filter(code=value)
        if ranking_type is not None:
            queryset = queryset.exclude(id=ranking_type.id)
        if queryset.exists():
            raise serializers.ValidationError("Ranking type code already exists.")
        return value


class AdminRankingTypeStatusUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class AdminRankingNovelSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)


class AdminRankingItemSerializer(serializers.ModelSerializer):
    ranking_type = AdminRankingTypeSerializer(read_only=True)
    ranking_type_id = serializers.IntegerField(read_only=True)
    novel = AdminRankingNovelSerializer(read_only=True)
    novel_id = serializers.IntegerField(read_only=True)
    novel_title = serializers.CharField(source="novel.title", read_only=True)
    score = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = RankingItem
        fields = (
            "id",
            "ranking_type",
            "ranking_type_id",
            "novel",
            "novel_id",
            "novel_title",
            "score",
            "rank",
            "calculated_at",
            "created_at",
            "updated_at",
        )


class AdminRankingItemQuerySerializer(serializers.Serializer):
    ranking_type_id = serializers.IntegerField(min_value=1, required=False)
    novel_id = serializers.IntegerField(min_value=1, required=False)
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)


class AdminRankingItemCreateSerializer(serializers.Serializer):
    ranking_type_id = serializers.PrimaryKeyRelatedField(
        queryset=RankingType.objects.all(),
        source="ranking_type",
    )
    novel_id = serializers.PrimaryKeyRelatedField(
        queryset=Novel.objects.filter(
            audit_status=Novel.AuditStatus.APPROVED,
        ).exclude(status=Novel.Status.REMOVED),
        source="novel",
    )
    score = serializers.DecimalField(max_digits=12, decimal_places=2)
    rank = serializers.IntegerField(min_value=1)
    calculated_at = serializers.DateTimeField(required=False)


class AdminRankingItemUpdateSerializer(serializers.Serializer):
    ranking_type_id = serializers.PrimaryKeyRelatedField(
        queryset=RankingType.objects.all(),
        source="ranking_type",
        required=False,
    )
    novel_id = serializers.PrimaryKeyRelatedField(
        queryset=Novel.objects.filter(
            audit_status=Novel.AuditStatus.APPROVED,
        ).exclude(status=Novel.Status.REMOVED),
        source="novel",
        required=False,
    )
    score = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    rank = serializers.IntegerField(min_value=1, required=False)
    calculated_at = serializers.DateTimeField(required=False)
