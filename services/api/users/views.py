from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .permissions import IsAdminUser, IsAuthenticatedAndNotBanned
from .selectors import get_admin_user_by_id, get_admin_users
from .serializers import (
    AdminUserBanSerializer,
    AdminUserDetailSerializer,
    AdminUserListQuerySerializer,
    AdminUserListSerializer,
    AdminUserRoleUpdateSerializer,
    AdminUserStatusSerializer,
    LoginSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    UserBasicSerializer,
    UserProfileSerializer,
)
from .services import ban_user, unban_user, update_user_role


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return success_response(UserBasicSerializer(user).data)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return success_response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserBasicSerializer(user).data,
            }
        )


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response({"access": serializer.validated_data["access"]})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticatedAndNotBanned]

    def get(self, request):
        return success_response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data)


class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query_serializer = AdminUserListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        paginator = PublicPageNumberPagination()
        queryset = get_admin_users(query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminUserListSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, id):
        user = get_admin_user_by_id(id)
        if user is None:
            raise NotFound("用户不存在。")
        return user

    def get(self, request, id):
        user = self.get_object(id)
        return success_response(AdminUserDetailSerializer(user).data)


class AdminUserRoleView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, id):
        target_user = get_admin_user_by_id(id)
        if target_user is None:
            raise NotFound("用户不存在。")

        serializer = AdminUserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = update_user_role(request.user, target_user, serializer.validated_data["role"])
        return success_response(AdminUserStatusSerializer(target_user).data)


class AdminUserBanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        target_user = get_admin_user_by_id(id)
        if target_user is None:
            raise NotFound("用户不存在。")

        serializer = AdminUserBanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = ban_user(
            request.user,
            target_user,
            reason=serializer.validated_data.get("reason", ""),
        )
        return success_response(AdminUserStatusSerializer(target_user).data, message="用户已封禁。")


class AdminUserUnbanView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        target_user = get_admin_user_by_id(id)
        if target_user is None:
            raise NotFound("用户不存在。")

        target_user = unban_user(target_user)
        return success_response(AdminUserStatusSerializer(target_user).data, message="用户已解封。")
