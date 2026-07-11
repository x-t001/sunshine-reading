from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from chapters.models import Chapter
from comments.models import Comment
from common.models import AuditLog
from novels.models import Category, Novel
from rankings.models import RankingItem, RankingType
from video_generation.models import VideoProject


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
