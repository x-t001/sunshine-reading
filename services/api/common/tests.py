import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from chapters.models import Chapter
from comments.models import Comment
from common.models import AuditLog
from novels.models import Category, Novel
from rankings.models import RankingItem, RankingType
from video_generation.models import VideoGenerationJob, VideoProject, VideoScene
from video_generation.services import claim_next_video_generation_job, process_video_generation_job, recover_stale_video_generation_jobs


class ApiSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.reader = User.objects.create_user(
            username="reader_smoke",
            password="password12345Strong!",
            role="reader",
            nickname="读者",
        )
        cls.author = User.objects.create_user(
            username="author_smoke",
            password="password12345Strong!",
            role="author",
            nickname="作者",
        )
        cls.reviewer = User.objects.create_user(
            username="reviewer_smoke",
            password="password12345Strong!",
            role="reviewer",
            nickname="审核员",
        )
        cls.admin = User.objects.create_user(
            username="admin_smoke",
            password="password12345Strong!",
            role="admin",
            is_staff=True,
            nickname="管理员",
        )

        cls.category = Category.objects.create(name="玄幻", slug="fantasy", sort_order=1, is_active=True)
        cls.novel = Novel.objects.create(
            title="烟火测试小说",
            author=cls.author,
            category=cls.category,
            description="用于 API 烟测的公开小说。",
            status="serializing",
            audit_status="approved",
            word_count=100,
            rating_score=Decimal("4.50"),
            rating_count=1,
        )
        cls.chapter = Chapter.objects.create(
            novel=cls.novel,
            title="第一章",
            chapter_number=1,
            content="这是第一章内容。",
            word_count=8,
            status="published",
            audit_status="approved",
            published_at=timezone.now(),
        )
        cls.pending_novel = Novel.objects.create(
            title="待审核小说",
            author=cls.author,
            category=cls.category,
            description="待审核内容。",
            status="serializing",
            audit_status="pending",
        )
        cls.pending_chapter = Chapter.objects.create(
            novel=cls.pending_novel,
            title="待审核章节",
            chapter_number=1,
            content="待审核章节内容。",
            word_count=8,
            status="draft",
            audit_status="pending",
        )
        cls.comment = Comment.objects.create(
            user=cls.reader,
            novel=cls.novel,
            chapter=cls.chapter,
            content="公开评论",
            status="normal",
        )
        cls.ranking_type = RankingType.objects.create(name="热度榜", code="hot", is_active=True)
        RankingItem.objects.create(
            ranking_type=cls.ranking_type,
            novel=cls.novel,
            score=Decimal("100.00"),
            rank=1,
            calculated_at=timezone.now(),
        )

    def setUp(self):
        self.client = APIClient()

    def assert_success_envelope(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 0)
        self.assertEqual(response.data["message"], "success")
        self.assertIn("data", response.data)

    def test_public_reading_endpoints(self):
        paths = [
            "/api/health/",
            "/api/categories/",
            "/api/novels/",
            f"/api/novels/{self.novel.id}/",
            f"/api/novels/{self.novel.id}/chapters/",
            f"/api/chapters/{self.chapter.id}/",
            "/api/rankings/",
            f"/api/novels/{self.novel.id}/comments/",
            f"/api/novels/{self.novel.id}/ratings/summary/",
        ]

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assert_success_envelope(response)

    def test_auth_register_login_and_me(self):
        register_response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new_reader_smoke",
                "password": "password12345Strong!",
                "password_confirm": "password12345Strong!",
                "nickname": "新读者",
                "email": "new_reader_smoke@example.com",
            },
            format="json",
        )
        self.assert_success_envelope(register_response)
        self.assertNotIn("password", register_response.data["data"])

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "new_reader_smoke", "password": "password12345Strong!"},
            format="json",
        )
        self.assert_success_envelope(login_response)
        self.assertIn("access", login_response.data["data"])
        self.assertIn("refresh", login_response.data["data"])

        self.client.force_authenticate(user=self.reader)
        me_response = self.client.get("/api/users/me/")
        self.assert_success_envelope(me_response)
        self.assertEqual(me_response.data["data"]["username"], self.reader.username)

    def test_reader_protected_write_endpoints(self):
        self.client.force_authenticate(user=self.reader)

        bookshelf_response = self.client.post("/api/bookshelf/", {"novel_id": self.novel.id}, format="json")
        self.assert_success_envelope(bookshelf_response)

        history_response = self.client.post(
            "/api/reading-history/",
            {
                "novel_id": self.novel.id,
                "chapter_id": self.chapter.id,
                "reading_position": 25,
            },
            format="json",
        )
        self.assert_success_envelope(history_response)

        comment_response = self.client.post(
            f"/api/novels/{self.novel.id}/comments/",
            {"content": "这是一条烟测评论。"},
            format="json",
        )
        self.assert_success_envelope(comment_response)

        rating_response = self.client.post(
            f"/api/novels/{self.novel.id}/ratings/",
            {"score": 5, "comment": "很好看"},
            format="json",
        )
        self.assert_success_envelope(rating_response)

    def test_author_reviewer_and_admin_permission_boundaries(self):
        self.client.force_authenticate(user=self.reader)
        reader_author_response = self.client.get("/api/author/novels/")
        self.assertIn(reader_author_response.status_code, [401, 403])

        self.client.force_authenticate(user=self.author)
        author_response = self.client.post(
            "/api/author/novels/",
            {
                "title": "作者烟测作品",
                "category_id": self.category.id,
                "description": "作者创建作品烟测。",
                "status": "serializing",
            },
            format="json",
        )
        self.assert_success_envelope(author_response)

        self.client.force_authenticate(user=self.reviewer)
        pending_response = self.client.get("/api/reviewer/novels/pending/")
        self.assert_success_envelope(pending_response)
        claim_response = self.client.post(f"/api/reviewer/novels/{self.pending_novel.id}/claim/")
        self.assert_success_envelope(claim_response)
        self.pending_novel.refresh_from_db()
        self.assertEqual(self.pending_novel.audit_status, "reviewing")
        self.assertEqual(self.pending_novel.reviewer_id, self.reviewer.id)

        self.client.force_authenticate(user=self.reader)
        reader_admin_response = self.client.get("/api/admin/users/")
        self.assertIn(reader_admin_response.status_code, [401, 403])

        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get("/api/admin/users/")
        self.assert_success_envelope(admin_response)

    def test_admin_category_management(self):
        self.client.force_authenticate(user=self.reader)
        denied_response = self.client.get("/api/admin/categories/")
        self.assertIn(denied_response.status_code, [401, 403])

        self.client.force_authenticate(user=self.admin)
        list_response = self.client.get("/api/admin/categories/")
        self.assert_success_envelope(list_response)

        create_response = self.client.post(
            "/api/admin/categories/",
            {
                "name": "都市",
                "slug": "city",
                "sort_order": 2,
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(create_response)
        category_id = create_response.data["data"]["id"]

        detail_response = self.client.get(f"/api/admin/categories/{category_id}/")
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["slug"], "city")

        update_response = self.client.patch(
            f"/api/admin/categories/{category_id}/",
            {"name": "现代都市", "sort_order": 3},
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.assertEqual(update_response.data["data"]["name"], "现代都市")
        self.assertEqual(update_response.data["data"]["sort_order"], 3)

        status_response = self.client.patch(
            f"/api/admin/categories/{category_id}/status/",
            {"is_active": False},
            format="json",
        )
        self.assert_success_envelope(status_response)
        self.assertFalse(status_response.data["data"]["is_active"])

    def test_admin_ranking_management(self):
        self.client.force_authenticate(user=self.reader)
        denied_response = self.client.get("/api/admin/ranking-types/")
        self.assertIn(denied_response.status_code, [401, 403])

        self.client.force_authenticate(user=self.admin)
        list_response = self.client.get("/api/admin/ranking-types/")
        self.assert_success_envelope(list_response)

        create_type_response = self.client.post(
            "/api/admin/ranking-types/",
            {
                "name": "新书榜",
                "code": "new-books",
                "description": "新书测试榜单",
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(create_type_response)
        ranking_type_id = create_type_response.data["data"]["id"]

        update_type_response = self.client.patch(
            f"/api/admin/ranking-types/{ranking_type_id}/",
            {"name": "新书推荐榜"},
            format="json",
        )
        self.assert_success_envelope(update_type_response)
        self.assertEqual(update_type_response.data["data"]["name"], "新书推荐榜")

        status_response = self.client.patch(
            f"/api/admin/ranking-types/{ranking_type_id}/status/",
            {"is_active": False},
            format="json",
        )
        self.assert_success_envelope(status_response)
        self.assertFalse(status_response.data["data"]["is_active"])

        calculated_at = timezone.now().isoformat()
        create_item_response = self.client.post(
            "/api/admin/ranking-items/",
            {
                "ranking_type_id": ranking_type_id,
                "novel_id": self.novel.id,
                "score": "88.50",
                "rank": 1,
                "calculated_at": calculated_at,
            },
            format="json",
        )
        self.assert_success_envelope(create_item_response)
        item_id = create_item_response.data["data"]["id"]

        update_item_response = self.client.patch(
            f"/api/admin/ranking-items/{item_id}/",
            {"score": "99.00", "rank": 2},
            format="json",
        )
        self.assert_success_envelope(update_item_response)
        self.assertEqual(update_item_response.data["data"]["score"], "99.00")
        self.assertEqual(update_item_response.data["data"]["rank"], 2)

    def test_admin_management_actions_create_audit_logs(self):
        self.client.force_authenticate(user=self.admin)

        role_response = self.client.patch(
            f"/api/admin/users/{self.reader.id}/role/",
            {"role": "author"},
            format="json",
        )
        self.assert_success_envelope(role_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.USER,
                object_id=self.reader.id,
                reviewer=self.admin,
                action=AuditLog.Action.ROLE_UPDATE,
                from_status="reader",
                to_status="author",
            ).exists()
        )

        ban_response = self.client.post(
            f"/api/admin/users/{self.reader.id}/ban/",
            {"reason": "smoke test"},
            format="json",
        )
        self.assertEqual(ban_response.status_code, 200)
        self.assertEqual(ban_response.data["code"], 0)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.USER,
                object_id=self.reader.id,
                reviewer=self.admin,
                action=AuditLog.Action.BAN,
                from_status="active",
                to_status="banned",
            ).exists()
        )

        unban_response = self.client.post(f"/api/admin/users/{self.reader.id}/unban/")
        self.assertEqual(unban_response.status_code, 200)
        self.assertEqual(unban_response.data["code"], 0)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.USER,
                object_id=self.reader.id,
                reviewer=self.admin,
                action=AuditLog.Action.UNBAN,
                from_status="banned",
                to_status="active",
            ).exists()
        )

        category_response = self.client.patch(
            f"/api/admin/categories/{self.category.id}/status/",
            {"is_active": False},
            format="json",
        )
        self.assert_success_envelope(category_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.CATEGORY,
                object_id=self.category.id,
                reviewer=self.admin,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status="active",
                to_status="inactive",
            ).exists()
        )

        novel_status_response = self.client.patch(
            f"/api/admin/novels/{self.novel.id}/status/",
            {"status": "paused"},
            format="json",
        )
        self.assert_success_envelope(novel_status_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.NOVEL,
                object_id=self.novel.id,
                reviewer=self.admin,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status="serializing",
                to_status="paused",
            ).exists()
        )

        featured_response = self.client.patch(
            f"/api/admin/novels/{self.novel.id}/featured/",
            {"is_featured": True},
            format="json",
        )
        self.assert_success_envelope(featured_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.NOVEL,
                object_id=self.novel.id,
                reviewer=self.admin,
                action=AuditLog.Action.FEATURE_UPDATE,
                from_status="normal",
                to_status="featured",
            ).exists()
        )

        chapter_status_response = self.client.patch(
            f"/api/admin/chapters/{self.chapter.id}/status/",
            {"status": "hidden"},
            format="json",
        )
        self.assert_success_envelope(chapter_status_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.CHAPTER,
                object_id=self.chapter.id,
                reviewer=self.admin,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status="published",
                to_status="hidden",
            ).exists()
        )

        comment_status_response = self.client.patch(
            f"/api/admin/comments/{self.comment.id}/status/",
            {"status": "hidden"},
            format="json",
        )
        self.assert_success_envelope(comment_status_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.COMMENT,
                object_id=self.comment.id,
                reviewer=self.admin,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status="normal",
                to_status="hidden",
            ).exists()
        )

        ranking_status_response = self.client.patch(
            f"/api/admin/ranking-types/{self.ranking_type.id}/status/",
            {"is_active": False},
            format="json",
        )
        self.assert_success_envelope(ranking_status_response)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.RANKING_TYPE,
                object_id=self.ranking_type.id,
                reviewer=self.admin,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status="active",
                to_status="inactive",
            ).exists()
        )

    def test_author_details_include_owned_audit_history(self):
        AuditLog.objects.create(
            content_type=AuditLog.ContentType.NOVEL,
            object_id=self.novel.id,
            reviewer=self.reviewer,
            action=AuditLog.Action.REJECT,
            from_status="reviewing",
            to_status="rejected",
            reason="作品简介需要补充。",
        )
        AuditLog.objects.create(
            content_type=AuditLog.ContentType.CHAPTER,
            object_id=self.chapter.id,
            reviewer=self.reviewer,
            action=AuditLog.Action.REJECT,
            from_status="reviewing",
            to_status="rejected",
            reason="章节内容需要完善。",
        )

        self.client.force_authenticate(user=self.author)

        novel_response = self.client.get(f"/api/author/novels/{self.novel.id}/")
        self.assert_success_envelope(novel_response)
        self.assertEqual(novel_response.data["data"]["audit_logs"][0]["reason"], "作品简介需要补充。")
        self.assertNotIn("email", novel_response.data["data"]["audit_logs"][0]["reviewer"])

        chapter_response = self.client.get(f"/api/author/chapters/{self.chapter.id}/")
        self.assert_success_envelope(chapter_response)
        self.assertEqual(chapter_response.data["data"]["audit_logs"][0]["reason"], "章节内容需要完善。")

        self.client.force_authenticate(user=self.reader)
        denied_response = self.client.get(f"/api/author/novels/{self.novel.id}/")
        self.assertIn(denied_response.status_code, [401, 403])

    def test_video_project_text_mvp_permissions_and_admin_visibility(self):
        input_text = "A hidden city wakes under the morning light. " * 20

        unauthenticated_response = self.client.post(
            "/api/video-projects/",
            {
                "source_type": "text",
                "title": "Story trailer",
                "input_text": input_text,
                "duration_target": 60,
                "aspect_ratio": "9:16",
            },
            format="json",
        )
        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_authenticate(user=self.reader)
        create_response = self.client.post(
            "/api/video-projects/",
            {
                "source_type": "text",
                "title": "Story trailer",
                "input_text": input_text,
                "duration_target": 60,
                "aspect_ratio": "9:16",
            },
            format="json",
        )
        self.assert_success_envelope(create_response)
        project_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.data["data"]["status"], VideoProject.Status.DRAFT)
        self.assertEqual(create_response.data["data"]["source_type"], VideoProject.SourceType.TEXT)
        self.assertEqual(create_response.data["data"]["scenes"], [])

        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project_id,
                reviewer=self.reader,
                action=AuditLog.Action.CREATE,
                to_status=VideoProject.Status.DRAFT,
            ).exists()
        )

        list_response = self.client.get("/api/video-projects/")
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["data"]["count"], 1)

        detail_response = self.client.get(f"/api/video-projects/{project_id}/")
        self.assert_success_envelope(detail_response)
        self.assertEqual(detail_response.data["data"]["title"], "Story trailer")

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_video",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        other_detail_response = self.client.get(f"/api/video-projects/{project_id}/")
        self.assertEqual(other_detail_response.status_code, 404)

        self.client.force_authenticate(user=self.admin)
        admin_list_response = self.client.get("/api/admin/video-projects/")
        self.assert_success_envelope(admin_list_response)
        self.assertEqual(admin_list_response.data["data"]["count"], 1)

        admin_detail_response = self.client.get(f"/api/admin/video-projects/{project_id}/")
        self.assert_success_envelope(admin_detail_response)
        self.assertEqual(admin_detail_response.data["data"]["owner"]["id"], self.reader.id)

        self.client.force_authenticate(user=self.reader)
        unsafe_response = self.client.post(
            "/api/video-projects/",
            {
                "source_type": "text",
                "input_text": "<script>alert(1)</script>" + (" safe story text" * 80),
            },
            format="json",
        )
        self.assertEqual(unsafe_response.status_code, 400)

        delete_response = self.client.delete(f"/api/video-projects/{project_id}/")
        self.assert_success_envelope(delete_response)
        self.assertFalse(VideoProject.objects.filter(id=project_id, deleted_at__isnull=True).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project_id,
                reviewer=self.reader,
                action=AuditLog.Action.DELETE,
                from_status=VideoProject.Status.DRAFT,
                to_status=VideoProject.Status.CANCELED,
            ).exists()
        )

    def test_video_project_chapter_source_permissions_snapshot_and_validation(self):
        public_content = "公开章节中的信使必须在天亮前穿过被洪水淹没的城市，把最后一份药送到医院。" * 45
        self.chapter.content = public_content
        self.chapter.word_count = len(public_content)
        self.chapter.save(update_fields=["content", "word_count", "updated_at"])

        author_content = "作者草稿记录了守塔人发现海面异常光芒，并在隐瞒真相和保护村庄之间做出选择。" * 40
        self.pending_chapter.content = author_content
        self.pending_chapter.word_count = len(author_content)
        self.pending_chapter.save(update_fields=["content", "word_count", "updated_at"])

        unauthenticated_response = self.client.get("/api/video-source-chapters/")
        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_authenticate(user=self.reader)
        source_list_response = self.client.get("/api/video-source-chapters/?keyword=烟火")
        self.assert_success_envelope(source_list_response)
        self.assertEqual(source_list_response.data["data"]["count"], 1)
        self.assertEqual(source_list_response.data["data"]["results"][0]["id"], self.chapter.id)
        self.assertEqual(source_list_response.data["data"]["results"][0]["source_access"], "public")

        create_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": self.chapter.id, "duration_target": 60, "aspect_ratio": "9:16"},
            format="json",
        )
        self.assert_success_envelope(create_response)
        project_data = create_response.data["data"]
        self.assertEqual(project_data["source_type"], VideoProject.SourceType.CHAPTER)
        self.assertEqual(project_data["source_novel_id"], self.novel.id)
        self.assertEqual(project_data["source_chapter_id"], self.chapter.id)
        self.assertEqual(project_data["input_text"], public_content[:3000])
        self.assertTrue(project_data["source_excerpt_hash"])
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project_data["id"],
                reviewer=self.reader,
                action=AuditLog.Action.CREATE,
            ).exists()
        )

        hidden_source_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": self.pending_chapter.id},
            format="json",
        )
        self.assertEqual(hidden_source_response.status_code, 404)

        self.client.force_authenticate(user=self.author)
        author_list_response = self.client.get("/api/video-source-chapters/?keyword=待审核")
        self.assert_success_envelope(author_list_response)
        self.assertEqual(author_list_response.data["data"]["results"][0]["source_access"], "owned")
        author_create_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": self.pending_chapter.id, "title": "作者草稿短片", "duration_target": 45},
            format="json",
        )
        self.assert_success_envelope(author_create_response)
        self.assertEqual(author_create_response.data["data"]["source_chapter_id"], self.pending_chapter.id)

        self.client.force_authenticate(user=self.admin)
        admin_create_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": self.pending_chapter.id, "title": "管理员章节项目"},
            format="json",
        )
        self.assert_success_envelope(admin_create_response)

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_chapter_source",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        private_source_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": self.pending_chapter.id},
            format="json",
        )
        self.assertEqual(private_source_response.status_code, 404)

        short_chapter = Chapter.objects.create(
            novel=self.novel,
            title="过短章节",
            chapter_number=99,
            content="内容太短。",
            word_count=5,
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
            published_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.reader)
        short_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": short_chapter.id},
            format="json",
        )
        self.assertEqual(short_response.status_code, 400)

        unsafe_chapter = Chapter.objects.create(
            novel=self.novel,
            title="危险章节",
            chapter_number=100,
            content="<script>alert(1)</script>" + ("安全正文" * 40),
            word_count=180,
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
            published_at=timezone.now(),
        )
        unsafe_response = self.client.post(
            "/api/video-projects/from-chapter/",
            {"chapter_id": unsafe_chapter.id},
            format="json",
        )
        self.assertEqual(unsafe_response.status_code, 400)

    def test_video_project_storyboard_generation(self):
        input_text = "A hidden city wakes under the morning light. The young courier finds a glowing map and follows it into danger. " * 8
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Story trailer",
            title="Story trailer",
            input_text=input_text,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )

        unauthenticated_response = self.client.post(f"/api/video-projects/{project.id}/storyboard/", {}, format="json")
        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_authenticate(user=self.reader)
        invalid_response = self.client.post(f"/api/video-projects/{project.id}/storyboard/", {"scene_count": 3}, format="json")
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(VideoScene.objects.filter(project=project).count(), 0)

        storyboard_response = self.client.post(f"/api/video-projects/{project.id}/storyboard/", {"scene_count": 5}, format="json")
        self.assert_success_envelope(storyboard_response)
        data = storyboard_response.data["data"]
        self.assertEqual(data["status"], VideoProject.Status.STORYBOARD_READY)
        self.assertEqual(data["scene_count"], 5)
        self.assertEqual(len(data["scenes"]), 5)
        self.assertEqual(sum(scene["duration_seconds"] for scene in data["scenes"]), 60)
        self.assertTrue(all(scene["status"] == VideoScene.Status.READY for scene in data["scenes"]))
        self.assertTrue(data["summary"])
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project.id,
                reviewer=self.reader,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status=VideoProject.Status.DRAFT,
                to_status=VideoProject.Status.STORYBOARD_READY,
            ).exists()
        )

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_storyboard",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        other_response = self.client.post(f"/api/video-projects/{project.id}/storyboard/", {}, format="json")
        self.assertEqual(other_response.status_code, 404)

        self.client.force_authenticate(user=self.reader)
        delete_response = self.client.delete(f"/api/video-projects/{project.id}/")
        self.assert_success_envelope(delete_response)
        deleted_response = self.client.post(f"/api/video-projects/{project.id}/storyboard/", {}, format="json")
        self.assertEqual(deleted_response.status_code, 404)

    def test_ai_storyboard_requires_server_configuration(self):
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="AI storyboard config",
            title="AI storyboard config",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)

        capabilities_response = self.client.get("/api/video-projects/capabilities/")
        self.assert_success_envelope(capabilities_response)
        self.assertFalse(capabilities_response.data["data"]["ai_storyboard_configured"])

        response = self.client.post(f"/api/video-projects/{project.id}/storyboard/ai/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        project.refresh_from_db()
        self.assertEqual(project.status, VideoProject.Status.DRAFT)

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-test-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
    )
    @patch("video_generation.providers.urlopen")
    def test_ai_storyboard_generation_failure_retry_and_permissions(self, mocked_urlopen):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

        scenes = [
            {
                "title": f"AI scene {index}",
                "visual_prompt": f"Vertical cinematic shot {index}, courier moving through rain and neon light.",
                "narration_text": f"Narration {index}",
                "subtitle_text": f"Subtitle {index}",
                "duration_seconds": 10,
                "camera_direction": "Tracking shot",
                "mood": "urgent",
            }
            for index in range(1, 7)
        ]
        storyboard_content = json.dumps({"summary": "AI generated summary", "scenes": scenes}, ensure_ascii=False)
        mocked_urlopen.side_effect = [
            FakeResponse(
                {
                    "model": "storyboard-test-model",
                    "choices": [{"message": {"content": storyboard_content}}],
                    "usage": {"total_tokens": 321},
                }
            ),
            FakeResponse(
                {
                    "model": "storyboard-test-model",
                    "choices": [{"message": {"content": "not-json"}}],
                }
            ),
        ]

        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Provider storyboard",
            title="Provider storyboard",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )

        self.client.force_authenticate(user=None)
        unauthenticated_response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {},
            format="json",
        )
        self.assertEqual(unauthenticated_response.status_code, 401)

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_ai_storyboard",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        denied_response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {},
            format="json",
        )
        self.assertEqual(denied_response.status_code, 404)

        self.client.force_authenticate(user=self.reader)
        capabilities_response = self.client.get("/api/video-projects/capabilities/")
        self.assert_success_envelope(capabilities_response)
        capabilities_data = capabilities_response.data["data"]
        self.assertTrue(capabilities_data["ai_storyboard_configured"])
        self.assertEqual(capabilities_data["ai_storyboard_model"], "storyboard-test-model")
        self.assertNotIn("api_key", capabilities_data)
        self.assertNotIn("api_url", capabilities_data)
        self.assertNotIn("server-test-key", json.dumps(capabilities_data))

        response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 6},
            format="json",
        )
        self.assert_success_envelope(response)
        self.assertEqual(response.data["data"]["status"], VideoProject.Status.STORYBOARD_READY)
        self.assertEqual(len(response.data["data"]["scenes"]), 6)
        self.assertEqual(sum(scene["duration_seconds"] for scene in response.data["data"]["scenes"]), 60)
        self.assertEqual(response.data["data"]["summary"], "AI generated summary")
        provider_request = mocked_urlopen.call_args_list[0].args[0]
        self.assertEqual(provider_request.get_header("Authorization"), "Bearer server-test-key")
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project.id,
                reviewer=self.reader,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status=VideoProject.Status.ANALYZING,
                to_status=VideoProject.Status.STORYBOARD_READY,
            ).exists()
        )

        existing_scene_ids = list(VideoScene.objects.filter(project=project).values_list("id", flat=True))
        failed_response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 6},
            format="json",
        )
        self.assertEqual(failed_response.status_code, 400)
        project.refresh_from_db()
        self.assertEqual(project.status, VideoProject.Status.FAILED)
        self.assertTrue(project.failure_reason)
        self.assertEqual(
            list(VideoScene.objects.filter(project=project).values_list("id", flat=True)),
            existing_scene_ids,
        )

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-job-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_JOB_MAX_ATTEMPTS=3,
        VIDEO_JOB_STALE_SECONDS=60,
    )
    @patch("video_generation.providers.urlopen")
    def test_durable_ai_storyboard_job_queue_poll_retry_and_recovery(self, mocked_urlopen):
        class FakeResponse:
            def __init__(self, content):
                self.content = content

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                payload = {
                    "model": "storyboard-job-model",
                    "choices": [{"message": {"content": self.content}}],
                    "usage": {"total_tokens": 222},
                }
                return json.dumps(payload, ensure_ascii=False).encode("utf-8")

        scenes = [
            {
                "title": f"Queued scene {index}",
                "visual_prompt": f"Vertical cinematic scene {index} with clear subject, action, light, and composition.",
                "narration_text": f"Narration {index}",
                "subtitle_text": f"Subtitle {index}",
                "duration_seconds": 10,
                "camera_direction": "Tracking shot",
                "mood": "urgent",
            }
            for index in range(1, 7)
        ]
        valid_content = json.dumps({"summary": "Durable job summary", "scenes": scenes}, ensure_ascii=False)
        mocked_urlopen.side_effect = [FakeResponse(valid_content), FakeResponse("not-json"), FakeResponse(valid_content)]

        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Durable storyboard job",
            title="Durable storyboard job",
            input_text="A courier races across a stormy city before the final train leaves. " * 10,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)
        create_response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/jobs/",
            {"scene_count": 6},
            format="json",
        )
        self.assert_success_envelope(create_response)
        job_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.data["data"]["status"], VideoGenerationJob.Status.QUEUED)
        self.assertEqual(create_response.data["data"]["attempt_count"], 0)

        duplicate_response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/jobs/",
            {"scene_count": 6},
            format="json",
        )
        self.assertEqual(duplicate_response.status_code, 400)

        latest_response = self.client.get(f"/api/video-projects/{project.id}/storyboard/jobs/latest/")
        self.assert_success_envelope(latest_response)
        self.assertEqual(latest_response.data["data"]["id"], job_id)

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_video_job",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        denied_response = self.client.get(f"/api/video-generation-jobs/{job_id}/")
        self.assertEqual(denied_response.status_code, 404)

        claimed_job = claim_next_video_generation_job()
        self.assertEqual(claimed_job.id, job_id)
        self.assertEqual(claimed_job.status, VideoGenerationJob.Status.RUNNING)
        completed_job = process_video_generation_job(claimed_job)
        self.assertEqual(completed_job.status, VideoGenerationJob.Status.SUCCEEDED)
        self.assertEqual(completed_job.attempt_count, 1)
        project.refresh_from_db()
        self.assertEqual(project.status, VideoProject.Status.STORYBOARD_READY)
        self.assertEqual(VideoScene.objects.filter(project=project).count(), 6)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_JOB,
                object_id=job_id,
                action=AuditLog.Action.STATUS_UPDATE,
                to_status=VideoGenerationJob.Status.SUCCEEDED,
            ).exists()
        )

        retry_project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Retry storyboard job",
            title="Retry storyboard job",
            input_text="An archivist opens a sealed room and must choose what truth to reveal. " * 10,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)
        retry_create_response = self.client.post(
            f"/api/video-projects/{retry_project.id}/storyboard/jobs/",
            {"scene_count": 6},
            format="json",
        )
        retry_job_id = retry_create_response.data["data"]["id"]
        failed_job = process_video_generation_job(claim_next_video_generation_job())
        self.assertEqual(failed_job.status, VideoGenerationJob.Status.FAILED)
        retry_project.refresh_from_db()
        self.assertEqual(retry_project.status, VideoProject.Status.FAILED)

        retry_response = self.client.post(f"/api/video-generation-jobs/{retry_job_id}/retry/", {}, format="json")
        self.assert_success_envelope(retry_response)
        self.assertEqual(retry_response.data["data"]["status"], VideoGenerationJob.Status.QUEUED)
        succeeded_retry = process_video_generation_job(claim_next_video_generation_job())
        self.assertEqual(succeeded_retry.status, VideoGenerationJob.Status.SUCCEEDED)
        self.assertEqual(succeeded_retry.attempt_count, 2)

        stale_project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Stale storyboard job",
            title="Stale storyboard job",
            input_text="A traveler waits for a signal that never arrives. " * 12,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.ANALYZING,
        )
        stale_job = VideoGenerationJob.objects.create(
            project=stale_project,
            requested_by=self.reader,
            status=VideoGenerationJob.Status.RUNNING,
            model_name="storyboard-job-model",
            request_payload={"scene_count": 6},
            attempt_count=1,
            max_attempts=3,
            started_at=timezone.now() - timedelta(minutes=2),
        )
        self.assertEqual(recover_stale_video_generation_jobs(), 1)
        stale_job.refresh_from_db()
        stale_project.refresh_from_db()
        self.assertEqual(stale_job.status, VideoGenerationJob.Status.QUEUED)
        self.assertEqual(stale_project.status, VideoProject.Status.FAILED)

    def test_video_scene_editing_permissions_validation_and_audit(self):
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Editable storyboard",
            title="Editable storyboard",
            input_text="A courier crosses a flooded city to deliver the last medicine before sunrise. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )

        self.client.force_authenticate(user=self.reader)
        storyboard_response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/",
            {"scene_count": 5},
            format="json",
        )
        self.assert_success_envelope(storyboard_response)
        scene = VideoScene.objects.filter(project=project).order_by("scene_no").first()

        self.client.force_authenticate(user=None)
        unauthenticated_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/{scene.id}/",
            {"title": "Opening rescue"},
            format="json",
        )
        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_authenticate(user=self.reader)
        unsafe_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/{scene.id}/",
            {"visual_prompt": "<script>alert(1)</script>"},
            format="json",
        )
        self.assertEqual(unsafe_response.status_code, 400)

        empty_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/{scene.id}/",
            {},
            format="json",
        )
        self.assertEqual(empty_response.status_code, 400)

        update_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/{scene.id}/",
            {
                "title": "Opening rescue",
                "visual_prompt": "Vertical cinematic frame, rain-soaked courier running through the old city.",
                "duration_seconds": scene.duration_seconds + 1,
                "mood": "urgent",
            },
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.assertEqual(update_response.data["data"]["title"], "Opening rescue")
        self.assertEqual(update_response.data["data"]["mood"], "urgent")
        scene.refresh_from_db()
        project.refresh_from_db()
        self.assertEqual(project.duration_target, 61)
        self.assertEqual(scene.status, VideoScene.Status.READY)
        self.assertTrue(
            AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_SCENE,
                object_id=scene.id,
                reviewer=self.reader,
                action=AuditLog.Action.UPDATE,
            ).exists()
        )

        invalid_duration_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/{scene.id}/",
            {"duration_seconds": 31},
            format="json",
        )
        self.assertEqual(invalid_duration_response.status_code, 400)

        long_project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Long storyboard",
            title="Long storyboard",
            input_text="A long night unfolds across eight connected scenes before the final sunrise. " * 9,
            duration_target=90,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        long_storyboard_response = self.client.post(
            f"/api/video-projects/{long_project.id}/storyboard/",
            {"scene_count": 8},
            format="json",
        )
        self.assert_success_envelope(long_storyboard_response)
        long_scene = VideoScene.objects.filter(project=long_project).order_by("scene_no").first()
        total_duration_response = self.client.patch(
            f"/api/video-projects/{long_project.id}/scenes/{long_scene.id}/",
            {"duration_seconds": 30},
            format="json",
        )
        self.assertEqual(total_duration_response.status_code, 400)

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_scene_edit",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        denied_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/{scene.id}/",
            {"title": "Unauthorized edit"},
            format="json",
        )
        self.assertEqual(denied_response.status_code, 404)

        self.client.force_authenticate(user=self.reader)
        missing_response = self.client.patch(
            f"/api/video-projects/{project.id}/scenes/999999/",
            {"title": "Missing scene"},
            format="json",
        )
        self.assertEqual(missing_response.status_code, 404)

    def test_video_story_draft_generation_can_seed_project(self):
        unauthenticated_response = self.client.post(
            "/api/video-projects/story-draft/",
            {"prompt": "边城少年捡到会发光的旧书"},
            format="json",
        )
        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_authenticate(user=self.reader)
        invalid_response = self.client.post(
            "/api/video-projects/story-draft/",
            {"prompt": "<script>alert(1)</script>"},
            format="json",
        )
        self.assertEqual(invalid_response.status_code, 400)

        draft_response = self.client.post(
            "/api/video-projects/story-draft/",
            {
                "prompt": "边城少年捡到会发光的旧书，被迫在家人和真相之间做选择",
                "genre": "fantasy",
                "tone": "high_energy",
                "protagonist": "边城少年",
                "key_conflict": "旧书会救人也会暴露家族秘密",
                "duration_target": 60,
            },
            format="json",
        )
        self.assert_success_envelope(draft_response)
        draft = draft_response.data["data"]
        self.assertGreaterEqual(len(draft["input_text"]), 500)
        self.assertLessEqual(len(draft["input_text"]), 3000)
        self.assertTrue(draft["title"])
        self.assertEqual(draft["aspect_ratio"], "9:16")

        create_response = self.client.post(
            "/api/video-projects/",
            {
                "source_type": "text",
                "title": draft["title"],
                "input_text": draft["input_text"],
                "duration_target": draft["duration_target"],
                "aspect_ratio": draft["aspect_ratio"],
            },
            format="json",
        )
        self.assert_success_envelope(create_response)
        self.assertEqual(create_response.data["data"]["status"], VideoProject.Status.DRAFT)

    def test_ai_chat_requires_valid_payload(self):
        response = self.client.post("/api/ai/chat/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(response.data["code"], 0)
        self.assertIn("message", response.data)

    @patch("common.services.urlopen")
    def test_ai_chat_returns_answer_from_openai_compatible_response(self, mocked_urlopen):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return (
                    b'{"model":"fake-model","choices":[{"message":{"content":"AI answer"}}],'
                    b'"usage":{"total_tokens":10}}'
                )

        mocked_urlopen.return_value = FakeResponse()

        response = self.client.post(
            "/api/ai/chat/",
            {
                "api_key": "test-key",
                "api_url": "https://api.example.com/v1/chat/completions",
                "model": "fake-model",
                "messages": [{"role": "user", "content": "这本小说讲了什么？"}],
                "context": {"novel_title": self.novel.title, "novel_description": self.novel.description},
            },
            format="json",
        )

        self.assert_success_envelope(response)
        self.assertEqual(response.data["data"]["answer"], "AI answer")
        self.assertEqual(response.data["data"]["model"], "fake-model")
        mocked_urlopen.assert_called_once()
