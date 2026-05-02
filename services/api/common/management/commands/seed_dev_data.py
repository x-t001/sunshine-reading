from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from bookshelf.models import Bookshelf, ReadingHistory
from chapters.models import Chapter
from comments.models import Comment
from novels.models import Category, Novel
from rankings.models import RankingItem, RankingType


class Command(BaseCommand):
    help = "Seed deterministic development data for Sunshine Reading."

    @transaction.atomic
    def handle(self, *args, **options):
        base_time = timezone.make_aware(
            datetime(2026, 5, 1, 9, 0, 0),
            timezone.get_current_timezone(),
        )

        categories = self._seed_categories()
        authors, readers = self._seed_users()
        novels = self._seed_novels(categories, authors, base_time)
        chapters_by_novel = self._seed_chapters(novels, base_time)
        self._seed_bookshelves(readers, novels, chapters_by_novel, base_time)
        self._seed_reading_history(readers, novels, chapters_by_novel, base_time)
        self._seed_comments(readers, novels, chapters_by_novel)
        self._seed_rankings(novels, base_time)
        self._refresh_novel_stats(novels)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded development data: "
                f"{len(categories)} categories, {len(authors)} authors, "
                f"{len(readers)} readers, {len(novels)} novels."
            )
        )

    def _seed_categories(self):
        category_data = [
            ("玄幻", "fantasy", 10),
            ("都市", "urban", 20),
            ("仙侠", "xianxia", 30),
            ("科幻", "sci-fi", 40),
            ("悬疑", "mystery", 50),
            ("游戏", "gaming", 60),
        ]
        categories = {}

        for name, slug, sort_order in category_data:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            categories[slug] = category

        return categories

    def _seed_users(self):
        User = get_user_model()
        author_data = [
            {
                "username": "author_sunrise",
                "email": "author_sunrise@example.com",
                "nickname": "晨光作者",
                "bio": "擅长热血成长和东方幻想题材。",
            },
            {
                "username": "author_starlight",
                "email": "author_starlight@example.com",
                "nickname": "星河作者",
                "bio": "偏好科幻、悬疑和游戏世界构建。",
            },
        ]
        reader_data = [
            {
                "username": "reader_alpha",
                "email": "reader_alpha@example.com",
                "nickname": "追更读者A",
            },
            {
                "username": "reader_beta",
                "email": "reader_beta@example.com",
                "nickname": "夜读读者B",
            },
            {
                "username": "reader_gamma",
                "email": "reader_gamma@example.com",
                "nickname": "收藏读者C",
            },
        ]

        authors = [
            self._upsert_user(User, role=User.Role.AUTHOR, **data)
            for data in author_data
        ]
        readers = [
            self._upsert_user(User, role=User.Role.READER, **data)
            for data in reader_data
        ]

        return authors, readers

    def _upsert_user(self, User, username, email, nickname, role, bio=""):
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                "email": email,
                "nickname": nickname,
                "bio": bio,
                "role": role,
                "is_active": True,
                "is_banned": False,
            },
        )
        if not user.password:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        return user

    def _seed_novels(self, categories, authors, base_time):
        novel_data = [
            ("星火神途", "fantasy", authors[0], "少年从边城走出，踏上寻找古老星火的修行路。", True),
            ("雾都夜行者", "urban", authors[1], "都市异闻与夜色案件交织，平凡调查员追踪真相。", False),
            ("青云剑书", "xianxia", authors[0], "一卷残缺剑书牵出宗门秘辛与山海旧约。", True),
            ("群星回声", "sci-fi", authors[1], "远航舰队收到百年前的求救信号，航线由此改写。", True),
            ("第七封信", "mystery", authors[1], "匿名信件接连出现，每一封都指向被遗忘的旧案。", False),
            ("无限副本日志", "gaming", authors[0], "玩家被卷入真实副本，用日志记录每次生还线索。", False),
            ("长街烟火", "urban", authors[0], "小店、街巷与普通人的选择，构成温暖现实群像。", False),
            ("天穹机械师", "sci-fi", authors[1], "机械师修复古老空港，也逐步接近天空崩塌的原因。", False),
        ]
        novels = []

        for index, (title, category_slug, author, description, is_featured) in enumerate(novel_data, start=1):
            novel, _ = Novel.objects.update_or_create(
                title=title,
                author=author,
                defaults={
                    "category": categories[category_slug],
                    "cover": f"https://example.com/covers/sunshine-reading-{index}.jpg",
                    "description": description,
                    "status": Novel.Status.SERIALIZING if index % 3 else Novel.Status.COMPLETED,
                    "audit_status": Novel.AuditStatus.APPROVED,
                    "view_count": 1200 + index * 379,
                    "collect_count": 0,
                    "comment_count": 0,
                    "rating_score": Decimal(f"{8 + (index % 2)}.{index % 10}"),
                    "is_featured": is_featured,
                },
            )
            novels.append(novel)

        return novels

    def _seed_chapters(self, novels, base_time):
        chapters_by_novel = {}

        for novel_index, novel in enumerate(novels, start=1):
            chapter_count = 5 + (novel_index % 6)
            chapters = []

            for chapter_number in range(1, chapter_count + 1):
                title = f"第{chapter_number}章 起点与回响"
                content = self._chapter_content(novel.title, chapter_number)
                published_at = base_time + timedelta(days=novel_index, hours=chapter_number)
                chapter, _ = Chapter.objects.update_or_create(
                    novel=novel,
                    chapter_number=chapter_number,
                    defaults={
                        "title": title,
                        "content": content,
                        "word_count": len(content),
                        "is_free": chapter_number <= 3,
                        "price": Decimal("0.00") if chapter_number <= 3 else Decimal("0.10"),
                        "status": Chapter.Status.PUBLISHED,
                        "audit_status": Chapter.AuditStatus.APPROVED,
                        "published_at": published_at,
                    },
                )
                chapters.append(chapter)

            latest_chapter = chapters[-1]
            Novel.objects.filter(pk=novel.pk).update(
                word_count=sum(chapter.word_count for chapter in chapters),
                latest_chapter_title=latest_chapter.title,
                latest_chapter_updated_at=latest_chapter.published_at,
            )
            novel.refresh_from_db()
            chapters_by_novel[novel.pk] = chapters

        return chapters_by_novel

    def _chapter_content(self, novel_title, chapter_number):
        return (
            f"{novel_title} 的第 {chapter_number} 章用于本地开发测试。"
            "这一章包含角色行动、场景推进和章节结尾悬念，"
            "方便在后台、书架、阅读历史和评论数据中查看关联效果。"
        )

    def _seed_bookshelves(self, readers, novels, chapters_by_novel, base_time):
        for reader_index, reader in enumerate(readers):
            for offset, novel in enumerate(novels[reader_index : reader_index + 4]):
                chapters = chapters_by_novel[novel.pk]
                chapter = chapters[min(offset + 1, len(chapters) - 1)]
                progress = Decimal(str(min(95, 20 + reader_index * 15 + offset * 12)))

                Bookshelf.objects.update_or_create(
                    user=reader,
                    novel=novel,
                    defaults={
                        "last_read_chapter": chapter,
                        "reading_progress": progress,
                        "last_read_at": base_time + timedelta(days=reader_index, hours=offset),
                    },
                )

    def _seed_reading_history(self, readers, novels, chapters_by_novel, base_time):
        for reader_index, reader in enumerate(readers):
            for novel_index, novel in enumerate(novels[:5]):
                chapters = chapters_by_novel[novel.pk]
                chapter = chapters[(reader_index + novel_index) % len(chapters)]
                history, _ = ReadingHistory.objects.update_or_create(
                    user=reader,
                    novel=novel,
                    chapter=chapter,
                    defaults={
                        "reading_position": 300 + reader_index * 120 + novel_index * 80,
                    },
                )
                ReadingHistory.objects.filter(pk=history.pk).update(
                    read_at=base_time + timedelta(days=novel_index, minutes=reader_index * 15)
                )

    def _seed_comments(self, readers, novels, chapters_by_novel):
        comment_data = [
            (readers[0], novels[0], 0, None, "开篇节奏很稳，世界观有继续追的空间。", 12),
            (readers[1], novels[0], 1, None, "第二章的信息量不错，期待主角下一步选择。", 7),
            (readers[2], novels[2], 0, None, "剑书设定清楚，分类页展示时很适合作为样例。", 9),
            (readers[0], novels[3], 2, None, "科幻线索比较明确，适合测试排行榜数据。", 15),
            (readers[1], novels[4], 1, None, "悬疑氛围足，评论列表可以看到不同小说关联。", 5),
            (readers[2], novels[5], 0, None, "副本设定适合后续做章节付费测试。", 4),
        ]
        roots = []

        for user, novel, chapter_index, parent, content, like_count in comment_data:
            chapter = chapters_by_novel[novel.pk][chapter_index]
            comment, _ = Comment.objects.update_or_create(
                user=user,
                novel=novel,
                chapter=chapter,
                parent=parent,
                content=content,
                defaults={
                    "like_count": like_count,
                    "status": Comment.Status.NORMAL,
                },
            )
            roots.append(comment)

        Comment.objects.update_or_create(
            user=readers[1],
            novel=novels[0],
            chapter=chapters_by_novel[novels[0].pk][0],
            parent=roots[0],
            content="同感，前几章用来做阅读历史测试也很合适。",
            defaults={
                "like_count": 3,
                "status": Comment.Status.NORMAL,
            },
        )

    def _seed_rankings(self, novels, base_time):
        ranking_types = [
            ("热门榜", "hot", "按近期阅读和互动热度生成的开发榜单。"),
            ("收藏榜", "collection", "按书架收藏数量生成的开发榜单。"),
            ("新书榜", "new", "按新书更新时间生成的开发榜单。"),
        ]
        snapshot_time = base_time.replace(hour=8, minute=0, second=0, microsecond=0)

        for name, code, description in ranking_types:
            ranking_type, _ = RankingType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "is_active": True,
                },
            )

            for rank, novel in enumerate(novels[:6], start=1):
                RankingItem.objects.update_or_create(
                    ranking_type=ranking_type,
                    rank=rank,
                    calculated_at=snapshot_time,
                    defaults={
                        "novel": novel,
                        "score": Decimal(str(1000 - rank * 37 + len(code))),
                    },
                )

    def _refresh_novel_stats(self, novels):
        for novel in novels:
            Novel.objects.filter(pk=novel.pk).update(
                collect_count=Bookshelf.objects.filter(novel=novel).count(),
                comment_count=Comment.objects.filter(novel=novel).count(),
            )
