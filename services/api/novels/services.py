from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Avg, Count
from rest_framework.exceptions import NotFound, ValidationError

from .models import Novel, NovelRating
from .selectors import get_public_novel_by_id, get_rating_for_user


def build_rating_summary(novel, user=None):
    return {
        "novel_id": novel.id,
        "rating_score": novel.rating_score,
        "rating_count": novel.rating_count,
        "my_rating": get_rating_for_user(novel.id, user),
    }


@transaction.atomic
def submit_or_update_rating(user, novel_id, score, comment=""):
    novel = get_public_novel_by_id(novel_id)
    if novel is None:
        raise ValidationError({"novel_id": ["Novel not found or unavailable."]})

    NovelRating.objects.update_or_create(
        user=user,
        novel=novel,
        defaults={
            "score": score,
            "comment": comment or "",
        },
    )
    novel = recalculate_novel_rating(novel.id)
    return build_rating_summary(novel, user)


@transaction.atomic
def delete_rating(user, novel_id):
    novel = get_public_novel_by_id(novel_id)
    if novel is None:
        raise ValidationError({"novel_id": ["Novel not found or unavailable."]})

    deleted_count, _ = NovelRating.objects.filter(user=user, novel=novel).delete()
    if deleted_count == 0:
        raise NotFound("Rating not found.")

    novel = recalculate_novel_rating(novel.id)
    return build_rating_summary(novel, user)


def recalculate_novel_rating(novel_id):
    stats = NovelRating.objects.filter(novel_id=novel_id).aggregate(
        score_avg=Avg("score"),
        score_count=Count("id"),
    )
    count = stats["score_count"] or 0
    if count == 0:
        score = Decimal("0.00")
    else:
        score = Decimal(str(stats["score_avg"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    Novel.objects.filter(id=novel_id).update(
        rating_score=score,
        rating_count=count,
    )
    return Novel.objects.get(id=novel_id)
