from rest_framework.views import APIView

from common.response import success_response

from .selectors import get_active_ranking_types_with_items
from .serializers import RankingTypeSerializer


class RankingListView(APIView):
    def get(self, request):
        serializer = RankingTypeSerializer(get_active_ranking_types_with_items(), many=True)
        return success_response(serializer.data)
