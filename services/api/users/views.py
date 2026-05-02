from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.response import success_response

from .permissions import IsAuthenticatedAndNotBanned
from .serializers import (
    LoginSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
    UserBasicSerializer,
    UserProfileSerializer,
)


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
