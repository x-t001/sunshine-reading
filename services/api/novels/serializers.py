from rest_framework import serializers

from common.models import AuditLog
from common.serializers import AuditLogSerializer

from .models import Category, Novel, NovelRating


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.IntegerField(source="parent_id", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "sort_order")


class AdminCategoryParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class AdminCategorySerializer(serializers.ModelSerializer):
    parent = AdminCategoryParentSerializer(read_only=True)
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, allow_null=True)
    children_count = serializers.IntegerField(read_only=True)
    novel_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "parent",
            "parent_id",
            "parent_name",
            "sort_order",
            "is_active",
            "children_count",
            "novel_count",
            "created_at",
            "updated_at",
        )


class AdminCategoryQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    parent_id = serializers.IntegerField(min_value=1, required=False)


class AdminCategoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    slug = serializers.SlugField(max_length=120)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="parent",
        required=False,
        allow_null=True,
    )
    sort_order = serializers.IntegerField(min_value=0, required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_slug(self, value):
        if Category.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Category slug already exists.")
        return value


class AdminCategoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    slug = serializers.SlugField(max_length=120, required=False)
    parent_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="parent",
        required=False,
        allow_null=True,
    )
    sort_order = serializers.IntegerField(min_value=0, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_slug(self, value):
        category = self.context.get("category")
        queryset = Category.objects.filter(slug=value)
        if category is not None:
            queryset = queryset.exclude(id=category.id)
        if queryset.exists():
            raise serializers.ValidationError("Category slug already exists.")
        return value


class AdminCategoryStatusUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


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
            "rating_count",
            "latest_chapter_title",
            "latest_chapter_updated_at",
            "is_featured",
            "created_at",
            "updated_at",
        )


class NovelDetailSerializer(NovelListSerializer):
    class Meta(NovelListSerializer.Meta):
        fields = NovelListSerializer.Meta.fields + ("audit_status",)


class AuthorNovelListSerializer(serializers.ModelSerializer):
    category = NovelCategorySerializer(read_only=True)
    rating_score = serializers.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        model = Novel
        fields = (
            "id",
            "title",
            "cover",
            "category",
            "status",
            "audit_status",
            "word_count",
            "view_count",
            "collect_count",
            "comment_count",
            "rating_score",
            "rating_count",
            "latest_chapter_title",
            "latest_chapter_updated_at",
            "created_at",
            "updated_at",
        )


class AuthorNovelDetailSerializer(AuthorNovelListSerializer):
    author = NovelAuthorSerializer(read_only=True)
    chapter_count = serializers.SerializerMethodField()
    audit_logs = serializers.SerializerMethodField()

    class Meta(AuthorNovelListSerializer.Meta):
        fields = AuthorNovelListSerializer.Meta.fields + ("author", "description", "chapter_count", "audit_logs")

    def get_chapter_count(self, obj):
        if hasattr(obj, "chapter_count"):
            return obj.chapter_count
        return obj.chapters.count()

    def get_audit_logs(self, obj):
        return AuditLogSerializer(self.context.get("audit_logs", []), many=True).data


class AuthorNovelCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        source="category",
    )
    cover = serializers.URLField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Novel.Status.choices, required=False, default=Novel.Status.SERIALIZING)

    def validate_status(self, value):
        if value == Novel.Status.REMOVED:
            raise serializers.ValidationError("New novels cannot be created as removed.")
        return value


class AuthorNovelUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        source="category",
        required=False,
    )
    cover = serializers.URLField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Novel.Status.choices, required=False)


class AuthorNovelSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Novel
        fields = ("id", "audit_status")


class AdminNovelListSerializer(serializers.ModelSerializer):
    author = NovelAuthorSerializer(read_only=True)
    category = NovelCategorySerializer(read_only=True)
    reviewer = NovelAuthorSerializer(read_only=True)
    rating_score = serializers.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        model = Novel
        fields = (
            "id",
            "title",
            "cover",
            "author",
            "category",
            "reviewer",
            "status",
            "audit_status",
            "reviewed_at",
            "word_count",
            "view_count",
            "collect_count",
            "comment_count",
            "rating_score",
            "rating_count",
            "latest_chapter_title",
            "latest_chapter_updated_at",
            "created_at",
            "updated_at",
        )


class AdminNovelDetailSerializer(AdminNovelListSerializer):
    chapter_count = serializers.SerializerMethodField()

    class Meta(AdminNovelListSerializer.Meta):
        fields = AdminNovelListSerializer.Meta.fields + ("description", "is_featured", "chapter_count")

    def get_chapter_count(self, obj):
        if hasattr(obj, "chapter_count"):
            return obj.chapter_count
        return obj.chapters.count()


class AdminNovelManagementSerializer(serializers.ModelSerializer):
    author = NovelAuthorSerializer(read_only=True)
    author_id = serializers.IntegerField(read_only=True)
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_nickname = serializers.CharField(source="author.nickname", read_only=True)
    category = NovelCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(read_only=True, allow_null=True)
    rating_score = serializers.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        model = Novel
        fields = (
            "id",
            "title",
            "author",
            "author_id",
            "author_username",
            "author_nickname",
            "category",
            "category_id",
            "status",
            "audit_status",
            "word_count",
            "view_count",
            "collect_count",
            "comment_count",
            "rating_score",
            "rating_count",
            "is_featured",
            "created_at",
            "updated_at",
            "latest_chapter_title",
            "latest_chapter_updated_at",
        )


class AdminNovelManagementDetailSerializer(AdminNovelManagementSerializer):
    reviewer = NovelAuthorSerializer(read_only=True)
    chapter_count = serializers.SerializerMethodField()

    class Meta(AdminNovelManagementSerializer.Meta):
        fields = AdminNovelManagementSerializer.Meta.fields + (
            "cover",
            "description",
            "reviewer",
            "reviewed_at",
            "chapter_count",
        )

    def get_chapter_count(self, obj):
        if hasattr(obj, "chapter_count"):
            return obj.chapter_count
        return obj.chapters.count()


class AdminNovelManagementQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Novel.Status.choices, required=False)
    audit_status = serializers.ChoiceField(choices=Novel.AuditStatus.choices, required=False)
    author_id = serializers.IntegerField(min_value=1, required=False)


class AdminNovelStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Novel.Status.choices)


class AdminNovelFeaturedUpdateSerializer(serializers.Serializer):
    is_featured = serializers.BooleanField()


class AdminNovelReviewSerializer(serializers.ModelSerializer):
    reviewer = NovelAuthorSerializer(read_only=True)

    class Meta:
        model = Novel
        fields = ("id", "title", "status", "audit_status", "reviewer", "reviewed_at", "updated_at")


class AdminNovelRejectInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class AdminNovelPendingQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)


class ReviewerRejectInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, allow_blank=False, trim_whitespace=True)


class ReviewerAuditLogQuerySerializer(serializers.Serializer):
    content_type = serializers.ChoiceField(choices=AuditLog.ContentType.choices, required=False)
    action = serializers.ChoiceField(choices=AuditLog.Action.choices, required=False)


class ReviewerAuditLogSerializer(serializers.ModelSerializer):
    reviewer = NovelAuthorSerializer(read_only=True)

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


class NovelRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NovelRating
        fields = ("score", "comment")


class NovelRatingInputSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)


class NovelRatingSummarySerializer(serializers.Serializer):
    novel_id = serializers.IntegerField()
    rating_score = serializers.FloatField()
    rating_count = serializers.IntegerField()
    my_rating = NovelRatingSerializer(allow_null=True)
