from django.contrib.auth import get_user_model
from django.db.models import Count, Q


User = get_user_model()


def get_admin_users(params):
    queryset = User.objects.all()

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            Q(username__icontains=keyword)
            | Q(nickname__icontains=keyword)
            | Q(email__icontains=keyword)
            | Q(phone__icontains=keyword)
        )

    role = params.get("role")
    if role:
        queryset = queryset.filter(role=role)

    if "is_banned" in params:
        queryset = queryset.filter(is_banned=params["is_banned"])

    return queryset.order_by("-date_joined", "-id")


def get_admin_user_by_id(user_id):
    return (
        User.objects.annotate(
            novel_count=Count("novels", distinct=True),
            comment_count=Count("comments", distinct=True),
            bookshelf_count=Count("bookshelves", distinct=True),
            rating_count=Count("novel_ratings", distinct=True),
        )
        .filter(id=user_id)
        .first()
    )
