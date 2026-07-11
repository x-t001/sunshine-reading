from django.urls import path

from common.views import AiChatView, health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("ai/chat/", AiChatView.as_view(), name="ai-chat"),
]
