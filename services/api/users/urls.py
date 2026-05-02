from django.urls import path

from .views import CurrentUserView, LoginView, RefreshTokenView, RegisterView

app_name = "users"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("users/me/", CurrentUserView.as_view(), name="users-me"),
]
