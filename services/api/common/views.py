from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.response import success_response
from common.serializers import AiChatRequestSerializer
from common.services import call_ai_chat_completion


@api_view(["GET"])
def health_check(request):
    return success_response(
        data={
            "status": "ok",
            "service": "sunshine-reading-api",
        }
    )


class AiChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AiChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = call_ai_chat_completion(**serializer.validated_data)
        return success_response(result)
