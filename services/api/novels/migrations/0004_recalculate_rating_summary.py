from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations
from django.db.models import Avg, Count


def recalculate_rating_summary(apps, schema_editor):
    Novel = apps.get_model("novels", "Novel")
    NovelRating = apps.get_model("novels", "NovelRating")

    for novel_id in Novel.objects.values_list("id", flat=True):
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


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0003_novel_rating_count_novelrating"),
    ]

    operations = [
        migrations.RunPython(recalculate_rating_summary, migrations.RunPython.noop),
    ]
