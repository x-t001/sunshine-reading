from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from users.permissions import IsAdminUser

from common.pagination import PublicPageNumberPagination
from common.response import success_response

from .selectors import (
    get_active_ranking_types_with_items,
    get_admin_ranking_item_by_id,
    get_admin_ranking_items,
    get_admin_ranking_type_by_id,
    get_admin_ranking_types,
)
from .serializers import (
    AdminRankingItemCreateSerializer,
    AdminRankingItemQuerySerializer,
    AdminRankingItemSerializer,
    AdminRankingItemUpdateSerializer,
    AdminRankingTypeCreateSerializer,
    AdminRankingTypeQuerySerializer,
    AdminRankingTypeSerializer,
    AdminRankingTypeStatusUpdateSerializer,
    AdminRankingTypeUpdateSerializer,
    RankingTypeSerializer,
)
from .services import (
    create_admin_ranking_item,
    create_admin_ranking_type,
    update_admin_ranking_item,
    update_admin_ranking_type,
    update_admin_ranking_type_status,
)


class RankingListView(APIView):
    def get(self, request):
        serializer = RankingTypeSerializer(get_active_ranking_types_with_items(), many=True)
        return success_response(serializer.data)


class AdminRankingTypeListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query_serializer = AdminRankingTypeQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        paginator = PublicPageNumberPagination()
        queryset = get_admin_ranking_types(query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminRankingTypeSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request):
        serializer = AdminRankingTypeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ranking_type = create_admin_ranking_type(serializer.validated_data, actor=request.user)
        ranking_type = get_admin_ranking_type_by_id(ranking_type.id)
        return success_response(AdminRankingTypeSerializer(ranking_type).data)


class AdminRankingTypeDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, id):
        ranking_type = get_admin_ranking_type_by_id(id)
        if ranking_type is None:
            raise NotFound("Ranking type not found.")
        return ranking_type

    def get(self, request, id):
        ranking_type = self.get_object(id)
        return success_response(AdminRankingTypeSerializer(ranking_type).data)

    def patch(self, request, id):
        ranking_type = self.get_object(id)
        serializer = AdminRankingTypeUpdateSerializer(
            data=request.data,
            context={"ranking_type": ranking_type},
        )
        serializer.is_valid(raise_exception=True)
        ranking_type = update_admin_ranking_type(ranking_type, serializer.validated_data, actor=request.user)
        ranking_type = get_admin_ranking_type_by_id(ranking_type.id)
        return success_response(AdminRankingTypeSerializer(ranking_type).data)


class AdminRankingTypeStatusView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, id):
        ranking_type = get_admin_ranking_type_by_id(id)
        if ranking_type is None:
            raise NotFound("Ranking type not found.")

        serializer = AdminRankingTypeStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ranking_type = update_admin_ranking_type_status(ranking_type, serializer.validated_data["is_active"], actor=request.user)
        ranking_type = get_admin_ranking_type_by_id(ranking_type.id)
        return success_response(AdminRankingTypeSerializer(ranking_type).data)


class AdminRankingItemListCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query_serializer = AdminRankingItemQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        paginator = PublicPageNumberPagination()
        queryset = get_admin_ranking_items(query_serializer.validated_data)
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminRankingItemSerializer(page, many=True)
        return success_response(paginator.get_paginated_data(serializer.data))

    def post(self, request):
        serializer = AdminRankingItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = create_admin_ranking_item(serializer.validated_data, actor=request.user)
        item = get_admin_ranking_item_by_id(item.id)
        return success_response(AdminRankingItemSerializer(item).data)


class AdminRankingItemDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get_object(self, id):
        item = get_admin_ranking_item_by_id(id)
        if item is None:
            raise NotFound("Ranking item not found.")
        return item

    def get(self, request, id):
        item = self.get_object(id)
        return success_response(AdminRankingItemSerializer(item).data)

    def patch(self, request, id):
        item = self.get_object(id)
        serializer = AdminRankingItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = update_admin_ranking_item(item, serializer.validated_data, actor=request.user)
        item = get_admin_ranking_item_by_id(item.id)
        return success_response(AdminRankingItemSerializer(item).data)
