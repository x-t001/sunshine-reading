from django.core.checks import Tags, run_checks
from django.test import SimpleTestCase, override_settings


class VideoAiProviderSystemChecksTests(SimpleTestCase):
    @staticmethod
    def _video_ai_messages():
        return [
            message
            for message in run_checks(tags=[Tags.security])
            if message.id.startswith("video_generation.")
        ]

    @override_settings(
        VIDEO_AI_API_URL="",
        VIDEO_AI_API_KEY="",
        VIDEO_AI_MODEL="",
    )
    def test_provider_is_optional(self):
        self.assertEqual(self._video_ai_messages(), [])

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-test-model",
    )
    def test_valid_provider_configuration_passes(self):
        self.assertEqual(self._video_ai_messages(), [])

    @override_settings(
        VIDEO_AI_API_URL="http://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="",
    )
    def test_invalid_provider_configuration_is_reported_without_key(self):
        messages = self._video_ai_messages()

        self.assertEqual(
            {message.id for message in messages},
            {"video_generation.E001", "video_generation.E002"},
        )
        self.assertNotIn("server-test-key", " ".join(str(message) for message in messages))
