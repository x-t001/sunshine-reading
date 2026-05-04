from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "nickname", "email", "role")
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "nickname", "email", "avatar", "bio", "role", "phone")
        read_only_fields = ("id", "username", "role")


class AdminUserListQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_banned = serializers.BooleanField(required=False)


class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "nickname",
            "email",
            "phone",
            "role",
            "is_banned",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class AdminUserDetailSerializer(AdminUserListSerializer):
    novel_count = serializers.IntegerField(read_only=True, default=0)
    comment_count = serializers.IntegerField(read_only=True, default=0)
    bookshelf_count = serializers.IntegerField(read_only=True, default=0)
    rating_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(AdminUserListSerializer.Meta):
        fields = AdminUserListSerializer.Meta.fields + (
            "avatar",
            "bio",
            "novel_count",
            "comment_count",
            "bookshelf_count",
            "rating_count",
        )


class AdminUserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class AdminUserBanSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class AdminUserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "nickname", "role", "is_banned", "is_active", "is_staff", "is_superuser")
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)
    nickname = serializers.CharField(max_length=64, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在。")
        return value

    def validate(self, attrs):
        password = attrs["password"]
        if password != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "两次输入的密码不一致。"})

        validate_password(password)
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            role=User.Role.READER,
            is_banned=False,
            **validated_data,
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError("用户名或密码错误。")
        if not user.is_active:
            raise serializers.ValidationError("用户已被禁用。")
        if user.is_banned:
            raise serializers.ValidationError("用户已被封禁，无法登录。")

        attrs["user"] = user
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except TokenError:
            raise serializers.ValidationError("refresh token 无效或已过期。")

        attrs["access"] = str(refresh.access_token)
        return attrs
