from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from .models import Bookshelf, ReadingHistory
from .selectors import (
    get_public_chapter_for_novel,
    get_public_novel,
    get_user_bookshelf_entry,
)


def add_novel_to_bookshelf(user, novel_id):
    novel = get_public_novel(novel_id)
    if novel is None:
        raise ValidationError({"novel_id": ["Novel not found or unavailable."]})

    Bookshelf.objects.get_or_create(user=user, novel=novel)
    return get_user_bookshelf_entry(user, novel.id)


def remove_novel_from_bookshelf(user, novel_id):
    entry = Bookshelf.objects.filter(user=user, novel_id=novel_id).first()
    if entry is None:
        raise NotFound("Bookshelf record not found.")

    entry.delete()


@transaction.atomic
def report_reading_history(user, novel_id, chapter_id, reading_position):
    chapter = get_public_chapter_for_novel(novel_id=novel_id, chapter_id=chapter_id)
    if chapter is None:
        raise ValidationError(
            {
                "chapter_id": [
                    "Chapter not found, unavailable, or does not belong to this novel.",
                ],
            }
        )

    history = ReadingHistory.objects.create(
        user=user,
        novel=chapter.novel,
        chapter=chapter,
        reading_position=reading_position,
    )

    Bookshelf.objects.update_or_create(
        user=user,
        novel=chapter.novel,
        defaults={
            "last_read_chapter": chapter,
            "reading_progress": Decimal(str(reading_position)),
            "last_read_at": timezone.now(),
        },
    )

    return history
