from rest_framework import serializers

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
