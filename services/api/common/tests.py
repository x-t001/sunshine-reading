import base64
import io
import json
import math
import socket
import ssl
import struct
import tempfile
import wave
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
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
from video_generation.audio_quality import analyze_wav_audio, build_speech_quality_report
from video_generation.models import VideoAsset, VideoGenerationJob, VideoProject, VideoScene
from video_generation.services import claim_next_video_generation_job, process_video_generation_job, recover_stale_video_generation_jobs


class _VideoProviderResponse:
    def __init__(self, content, content_type="application/json", url="https://api.example.com/result"):
        self.content = content
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(content)),
        }
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size=-1):
        return self.content if size is None or size < 0 else self.content[:size]

    def geturl(self):
        return self.url


def _build_test_wav(*, duration_seconds=1.0, amplitude=8000, sample_rate=24000):
    frame_count = max(1, int(duration_seconds * sample_rate))
    frames = bytearray()
    for sample_index in range(frame_count):
        sample = int(amplitude * math.sin(2 * math.pi * 440 * sample_index / sample_rate))
        frames.extend(struct.pack("<h", sample))
    output = io.BytesIO()
    with wave.open(output, "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(sample_rate)
        audio_file.writeframes(frames)
    return output.getvalue()


def _build_agent_production_plan(scene_count):
    return {
        "logline": "主角在限时压力下完成任务，并在行动中揭示真相。",
        "theme": "选择与责任",
        "visual_style": "写实电影感，冷色雨夜，竖屏构图，人物服装和光线保持一致。",
        "characters": [
            {
                "id": "char_protagonist",
                "name": "主角",
                "story_role": "推动任务的核心人物",
                "identity": "二十多岁的城市信使",
                "appearance": "二十多岁，短发，清晰自然的面部特征",
                "behavior": "行动果断，始终保护手中的信件",
                "voice_profile_id": "voice_protagonist",
            }
        ],
        "character_looks": [
            {
                "id": "look_protagonist_rain",
                "character_id": "char_protagonist",
                "label": "雨夜任务装",
                "wardrobe": "深色防水外套和耐磨长裤",
                "hair_makeup": "短发被雨水微微打湿，面部自然无浓妆",
                "signature_features": "左肩旧帆布包带和银色外套拉链",
                "color_palette": "炭黑、冷灰和少量银色",
                "reference_prompt": "同一位短发城市信使，深色防水外套，左肩旧帆布包，正面半身角色设定照",
            }
        ],
        "locations": [
            {
                "id": "loc_rain_city",
                "name": "雨夜旧城",
                "geography": "狭长石板街连接旧车站，街道由左后方向右前方延伸",
                "visual_anchor": "湿润石板路、暖色路灯和远处车站钟楼",
                "time_of_day": "深夜",
                "weather": "稳定小雨",
                "lighting": "冷蓝环境光与暖黄路灯形成稳定对比",
                "color_palette": "冷蓝、湿黑和暖黄",
                "reference_prompt": "深夜旧城石板街，远处车站钟楼，右侧暖黄路灯，稳定小雨，竖屏场景设定图",
            }
        ],
        "props": [
            {
                "id": "prop_letter",
                "name": "密封信件",
                "owner_character_id": "char_protagonist",
                "visual_anchor": "米白信封、深红圆形蜡封和右下角轻微折痕",
                "initial_state": "干燥完整，被收在帆布包内层",
                "continuity_rule": "蜡封始终完整，折痕方向保持一致",
                "reference_prompt": "米白色密封信封，深红圆形蜡封，右下角轻微折痕，纯色背景道具设定照",
            }
        ],
        "dialogue_units": [
            {
                "id": f"line_{index:02d}",
                "beat_no": index,
                "kind": "narration",
                "speaker_id": "narrator",
                "text": f"第{index}步，继续前进。",
                "subtitle_text": f"第{index}步，继续前进。",
                "emotion": "克制而紧迫",
                "pause_after_ms": 300,
                "target_duration_ms": 3000,
                "voice_profile_id": "voice_narrator",
            }
            for index in range(1, scene_count + 1)
        ],
        "continuity_rules": [
            "主角始终穿深色防水外套并携带同一个帆布包。",
            "雨势、夜色和路灯方向在相邻镜头中连续。",
        ],
        "beats": [
            {
                "beat_no": index,
                "purpose": f"推进任务阶段 {index}",
                "action": f"主角完成第 {index} 个连续动作",
                "outcome": f"行动结果自然引向镜头 {index + 1}",
                "location_id": "loc_rain_city",
                "character_ids": ["char_protagonist"],
                "look_ids": ["look_protagonist_rain"],
                "prop_ids": ["prop_letter"],
                "dialogue_unit_ids": [f"line_{index:02d}"],
            }
            for index in range(1, scene_count + 1)
        ],
    }


def _enrich_agent_scenes(scenes, start_index=1, total_scene_count=None):
    if total_scene_count is None:
        total_scene_count = start_index + len(scenes) - 1
    enriched = []
    for index, scene in enumerate(scenes, start=start_index):
        enriched.append(
            {
                **scene,
                "narration_text": f"第{index}步，继续前进。",
                "subtitle_text": f"第{index}步，继续前进。",
                "story_function": f"推进任务阶段 {index}",
                "location_id": "loc_rain_city",
                "character_ids": ["char_protagonist"],
                "look_ids": ["look_protagonist_rain"],
                "prop_states": [{"prop_id": "prop_letter", "state": f"被主角护在胸前，蜡封完整，阶段 {index}"}],
                "dialogue_unit_ids": [f"line_{index:02d}"],
                "start_state": f"主角承接上一镜动作，站在路灯 {index} 附近",
                "end_state": f"主角完成动作并看向下一处路灯 {index + 1}",
                "continuity_anchor": "深色防水外套、帆布包、冷蓝雨夜和右侧暖黄路灯",
                "transition_out": "主角的视线与前进方向引向下一镜" if index < total_scene_count else "",
                "motion_prompt": f"主角向前跑动并完成第 {index} 个明确动作，衣摆和雨滴自然运动",
            }
        )
    return enriched


def _build_dialogue_repair_payload(production_plan, *dialogue_unit_ids):
    dialogue_by_id = {item["id"]: item for item in production_plan["dialogue_units"]}
    return {
        "dialogue_units": [
            {
                "id": dialogue_unit_id,
                "text": dialogue_by_id[dialogue_unit_id]["text"],
                "subtitle_text": dialogue_by_id[dialogue_unit_id]["subtitle_text"],
                "target_duration_ms": dialogue_by_id[dialogue_unit_id]["target_duration_ms"],
                "pause_after_ms": dialogue_by_id[dialogue_unit_id]["pause_after_ms"],
            }
            for dialogue_unit_id in dialogue_unit_ids
        ]
    }


class ApiSmokeTests(TestCase):
    def test_agent_production_plan_repairs_missing_character_looks(self):
        from video_generation.agent_workflow import repair_production_plan
        from video_generation.serializers import VideoAgentProductionPlanSerializer

        production_plan = _build_agent_production_plan(4)
        production_plan["characters"].append(
            {
                "id": "char_mentor",
                "name": "引路人",
                "story_role": "提供关键方向",
                "identity": "熟悉旧城道路的年长引路人",
                "appearance": "五十多岁，清瘦体态，短灰发，眉骨清晰",
                "behavior": "说话克制，只在关键节点指明方向",
                "voice_profile_id": "voice_mentor",
            }
        )
        production_plan["beats"][1]["character_ids"].append("char_mentor")
        production_plan["beats"][1]["look_ids"].append("look_mentor_missing")

        repaired_plan, report = repair_production_plan(production_plan, 4)
        serializer = VideoAgentProductionPlanSerializer(
            data=repaired_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        generated_look = next(
            item for item in repaired_plan["character_looks"] if item["character_id"] == "char_mentor"
        )
        self.assertTrue(generated_look["id"].startswith("look_auto_"))
        self.assertIn("年长引路人", generated_look["wardrobe"])
        self.assertEqual(
            repaired_plan["beats"][1]["look_ids"],
            ["look_protagonist_rain", generated_look["id"]],
        )
        self.assertEqual(report["generated_missing_character_looks"], 1)
        self.assertEqual(report["removed_unknown_look_references"], 1)
        self.assertEqual(report["rewritten_beat_look_references"], 1)
        self.assertTrue(report["applied"])
        self.assertEqual(len(production_plan["character_looks"]), 1)

        malformed_plan = _build_agent_production_plan(4)
        malformed_plan["locations"] = 1
        unrepaired_plan, _ = repair_production_plan(malformed_plan, 4)
        malformed_serializer = VideoAgentProductionPlanSerializer(
            data=unrepaired_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )
        self.assertFalse(malformed_serializer.is_valid())

    def test_agent_production_plan_repairs_out_of_range_dialogue_units(self):
        from video_generation.agent_workflow import repair_production_plan
        from video_generation.serializers import VideoAgentProductionPlanSerializer

        production_plan = _build_agent_production_plan(4)
        production_plan["dialogue_units"].append(
            {
                "id": "line_05_extra",
                "beat_no": 5,
                "kind": "narration",
                "speaker_id": "narrator",
                "text": "越界台词。",
                "subtitle_text": "越界台词。",
                "emotion": "克制",
                "pause_after_ms": 100,
                "target_duration_ms": 1000,
                "voice_profile_id": "voice_narrator",
            }
        )
        production_plan["beats"][-1]["dialogue_unit_ids"].append("line_05_extra")

        repaired_plan, report = repair_production_plan(production_plan, 4)
        serializer = VideoAgentProductionPlanSerializer(
            data=repaired_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            [item["id"] for item in repaired_plan["dialogue_units"]],
            ["line_01", "line_02", "line_03", "line_04"],
        )
        self.assertEqual(repaired_plan["beats"][-1]["dialogue_unit_ids"], ["line_04"])
        self.assertTrue(report["applied"])
        self.assertEqual(report["removed_out_of_range_dialogue_units"], 1)
        self.assertEqual(report["rewritten_beat_dialogue_references"], 1)
        self.assertEqual(production_plan["dialogue_units"][-1]["id"], "line_05_extra")

        malformed_plan = _build_agent_production_plan(4)
        malformed_plan["dialogue_units"][-1]["target_duration_ms"] = "not-a-number"
        unrepaired_plan, unrepaired_report = repair_production_plan(malformed_plan, 4)
        malformed_serializer = VideoAgentProductionPlanSerializer(
            data=unrepaired_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )
        self.assertFalse(malformed_serializer.is_valid())
        self.assertFalse(unrepaired_report["applied"])

    def test_agent_production_plan_normalizes_dialogue_timing_without_rewriting_text(self):
        from video_generation.agent_workflow import repair_production_plan
        from video_generation.serializers import VideoAgentProductionPlanSerializer

        production_plan = _build_agent_production_plan(4)
        production_plan["dialogue_units"][0]["target_duration_ms"] = 4000
        production_plan["dialogue_units"][0]["pause_after_ms"] = 700
        production_plan["dialogue_units"].append(
            {
                "id": "line_01_followup",
                "beat_no": 1,
                "kind": "narration",
                "speaker_id": "narrator",
                "text": "别停。",
                "subtitle_text": "别停。",
                "emotion": "克制而紧迫",
                "pause_after_ms": 300,
                "target_duration_ms": 2000,
                "voice_profile_id": "voice_narrator",
            }
        )
        production_plan["beats"][0]["dialogue_unit_ids"].append("line_01_followup")
        original_texts = [item["text"] for item in production_plan["dialogue_units"]]

        repaired_plan, report = repair_production_plan(production_plan, 4, 5)
        serializer = VideoAgentProductionPlanSerializer(
            data=repaired_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        beat_dialogues = [item for item in repaired_plan["dialogue_units"] if item["beat_no"] == 1]
        self.assertEqual(
            sum(item["target_duration_ms"] + item["pause_after_ms"] for item in beat_dialogues),
            5000,
        )
        self.assertTrue(all(item["target_duration_ms"] >= 500 for item in beat_dialogues))
        self.assertEqual([item["text"] for item in repaired_plan["dialogue_units"]], original_texts)
        self.assertEqual(report["normalized_dialogue_timing_beats"], 1)
        self.assertEqual(report["normalized_dialogue_timing_units"], 2)
        self.assertTrue(report["applied"])
        self.assertEqual(production_plan["dialogue_units"][0]["target_duration_ms"], 4000)
        self.assertEqual(production_plan["dialogue_units"][0]["pause_after_ms"], 700)

    def test_dialogue_repair_payload_cannot_modify_production_structure(self):
        from rest_framework.exceptions import ValidationError

        from video_generation.providers import _apply_dialogue_repair_payload

        production_plan = _build_agent_production_plan(4)
        production_plan["dialogue_units"][0]["text"] = (
            "主角必须赶在列车离站前把密封信件送到钟楼下等待的人手中。"
        )
        valid_source_plan = _build_agent_production_plan(4)
        valid_payload = _build_dialogue_repair_payload(valid_source_plan, "line_01")
        unauthorized_payload = json.loads(json.dumps(valid_payload, ensure_ascii=False))
        unauthorized_payload["dialogue_units"][0]["beat_no"] = 2

        with self.assertRaises(ValidationError):
            _apply_dialogue_repair_payload(production_plan, unauthorized_payload)

        merged_plan = _apply_dialogue_repair_payload(production_plan, valid_payload)
        self.assertEqual(merged_plan["characters"], production_plan["characters"])
        self.assertEqual(merged_plan["beats"], production_plan["beats"])
        self.assertEqual(
            merged_plan["dialogue_units"][0]["text"],
            valid_source_plan["dialogue_units"][0]["text"],
        )
        self.assertNotEqual(
            merged_plan["dialogue_units"][0]["text"],
            production_plan["dialogue_units"][0]["text"],
        )

    def test_agent_production_plan_rejects_reference_and_dialogue_drift(self):
        from video_generation.serializers import VideoAgentProductionPlanSerializer

        mismatched_plan = _build_agent_production_plan(4)
        mismatched_plan["beats"][0]["look_ids"] = []
        mismatched_serializer = VideoAgentProductionPlanSerializer(
            data=mismatched_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )
        self.assertFalse(mismatched_serializer.is_valid())
        self.assertIn("beats", mismatched_serializer.errors)

        dense_dialogue_plan = _build_agent_production_plan(4)
        dense_dialogue_plan["dialogue_units"][0]["text"] = "这是一段明显超过单个五秒镜头自然语速承载能力的旁白文本"
        dense_dialogue_serializer = VideoAgentProductionPlanSerializer(
            data=dense_dialogue_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )
        self.assertFalse(dense_dialogue_serializer.is_valid())
        self.assertIn("dialogue_units", dense_dialogue_serializer.errors)
        self.assertEqual(
            dense_dialogue_serializer.errors["dialogue_units"][0].code,
            "dialogue_text_too_long",
        )

    def test_agent_production_plan_allows_same_speaker_multi_line_beat(self):
        from video_generation.serializers import VideoAgentProductionPlanSerializer

        production_plan = _build_agent_production_plan(4)
        production_plan["dialogue_units"].append(
            {
                "id": "line_01_followup",
                "beat_no": 1,
                "kind": "narration",
                "speaker_id": "narrator",
                "text": "别停。",
                "subtitle_text": "别停。",
                "emotion": "克制而紧迫",
                "pause_after_ms": 100,
                "target_duration_ms": 1000,
                "voice_profile_id": "voice_narrator",
            }
        )
        production_plan["beats"][0]["dialogue_unit_ids"].append("line_01_followup")
        serializer = VideoAgentProductionPlanSerializer(
            data=production_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_agent_production_plan_rejects_multi_speaker_beat(self):
        from video_generation.serializers import VideoAgentProductionPlanSerializer

        production_plan = _build_agent_production_plan(4)
        production_plan["dialogue_units"].append(
            {
                "id": "line_01_reply",
                "beat_no": 1,
                "kind": "dialogue",
                "speaker_id": "char_protagonist",
                "text": "我会继续。",
                "subtitle_text": "我会继续。",
                "emotion": "坚定",
                "pause_after_ms": 100,
                "target_duration_ms": 1000,
                "voice_profile_id": "voice_protagonist",
            }
        )
        production_plan["beats"][0]["dialogue_unit_ids"].append("line_01_reply")
        serializer = VideoAgentProductionPlanSerializer(
            data=production_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("dialogue_units", serializer.errors)

    def test_validation_error_message_preserves_nested_field_path(self):
        from rest_framework.exceptions import ValidationError

        from video_generation.services import _validation_error_message

        error = ValidationError(
            {"beats": [{}, {"dialogue_unit_ids": ["该字段不能超过 4 个元素。"]}]}
        )

        self.assertEqual(
            _validation_error_message(error),
            "beats.1.dialogue_unit_ids: 该字段不能超过 4 个元素。",
        )

    def test_agent_workflow_allows_limited_silent_transition(self):
        from video_generation.serializers import (
            VideoAgentProductionPlanSerializer,
            VideoAiStoryboardResultSerializer,
        )

        production_plan = _build_agent_production_plan(4)
        production_plan["dialogue_units"] = [
            item for item in production_plan["dialogue_units"] if item["beat_no"] != 1
        ]
        production_plan["beats"][0]["dialogue_unit_ids"] = []
        plan_serializer = VideoAgentProductionPlanSerializer(
            data=production_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )
        self.assertTrue(plan_serializer.is_valid(), plan_serializer.errors)

        scenes = _enrich_agent_scenes(
            [
                {
                    "title": f"Atomic shot {index}",
                    "visual_prompt": f"Single-location action shot {index}",
                    "narration_text": f"Narration {index}",
                    "subtitle_text": f"Subtitle {index}",
                    "duration_seconds": 5,
                    "camera_direction": "Tracking shot",
                    "mood": "urgent",
                }
                for index in range(1, 5)
            ]
        )
        scenes[0]["dialogue_unit_ids"] = []
        scenes[0]["narration_text"] = ""
        scenes[0]["subtitle_text"] = ""
        storyboard_serializer = VideoAiStoryboardResultSerializer(
            data={"summary": "包含一个静默转场的分镜", "scenes": scenes},
            context={
                "expected_scene_count": 4,
                "production_plan": plan_serializer.validated_data,
            },
        )
        self.assertTrue(storyboard_serializer.is_valid(), storyboard_serializer.errors)

        overly_silent_plan = _build_agent_production_plan(4)
        overly_silent_plan["dialogue_units"] = [
            item for item in overly_silent_plan["dialogue_units"] if item["beat_no"] not in (1, 2)
        ]
        overly_silent_plan["beats"][0]["dialogue_unit_ids"] = []
        overly_silent_plan["beats"][1]["dialogue_unit_ids"] = []
        overly_silent_serializer = VideoAgentProductionPlanSerializer(
            data=overly_silent_plan,
            context={"expected_scene_count": 4, "clip_duration_seconds": 5},
        )
        self.assertFalse(overly_silent_serializer.is_valid())
        self.assertIn("beats", overly_silent_serializer.errors)

    def test_agent_workflow_uses_five_second_atomic_shots_by_default(self):
        from video_generation.agent_workflow import build_quality_report
        from video_generation.services import _default_scene_count

        scene_count = _default_scene_count(60)
        production_plan = _build_agent_production_plan(scene_count)
        scenes = _enrich_agent_scenes(
            [
                {
                    "title": f"Atomic shot {index}",
                    "visual_prompt": f"Single-location action shot {index}",
                    "narration_text": f"Narration {index}",
                    "subtitle_text": f"Subtitle {index}",
                    "duration_seconds": 5,
                    "camera_direction": "Tracking shot",
                    "mood": "focused",
                }
                for index in range(1, scene_count + 1)
            ]
        )

        report = build_quality_report(scenes, production_plan, 60, 5)

        self.assertEqual(scene_count, 12)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["score"], 100)
        self.assertEqual(report["metrics"]["scenes_over_clip_duration"], 0)
        self.assertEqual(report["metrics"]["render_target_fps"], 30)
        self.assertEqual(report["metrics"]["state_link_count"], 11)
        self.assertIn("visual_semantic_review_required", {issue["code"] for issue in report["issues"]})

    def test_visual_world_model_locks_character_scene_and_state_contracts(self):
        from video_generation.agent_workflow import (
            build_scene_agent_metadata,
            build_visual_world_model,
        )

        production_plan = _build_agent_production_plan(2)
        scenes = _enrich_agent_scenes(
            [
                {
                    "title": f"Model shot {index}",
                    "visual_prompt": f"Single-location model shot {index}",
                    "duration_seconds": 5,
                    "camera_direction": "Tracking shot",
                    "mood": "focused",
                }
                for index in range(1, 3)
            ]
        )
        visual_world_model = build_visual_world_model(production_plan, render_fps=24)
        metadata = build_scene_agent_metadata(
            scenes[1],
            production_plan,
            2,
            previous_scene_data=scenes[0],
            visual_world_model=visual_world_model,
        )

        self.assertEqual(visual_world_model["version"], "1.1")
        self.assertEqual(len(visual_world_model["character_models"]), 1)
        self.assertEqual(len(visual_world_model["scene_models"]), 1)
        self.assertEqual(len(visual_world_model["prop_models"]), 1)
        self.assertEqual(
            visual_world_model["generation_policy"]["strategy"],
            "canonical_assets_plus_shot_delta",
        )
        self.assertEqual(visual_world_model["frame_policy"]["target_fps"], 24)
        self.assertEqual(
            metadata["continuity_contract"]["previous_end_state"],
            scenes[0]["end_state"],
        )
        self.assertEqual(
            metadata["continuity_contract"]["required_start_state"],
            scenes[0]["end_state"],
        )
        self.assertEqual(metadata["continuity_contract"]["character_model_ids"], ["model_look_protagonist_rain"])
        self.assertEqual(metadata["continuity_contract"]["scene_model_id"], "model_loc_rain_city")
        self.assertIn("物理约束", metadata["prompt_adapter"]["video_prompt"])
        self.assertIn("逻辑约束", metadata["prompt_adapter"]["video_prompt"])
        self.assertIn("身体穿模", metadata["prompt_adapter"]["negative_prompt"])
        self.assertEqual(metadata["prompt_adapter"]["frame_policy"]["target_fps"], 24)

    def test_visual_continuity_plan_groups_shots_and_reuses_canonical_anchors(self):
        from video_generation.agent_workflow import (
            build_scene_agent_metadata,
            build_visual_continuity_plan,
            build_visual_world_model,
        )

        production_plan = _build_agent_production_plan(3)
        production_plan["locations"].append(
            {
                "id": "loc_station",
                "name": "旧车站站台",
                "geography": "狭长站台由左向右延伸，轨道位于画面后方",
                "visual_anchor": "绿色站牌、黑色铁柱和圆形站钟",
                "time_of_day": "深夜",
                "weather": "站棚外稳定小雨",
                "lighting": "右侧暖黄顶灯与冷蓝月台环境光",
                "color_palette": "冷蓝、墨绿和暖黄",
                "reference_prompt": "同一座深夜旧车站站台，绿色站牌、黑色铁柱、圆形站钟",
            }
        )
        production_plan["beats"][2]["location_id"] = "loc_station"
        scenes = _enrich_agent_scenes(
            [
                {
                    "title": f"连续镜头 {index}",
                    "visual_prompt": f"主角完成第 {index} 个连续动作",
                    "duration_seconds": 5,
                    "camera_direction": "中景跟拍",
                    "mood": "紧迫",
                }
                for index in range(1, 4)
            ]
        )
        scenes[2]["location_id"] = "loc_station"
        visual_world_model = build_visual_world_model(production_plan, render_fps=30)
        visual_world_model["visual_continuity_plan"] = build_visual_continuity_plan(
            scenes,
            production_plan,
            visual_world_model,
        )

        plan = visual_world_model["visual_continuity_plan"]
        self.assertEqual(len(plan["continuity_groups"]), 2)
        self.assertEqual(plan["continuity_groups"][0]["scene_nos"], [1, 2])
        self.assertEqual(plan["shots"][1]["relationship_to_previous"], "continuous_action")
        self.assertEqual(plan["shots"][2]["relationship_to_previous"], "location_transition")
        first_metadata = build_scene_agent_metadata(
            scenes[0],
            production_plan,
            1,
            visual_world_model=visual_world_model,
        )
        second_metadata = build_scene_agent_metadata(
            scenes[1],
            production_plan,
            2,
            previous_scene_data=scenes[0],
            visual_world_model=visual_world_model,
        )
        first_prompt = first_metadata["prompt_adapter"]["image_prompt"]
        second_prompt = second_metadata["prompt_adapter"]["image_prompt"]
        self.assertIn("视觉圣经", first_prompt)
        self.assertIn("角色不可变", first_prompt)
        self.assertIn("场景不可变", first_prompt)
        self.assertIn("本镜仅变化", second_prompt)
        self.assertIn("承接分镜1", second_prompt)
        self.assertIn("左肩旧帆布包带", first_prompt)
        self.assertIn("左肩旧帆布包带", second_prompt)
        self.assertLessEqual(len(first_prompt), 980)
        self.assertLessEqual(len(second_prompt), 980)
        self.assertEqual(
            first_metadata["prompt_adapter"]["anchor_fingerprint"],
            second_metadata["prompt_adapter"]["anchor_fingerprint"],
        )
        self.assertEqual(
            second_metadata["visual_plan"]["continuity_group_id"],
            "sequence_01",
        )

    @patch("video_generation.rendering._run_ffmpeg")
    @patch("video_generation.rendering.get_ffmpeg_executable")
    def test_video_tail_frame_extraction_validates_jpeg_output(
        self,
        mocked_get_ffmpeg_executable,
        mocked_run_ffmpeg,
    ):
        from video_generation.rendering import extract_video_tail_frame

        tail_content = b"\xff\xd8\xff\xe0" + b"tail-frame" * 32
        mocked_get_ffmpeg_executable.return_value = Path("ffmpeg-test.exe")

        def fake_ffmpeg(_executable, arguments, working_directory, _timeout_seconds):
            (Path(working_directory) / arguments[-1]).write_bytes(tail_content)

        mocked_run_ffmpeg.side_effect = fake_ffmpeg
        with tempfile.TemporaryDirectory() as temporary_directory:
            video_path = Path(temporary_directory) / "scene.mp4"
            video_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
            result = extract_video_tail_frame(
                video_path,
                timeout_seconds=10,
                max_file_bytes=1024 * 1024,
            )

        self.assertEqual(result["content"], tail_content)
        self.assertEqual(result["mime_type"], "image/jpeg")
        self.assertEqual(result["file_size"], len(tail_content))
        ffmpeg_arguments = mocked_run_ffmpeg.call_args.args[1]
        self.assertIn("-sseof", ffmpeg_arguments)
        self.assertIn("-frames:v", ffmpeg_arguments)

    @override_settings(
        VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME=True,
        VIDEO_CLIP_USE_SCENE_IMAGE=True,
        VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES=5 * 1024 * 1024,
    )
    def test_video_reference_frame_prefers_previous_tail_and_falls_back_to_scene_image(self):
        from video_generation.services import _load_scene_video_reference_frame

        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="Tail frame continuity",
            input_text="Tail frame continuity source " * 20,
            duration_target=30,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        first_scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="First scene",
            duration_seconds=5,
            status=VideoScene.Status.READY,
        )
        second_scene = VideoScene.objects.create(
            project=project,
            scene_no=2,
            title="Second scene",
            duration_seconds=5,
            status=VideoScene.Status.READY,
        )
        tail_content = b"\xff\xd8\xff\xe0" + b"previous-tail" * 32
        scene_image_content = b"\x89PNG\r\n\x1a\n" + b"scene-image" * 32

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            video_storage_path = Path(
                "video_projects",
                str(project.id),
                "scenes",
                "scene-01",
                "video-job-1.mp4",
            ).as_posix()
            video_path = Path(media_root) / video_storage_path
            video_path.parent.mkdir(parents=True, exist_ok=True)
            video_path.write_bytes(b"\x00\x00\x00\x18ftypmp42")
            tail_path = video_path.with_name(f"{video_path.stem}-tail.jpg")
            tail_path.write_bytes(tail_content)
            previous_video_asset = VideoAsset.objects.create(
                project=project,
                scene=first_scene,
                asset_type=VideoAsset.AssetType.VIDEO,
                status=VideoAsset.Status.READY,
                storage_path=video_storage_path,
                file_name="scene-01.mp4",
                mime_type="video/mp4",
                file_size=video_path.stat().st_size,
                provider="test",
                metadata={"tail_frame": {"status": "ready"}},
            )

            image_storage_path = Path(
                "video_projects",
                str(project.id),
                "scenes",
                "scene-02",
                "image.png",
            ).as_posix()
            image_path = Path(media_root) / image_storage_path
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(scene_image_content)
            scene_image_asset = VideoAsset.objects.create(
                project=project,
                scene=second_scene,
                asset_type=VideoAsset.AssetType.IMAGE,
                status=VideoAsset.Status.READY,
                storage_path=image_storage_path,
                file_name="scene-02.png",
                mime_type="image/png",
                file_size=image_path.stat().st_size,
                provider="test",
            )

            reference_frame, fallback_reasons = _load_scene_video_reference_frame(second_scene)
            self.assertEqual(reference_frame["content"], tail_content)
            self.assertEqual(reference_frame["mode"], "previous_scene_tail_base64")
            self.assertEqual(reference_frame["asset_id"], previous_video_asset.id)
            self.assertEqual(reference_frame["source_scene_no"], 1)
            self.assertEqual(fallback_reasons, [])

            tail_path.unlink()
            reference_frame, fallback_reasons = _load_scene_video_reference_frame(second_scene)
            self.assertEqual(reference_frame["content"], scene_image_content)
            self.assertEqual(reference_frame["mode"], "scene_image_base64")
            self.assertEqual(reference_frame["asset_id"], scene_image_asset.id)
            self.assertEqual(reference_frame["source_scene_no"], 2)
            self.assertEqual(fallback_reasons, ["reference_frame_file_missing"])

    def test_glm_content_safety_error_has_actionable_message(self):
        from video_generation.providers import _glm_http_error_message

        error_body = json.dumps({"error": {"code": "1301"}}).encode("utf-8")
        error = HTTPError("https://api.example.com/async-result/task-1", 400, "Bad Request", {}, io.BytesIO(error_body))

        message = _glm_http_error_message(error, "短视频画面结果查询")

        self.assertIn("内容安全策略", message)
        self.assertIn("业务错误码 1301", message)
        self.assertNotIn("请求参数", message)

    def test_glm_illegal_field_error_is_not_reported_as_quota_failure(self):
        from video_generation.providers import _glm_http_error_message

        error_body = json.dumps(
            {"error": {"code": "1214", "message": "size 参数非法"}}
        ).encode("utf-8")
        error = HTTPError(
            "https://api.example.com/videos/generations",
            400,
            "Bad Request",
            {},
            io.BytesIO(error_body),
        )

        message = _glm_http_error_message(error, "短视频画面生成")

        self.assertIn("字段取值不合法", message)
        self.assertIn("业务错误码 1214", message)
        self.assertNotIn("额度", message)

    def test_video_provider_network_errors_have_safe_actionable_messages(self):
        from video_generation.providers import _provider_network_error_message

        cases = (
            (URLError(socket.gaierror(11001, "open.bigmodel.cn")), "域名解析失败"),
            (URLError(ConnectionRefusedError(10061, "open.bigmodel.cn")), "连接被拒绝"),
            (URLError(socket.timeout("open.bigmodel.cn")), "连接超时"),
            (URLError(ssl.SSLError("open.bigmodel.cn")), "TLS 握手失败"),
        )

        for error, expected_message in cases:
            with self.subTest(expected_message=expected_message):
                message = _provider_network_error_message(error, "短视频画面生成服务")
                self.assertIn(expected_message, message)
                self.assertNotIn("open.bigmodel.cn", message)

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

    def test_video_project_novel_source_permissions_range_snapshot_and_validation(self):
        first_content = "第一章里，信使在暴雨中接到送药任务，并发现城市道路正在快速封闭。" * 120
        second_content = "第二章里，信使穿过旧城区，在倒塌的桥边救下掌握备用路线的医生。" * 120
        third_content = "第三章里，两人抵达医院，却必须在最后一剂药和新的求救信号之间选择。" * 120
        self.chapter.content = first_content
        self.chapter.word_count = len(first_content)
        self.chapter.save(update_fields=["content", "word_count", "updated_at"])
        second_chapter = Chapter.objects.create(
            novel=self.novel,
            title="第二章",
            chapter_number=2,
            content=second_content,
            word_count=len(second_content),
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
            published_at=timezone.now(),
        )
        third_chapter = Chapter.objects.create(
            novel=self.novel,
            title="第三章",
            chapter_number=3,
            content=third_content,
            word_count=len(third_content),
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
            published_at=timezone.now(),
        )

        author_first_content = "作者草稿第一章记录守塔人发现海面异常光芒，并决定独自调查。" * 80
        author_second_content = "作者草稿第二章记录守塔人在隐瞒真相和保护村庄之间做出选择。" * 80
        self.pending_chapter.content = author_first_content
        self.pending_chapter.word_count = len(author_first_content)
        self.pending_chapter.save(update_fields=["content", "word_count", "updated_at"])
        Chapter.objects.create(
            novel=self.pending_novel,
            title="待审核第二章",
            chapter_number=2,
            content=author_second_content,
            word_count=len(author_second_content),
            status=Chapter.Status.DRAFT,
            audit_status=Chapter.AuditStatus.PENDING,
        )

        unauthenticated_response = self.client.get("/api/video-source-novels/")
        self.assertEqual(unauthenticated_response.status_code, 401)

        self.client.force_authenticate(user=self.reader)
        source_list_response = self.client.get("/api/video-source-novels/?keyword=烟火")
        self.assert_success_envelope(source_list_response)
        self.assertEqual(source_list_response.data["data"]["count"], 1)
        source_novel = source_list_response.data["data"]["results"][0]
        self.assertEqual(source_novel["id"], self.novel.id)
        self.assertEqual(source_novel["chapter_count"], 3)
        self.assertEqual(source_novel["first_chapter_number"], 1)
        self.assertEqual(source_novel["last_chapter_number"], 3)
        self.assertEqual(source_novel["source_access"], "public")

        create_response = self.client.post(
            "/api/video-projects/from-novel/",
            {
                "novel_id": self.novel.id,
                "start_chapter_number": 1,
                "end_chapter_number": 3,
                "duration_target": 90,
            },
            format="json",
        )
        self.assert_success_envelope(create_response)
        project_data = create_response.data["data"]
        self.assertEqual(project_data["source_type"], VideoProject.SourceType.NOVEL)
        self.assertEqual(project_data["source_novel_id"], self.novel.id)
        self.assertIsNone(project_data["source_chapter_id"])
        self.assertIn("第 1-3 章", project_data["source_title"])
        self.assertLessEqual(len(project_data["input_text"]), 6000)
        self.assertIn(f"第 {self.chapter.chapter_number} 章 {self.chapter.title}", project_data["input_text"])
        self.assertIn(f"第 {second_chapter.chapter_number} 章 {second_chapter.title}", project_data["input_text"])
        self.assertIn(f"第 {third_chapter.chapter_number} 章 {third_chapter.title}", project_data["input_text"])
        self.assertTrue(project_data["source_excerpt_hash"])
        audit_log = AuditLog.objects.get(
            content_type=AuditLog.ContentType.VIDEO_PROJECT,
            object_id=project_data["id"],
            reviewer=self.reader,
            action=AuditLog.Action.CREATE,
        )
        self.assertNotIn(first_content[:100], audit_log.reason)

        reversed_range_response = self.client.post(
            "/api/video-projects/from-novel/",
            {"novel_id": self.novel.id, "start_chapter_number": 3, "end_chapter_number": 1},
            format="json",
        )
        self.assertEqual(reversed_range_response.status_code, 400)
        oversized_range_response = self.client.post(
            "/api/video-projects/from-novel/",
            {"novel_id": self.novel.id, "start_chapter_number": 1, "end_chapter_number": 11},
            format="json",
        )
        self.assertEqual(oversized_range_response.status_code, 400)

        unsafe_chapter = Chapter.objects.create(
            novel=self.novel,
            title="危险第四章",
            chapter_number=4,
            content="<script>alert(1)</script>" + ("后续安全正文" * 40),
            word_count=240,
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
            published_at=timezone.now(),
        )
        unsafe_range_response = self.client.post(
            "/api/video-projects/from-novel/",
            {"novel_id": self.novel.id, "start_chapter_number": 3, "end_chapter_number": unsafe_chapter.chapter_number},
            format="json",
        )
        self.assertEqual(unsafe_range_response.status_code, 400)

        self.client.force_authenticate(user=self.author)
        author_list_response = self.client.get("/api/video-source-novels/?keyword=待审核")
        self.assert_success_envelope(author_list_response)
        self.assertEqual(author_list_response.data["data"]["results"][0]["source_access"], "owned")
        author_create_response = self.client.post(
            "/api/video-projects/from-novel/",
            {"novel_id": self.pending_novel.id, "start_chapter_number": 1, "end_chapter_number": 2},
            format="json",
        )
        self.assert_success_envelope(author_create_response)

        User = get_user_model()
        other_reader = User.objects.create_user(
            username="other_reader_novel_source",
            password="password12345Strong!",
            role="reader",
        )
        self.client.force_authenticate(user=other_reader)
        private_source_response = self.client.post(
            "/api/video-projects/from-novel/",
            {"novel_id": self.pending_novel.id, "start_chapter_number": 1, "end_chapter_number": 2},
            format="json",
        )
        self.assertEqual(private_source_response.status_code, 404)

        self.client.force_authenticate(user=self.admin)
        admin_create_response = self.client.post(
            "/api/video-projects/from-novel/",
            {"novel_id": self.pending_novel.id, "start_chapter_number": 1, "end_chapter_number": 2},
            format="json",
        )
        self.assert_success_envelope(admin_create_response)

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

    @override_settings(VIDEO_AI_API_URL="", VIDEO_AI_API_KEY="")
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
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=120,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=150,
        VIDEO_AI_THINKING_TYPE="disabled",
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

        scenes = _enrich_agent_scenes([
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
        ])
        production_plan = _build_agent_production_plan(6)
        production_plan["dialogue_units"].append(
            {
                "id": "line_07_extra",
                "beat_no": 7,
                "kind": "narration",
                "speaker_id": "narrator",
                "text": "额外一步。",
                "subtitle_text": "额外一步。",
                "emotion": "克制",
                "pause_after_ms": 100,
                "target_duration_ms": 1000,
                "voice_profile_id": "voice_narrator",
            }
        )
        production_plan["beats"][-1]["dialogue_unit_ids"].append("line_07_extra")
        production_plan["dialogue_units"][0]["target_duration_ms"] = 5000
        production_plan_content = json.dumps(production_plan, ensure_ascii=False)
        storyboard_content = json.dumps({"summary": "AI generated summary", "scenes": scenes}, ensure_ascii=False)
        mocked_urlopen.side_effect = [
            FakeResponse(
                {
                    "model": "storyboard-test-model",
                    "choices": [{"message": {"content": production_plan_content}}],
                    "usage": {"total_tokens": 120},
                }
            ),
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
                    "choices": [{"message": {"content": production_plan_content}}],
                    "usage": {"total_tokens": 120},
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
        self.assertEqual(response.data["data"]["agent_workflow"]["version"], "2.2")
        workflow = response.data["data"]["agent_workflow"]
        self.assertEqual(len(workflow["stages"]), 7)
        self.assertEqual(workflow["stages"][1]["id"], "schema_guard")
        self.assertEqual(workflow["stages"][2]["id"], "visual_modeler")
        self.assertTrue(workflow["repair_report"]["applied"])
        self.assertEqual(workflow["repair_report"]["removed_out_of_range_dialogue_units"], 1)
        self.assertEqual(workflow["repair_report"]["rewritten_beat_dialogue_references"], 1)
        self.assertEqual(workflow["repair_report"]["normalized_dialogue_timing_beats"], 1)
        self.assertEqual(workflow["repair_report"]["normalized_dialogue_timing_units"], 1)
        self.assertEqual(workflow["quality_report"]["metrics"]["provider_call_count"], 2)
        first_scene_metadata = response.data["data"]["scenes"][0]["agent_metadata"]
        adapted_prompt = first_scene_metadata["prompt_adapter"]["video_prompt"]
        self.assertIn("核心动作", adapted_prompt)
        self.assertIn("角色固定", adapted_prompt)
        self.assertIn("物理约束", adapted_prompt)
        self.assertIn("逻辑约束", adapted_prompt)
        self.assertLessEqual(len(adapted_prompt), 460)
        self.assertIn("角色不可变", first_scene_metadata["prompt_adapter"]["image_prompt"])
        self.assertLessEqual(len(first_scene_metadata["prompt_adapter"]["image_prompt"]), 980)
        self.assertEqual(first_scene_metadata["audio_script"]["text"], "第1步，继续前进。")
        self.assertEqual(first_scene_metadata["look_ids"], ["look_protagonist_rain"])
        second_scene_metadata = response.data["data"]["scenes"][1]["agent_metadata"]
        self.assertEqual(
            second_scene_metadata["continuity_contract"]["previous_end_state"],
            first_scene_metadata["end_state"],
        )
        self.assertEqual(len(workflow["visual_world_model"]["character_models"]), 1)
        self.assertEqual(len(workflow["visual_world_model"]["scene_models"]), 1)
        self.assertEqual(len(workflow["visual_world_model"]["prop_models"]), 1)
        self.assertEqual(
            workflow["quality_report"]["metrics"]["continuity_group_count"],
            1,
        )
        self.assertEqual(
            workflow["quality_report"]["metrics"]["linked_shot_count"],
            5,
        )
        self.assertEqual(workflow["visual_world_model"]["frame_policy"]["target_fps"], 30)
        provider_request = mocked_urlopen.call_args_list[0].args[0]
        provider_payload = json.loads(provider_request.data.decode("utf-8"))
        self.assertEqual(provider_request.get_header("Authorization"), "Bearer server-test-key")
        self.assertEqual(provider_payload["thinking"], {"type": "disabled"})
        self.assertEqual(mocked_urlopen.call_args_list[0].kwargs["timeout"], 120)
        self.assertEqual(mocked_urlopen.call_args_list[1].kwargs["timeout"], 150)
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
        VIDEO_AI_MODEL="storyboard-batch-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=120,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=150,
        VIDEO_AI_THINKING_TYPE="disabled",
        VIDEO_CLIP_DURATION_SECONDS=5,
    )
    @patch("video_generation.providers.urlopen")
    def test_ai_storyboard_generates_twelve_scenes_in_two_continuous_batches(self, mocked_urlopen):
        def provider_response(content, total_tokens):
            return _VideoProviderResponse(
                json.dumps(
                    {
                        "model": "storyboard-batch-model",
                        "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
                        "usage": {"total_tokens": total_tokens},
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )

        production_plan = _build_agent_production_plan(12)
        first_batch = _enrich_agent_scenes(
            [
                {
                    "title": f"批次一镜头 {index}",
                    "visual_prompt": f"雨夜旧城第 {index} 镜，主角持续前进，主体、环境、光线和构图清晰。",
                    "duration_seconds": 5,
                    "camera_direction": "稳定跟拍",
                    "mood": "紧迫",
                }
                for index in range(1, 7)
            ],
            start_index=1,
            total_scene_count=12,
        )
        second_batch = _enrich_agent_scenes(
            [
                {
                    "title": f"批次二镜头 {index}",
                    "visual_prompt": f"雨夜旧城第 {index} 镜，主角延续行动，主体、环境、光线和构图清晰。",
                    "duration_seconds": 5,
                    "camera_direction": "稳定跟拍",
                    "mood": "紧迫",
                }
                for index in range(7, 13)
            ],
            start_index=7,
            total_scene_count=12,
        )
        second_batch[0]["start_state"] = first_batch[-1]["end_state"]
        mocked_urlopen.side_effect = [
            provider_response(production_plan, 100),
            provider_response({"summary": "两批连续生成的完整分镜", "scenes": first_batch}, 200),
            provider_response({"summary": "第二批分镜", "scenes": second_batch}, 220),
        ]
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Twelve scene batch storyboard",
            title="Twelve scene batch storyboard",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 12},
            format="json",
        )

        self.assert_success_envelope(response)
        workflow = response.data["data"]["agent_workflow"]
        shot_stage = next(stage for stage in workflow["stages"] if stage["id"] == "shot_director")
        self.assertEqual(len(response.data["data"]["scenes"]), 12)
        self.assertEqual(response.data["data"]["summary"], "两批连续生成的完整分镜")
        self.assertEqual(workflow["quality_report"]["metrics"]["provider_call_count"], 3)
        self.assertEqual(shot_stage["metrics"]["batch_size"], 6)
        self.assertEqual(shot_stage["metrics"]["batch_count"], 2)
        self.assertEqual(shot_stage["metrics"]["repair_call_count"], 0)
        self.assertEqual(shot_stage["usage"]["total_tokens"], 420)
        self.assertEqual(mocked_urlopen.call_count, 3)
        first_shot_payload = json.loads(mocked_urlopen.call_args_list[1].args[0].data.decode("utf-8"))
        second_shot_payload = json.loads(mocked_urlopen.call_args_list[2].args[0].data.decode("utf-8"))
        first_shot_system_prompt = first_shot_payload["messages"][0]["content"]
        first_shot_prompt = first_shot_payload["messages"][1]["content"]
        second_shot_prompt = second_shot_payload["messages"][1]["content"]
        self.assertIn("禁止人物、衣物、道具或环境表面互相穿透", first_shot_system_prompt)
        self.assertIn("当前批次镜头范围：1-6 / 12", first_shot_prompt)
        self.assertIn("当前批次必须恰好返回 6 个 scenes", first_shot_prompt)
        self.assertIn('"visual_models"', first_shot_prompt)
        self.assertIn('"id": "model_look_protagonist_rain"', first_shot_prompt)
        self.assertIn('"id": "model_loc_rain_city"', first_shot_prompt)
        self.assertNotIn("line_07", first_shot_prompt)
        self.assertNotIn("故事正文：", first_shot_prompt)
        self.assertIn("当前批次镜头范围：7-12 / 12", second_shot_prompt)
        self.assertIn(first_batch[-1]["end_state"], second_shot_prompt)
        self.assertNotIn("line_01", second_shot_prompt)

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-batch-repair-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=120,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=150,
        VIDEO_AI_THINKING_TYPE="disabled",
        VIDEO_CLIP_DURATION_SECONDS=5,
    )
    @patch("video_generation.providers.urlopen")
    def test_ai_storyboard_repairs_only_the_invalid_shot_batch_once(self, mocked_urlopen):
        def provider_response(content, total_tokens):
            return _VideoProviderResponse(
                json.dumps(
                    {
                        "model": "storyboard-batch-repair-model",
                        "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
                        "usage": {"total_tokens": total_tokens},
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )

        production_plan = _build_agent_production_plan(12)
        first_batch = _enrich_agent_scenes(
            [
                {
                    "title": f"修复批次镜头 {index}",
                    "visual_prompt": f"雨夜旧城第 {index} 镜，主角执行连续动作，细节和构图清晰。",
                    "duration_seconds": 5,
                    "camera_direction": "稳定跟拍",
                    "mood": "紧迫",
                }
                for index in range(1, 7)
            ],
            start_index=1,
            total_scene_count=12,
        )
        second_batch = _enrich_agent_scenes(
            [
                {
                    "title": f"后续批次镜头 {index}",
                    "visual_prompt": f"雨夜旧城第 {index} 镜，主角延续行动，细节和构图清晰。",
                    "duration_seconds": 5,
                    "camera_direction": "稳定跟拍",
                    "mood": "紧迫",
                }
                for index in range(7, 13)
            ],
            start_index=7,
            total_scene_count=12,
        )
        second_batch[0]["start_state"] = first_batch[-1]["end_state"]
        mocked_urlopen.side_effect = [
            provider_response(production_plan, 100),
            provider_response({"summary": "少镜头的无效批次", "scenes": first_batch[:5]}, 160),
            provider_response({"summary": "已修复的第一批", "scenes": first_batch}, 90),
            provider_response({"summary": "第二批", "scenes": second_batch}, 220),
        ]
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Shot batch repair",
            title="Shot batch repair",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 12},
            format="json",
        )

        self.assert_success_envelope(response)
        workflow = response.data["data"]["agent_workflow"]
        shot_stage = next(stage for stage in workflow["stages"] if stage["id"] == "shot_director")
        self.assertEqual(len(response.data["data"]["scenes"]), 12)
        self.assertEqual(workflow["quality_report"]["metrics"]["provider_call_count"], 4)
        self.assertEqual(shot_stage["metrics"]["batch_count"], 2)
        self.assertEqual(shot_stage["metrics"]["repair_call_count"], 1)
        self.assertEqual(shot_stage["usage"]["total_tokens"], 470)
        self.assertEqual(mocked_urlopen.call_count, 4)
        self.assertEqual(
            [call.kwargs["timeout"] for call in mocked_urlopen.call_args_list],
            [120, 150, 150, 150],
        )
        repair_payload = json.loads(mocked_urlopen.call_args_list[2].args[0].data.decode("utf-8"))
        self.assertEqual(repair_payload["temperature"], 0.1)
        self.assertIn("原子镜头批次契约修复 Agent", repair_payload["messages"][0]["content"])
        self.assertIn("AI storyboard must contain exactly 6 scenes", repair_payload["messages"][1]["content"])
        self.assertIn("当前批次必须恰好返回 6 个 scenes", repair_payload["messages"][1]["content"])

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-repair-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=120,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=150,
        VIDEO_AI_THINKING_TYPE="disabled",
    )
    @patch("video_generation.providers.urlopen")
    def test_ai_storyboard_runs_bounded_schema_and_dialogue_repairs(self, mocked_urlopen):
        def provider_response(content, total_tokens):
            return _VideoProviderResponse(
                json.dumps(
                    {
                        "model": "storyboard-repair-model",
                        "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
                        "usage": {"total_tokens": total_tokens},
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )

        invalid_plan = _build_agent_production_plan(5)
        repaired_plan = _build_agent_production_plan(6)
        repaired_plan["dialogue_units"][0]["target_duration_ms"] = 5000
        repaired_plan["dialogue_units"][0]["text"] = (
            "主角必须赶在列车离站前把密封信件送到钟楼下等待的人手中。"
        )
        repaired_plan["dialogue_units"][0]["subtitle_text"] = repaired_plan["dialogue_units"][0]["text"]
        dialogue_repaired_plan = _build_agent_production_plan(6)
        scenes = _enrich_agent_scenes(
            [
                {
                    "title": f"修复后镜头 {index}",
                    "visual_prompt": f"雨夜旧城中主角完成第 {index} 个连续动作，冷蓝环境光与暖黄路灯清晰可见。",
                    "narration_text": f"第{index}步，继续前进。",
                    "subtitle_text": f"第{index}步，继续前进。",
                    "duration_seconds": 10,
                    "camera_direction": "跟拍",
                    "mood": "紧迫",
                }
                for index in range(1, 7)
            ]
        )
        mocked_urlopen.side_effect = [
            provider_response(invalid_plan, 100),
            provider_response(repaired_plan, 80),
            provider_response(_build_dialogue_repair_payload(dialogue_repaired_plan, "line_01"), 60),
            provider_response({"summary": "结构修复后的完整分镜", "scenes": scenes}, 200),
        ]
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Bounded schema repair",
            title="Bounded schema repair",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 6},
            format="json",
        )

        self.assert_success_envelope(response)
        workflow = response.data["data"]["agent_workflow"]
        self.assertEqual([stage["id"] for stage in workflow["stages"]], [
            "story_architect",
            "schema_repair",
            "dialogue_repair",
            "schema_guard",
            "visual_modeler",
            "shot_director",
            "visual_sequence_planner",
            "prompt_adapter",
            "quality_supervisor",
        ])
        self.assertTrue(workflow["repair_report"]["provider_schema_repair_applied"])
        self.assertEqual(workflow["repair_report"]["provider_schema_repair_call_count"], 1)
        self.assertTrue(workflow["repair_report"]["provider_dialogue_repair_applied"])
        self.assertEqual(workflow["repair_report"]["provider_dialogue_repair_call_count"], 1)
        self.assertEqual(workflow["repair_report"]["normalized_dialogue_timing_beats"], 1)
        self.assertEqual(workflow["repair_report"]["normalized_dialogue_timing_units"], 1)
        self.assertEqual(workflow["quality_report"]["metrics"]["provider_call_count"], 4)
        self.assertEqual(workflow["stages"][1]["usage"]["total_tokens"], 80)
        self.assertEqual(workflow["stages"][2]["usage"]["total_tokens"], 60)
        self.assertEqual(len(response.data["data"]["scenes"]), 6)
        self.assertEqual(mocked_urlopen.call_count, 4)
        self.assertEqual(
            [call.kwargs["timeout"] for call in mocked_urlopen.call_args_list],
            [120, 120, 120, 150],
        )
        repair_request = mocked_urlopen.call_args_list[1].args[0]
        repair_payload = json.loads(repair_request.data.decode("utf-8"))
        self.assertEqual(repair_payload["temperature"], 0.1)
        self.assertIn("硬性节拍数量：6", repair_payload["messages"][1]["content"])
        self.assertIn("剧情策划必须包含 6 个连续节拍", repair_payload["messages"][1]["content"])
        self.assertNotIn("server-test-key", json.dumps(repair_payload, ensure_ascii=False))
        dialogue_request = mocked_urlopen.call_args_list[2].args[0]
        dialogue_payload = json.loads(dialogue_request.data.decode("utf-8"))
        self.assertIn("台词预算精编 Agent", dialogue_payload["messages"][0]["content"])
        self.assertIn('"actual_text_characters"', dialogue_payload["messages"][1]["content"])
        self.assertIn('"hard_max_text_characters": 25', dialogue_payload["messages"][1]["content"])

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-dialogue-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=120,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=150,
        VIDEO_AI_THINKING_TYPE="disabled",
    )
    @patch("video_generation.providers.urlopen")
    def test_ai_storyboard_routes_dialogue_density_failure_to_dialogue_agent(self, mocked_urlopen):
        def provider_response(content, total_tokens):
            return _VideoProviderResponse(
                json.dumps(
                    {
                        "model": "storyboard-dialogue-model",
                        "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
                        "usage": {"total_tokens": total_tokens},
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )

        invalid_plan = _build_agent_production_plan(6)
        invalid_plan["dialogue_units"][0]["text"] = (
            "主角必须赶在列车离站前把密封信件送到钟楼下等待的人手中。"
        )
        invalid_plan["dialogue_units"][0]["subtitle_text"] = invalid_plan["dialogue_units"][0]["text"]
        dialogue_repaired_plan = _build_agent_production_plan(6)
        scenes = _enrich_agent_scenes(
            [
                {
                    "title": f"台词精编镜头 {index}",
                    "visual_prompt": f"主角在雨夜旧城完成第 {index} 个连续动作，主体、光线和构图清晰。",
                    "narration_text": f"第{index}步，继续前进。",
                    "subtitle_text": f"第{index}步，继续前进。",
                    "duration_seconds": 10,
                    "camera_direction": "跟拍",
                    "mood": "紧迫",
                }
                for index in range(1, 7)
            ]
        )
        mocked_urlopen.side_effect = [
            provider_response(invalid_plan, 100),
            provider_response(_build_dialogue_repair_payload(dialogue_repaired_plan, "line_01"), 60),
            provider_response({"summary": "台词精编后的完整分镜", "scenes": scenes}, 200),
        ]
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Dialogue budget repair",
            title="Dialogue budget repair",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 6},
            format="json",
        )

        self.assert_success_envelope(response)
        workflow = response.data["data"]["agent_workflow"]
        self.assertEqual(
            [stage["id"] for stage in workflow["stages"]],
            [
                "story_architect",
                "dialogue_repair",
                "schema_guard",
                "visual_modeler",
                "shot_director",
                "visual_sequence_planner",
                "prompt_adapter",
                "quality_supervisor",
            ],
        )
        self.assertFalse(workflow["repair_report"]["provider_schema_repair_applied"])
        self.assertTrue(workflow["repair_report"]["provider_dialogue_repair_applied"])
        self.assertEqual(workflow["repair_report"]["provider_dialogue_repair_call_count"], 1)
        self.assertEqual(workflow["quality_report"]["metrics"]["provider_call_count"], 3)
        self.assertEqual(workflow["production_plan"]["characters"], invalid_plan["characters"])
        self.assertEqual(workflow["production_plan"]["beats"], invalid_plan["beats"])
        self.assertEqual(
            workflow["production_plan"]["dialogue_units"][0]["text"],
            dialogue_repaired_plan["dialogue_units"][0]["text"],
        )
        self.assertEqual(mocked_urlopen.call_count, 3)
        self.assertEqual(
            [call.kwargs["timeout"] for call in mocked_urlopen.call_args_list],
            [120, 120, 150],
        )
        dialogue_request = mocked_urlopen.call_args_list[1].args[0]
        dialogue_payload = json.loads(dialogue_request.data.decode("utf-8"))
        self.assertEqual(dialogue_payload["temperature"], 0.1)
        self.assertIn("每个 beat 建议最多 20 个字符", dialogue_payload["messages"][1]["content"])
        self.assertIn('"hard_max_text_characters": 25', dialogue_payload["messages"][1]["content"])
        self.assertNotIn("server-test-key", json.dumps(dialogue_payload, ensure_ascii=False))

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-repair-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=120,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=150,
        VIDEO_AI_THINKING_TYPE="disabled",
    )
    @patch("video_generation.providers.urlopen")
    def test_ai_storyboard_stops_after_one_invalid_schema_repair(self, mocked_urlopen):
        invalid_plan_content = json.dumps(_build_agent_production_plan(5), ensure_ascii=False)
        invalid_response = _VideoProviderResponse(
            json.dumps(
                {
                    "model": "storyboard-repair-model",
                    "choices": [{"message": {"content": invalid_plan_content}}],
                    "usage": {"total_tokens": 100},
                },
                ensure_ascii=False,
            ).encode("utf-8")
        )
        mocked_urlopen.side_effect = [invalid_response, invalid_response]
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Rejected schema repair",
            title="Rejected schema repair",
            input_text="A courier follows a signal through the sleeping city before the last train leaves. " * 9,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.DRAFT,
        )
        self.client.force_authenticate(user=self.reader)

        response = self.client.post(
            f"/api/video-projects/{project.id}/storyboard/ai/",
            {"scene_count": 6},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(mocked_urlopen.call_count, 2)
        self.assertEqual(
            [call.kwargs["timeout"] for call in mocked_urlopen.call_args_list],
            [120, 120],
        )
        project.refresh_from_db()
        self.assertEqual(project.status, VideoProject.Status.FAILED)
        self.assertIn("6 个连续节拍", project.failure_reason)

    @override_settings(
        VIDEO_AI_API_URL="https://api.example.com/v1/chat/completions",
        VIDEO_AI_API_KEY="server-test-key",
        VIDEO_AI_MODEL="storyboard-job-model",
        VIDEO_AI_TIMEOUT_SECONDS=10,
        VIDEO_AI_PLANNING_TIMEOUT_SECONDS=11,
        VIDEO_AI_DIRECTING_TIMEOUT_SECONDS=12,
        VIDEO_AI_THINKING_TYPE="",
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

        scenes = _enrich_agent_scenes([
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
        ])
        valid_plan = json.dumps(_build_agent_production_plan(6), ensure_ascii=False)
        valid_content = json.dumps({"summary": "Durable job summary", "scenes": scenes}, ensure_ascii=False)
        mocked_urlopen.side_effect = [
            FakeResponse(valid_plan),
            FakeResponse(valid_content),
            TimeoutError(),
            FakeResponse(valid_plan),
            FakeResponse(valid_content),
        ]

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
        self.assertEqual(project.agent_workflow["mode"], "multi_agent")
        first_provider_payload = json.loads(mocked_urlopen.call_args_list[0].args[0].data.decode("utf-8"))
        self.assertNotIn("thinking", first_provider_payload)
        self.assertEqual(mocked_urlopen.call_args_list[0].kwargs["timeout"], 11)
        self.assertEqual(mocked_urlopen.call_args_list[1].kwargs["timeout"], 12)
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
        self.assertIn("11 秒", retry_project.failure_reason)

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

    @override_settings(
        VIDEO_IMAGE_API_KEY="",
        VIDEO_CLIP_API_KEY="",
        VIDEO_TTS_API_KEY="",
    )
    def test_video_asset_jobs_require_server_configuration(self):
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Unconfigured assets",
            title="Unconfigured assets",
            input_text="A quiet station waits for the last train. " * 20,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Station",
            visual_prompt="A vertical cinematic station at night.",
            narration_text="最后一班车即将到站。",
            duration_seconds=60,
            status=VideoScene.Status.READY,
        )
        self.client.force_authenticate(user=self.reader)

        capabilities_response = self.client.get("/api/video-projects/capabilities/")
        self.assert_success_envelope(capabilities_response)
        self.assertFalse(capabilities_response.data["data"]["image_assets_configured"])
        self.assertFalse(capabilities_response.data["data"]["video_clips_configured"])
        self.assertFalse(capabilities_response.data["data"]["narration_audio_configured"])

        image_response = self.client.post(
            f"/api/video-projects/{project.id}/assets/images/jobs/",
            {},
            format="json",
        )
        audio_response = self.client.post(
            f"/api/video-projects/{project.id}/assets/audio/jobs/",
            {},
            format="json",
        )
        video_response = self.client.post(
            f"/api/video-projects/{project.id}/assets/videos/jobs/",
            {},
            format="json",
        )
        self.assertEqual(image_response.status_code, 400)
        self.assertEqual(video_response.status_code, 400)
        self.assertEqual(audio_response.status_code, 400)
        self.assertEqual(VideoGenerationJob.objects.filter(project=project).count(), 0)

    def test_wav_audio_quality_accepts_audible_signal_and_rejects_silence(self):
        passed_report = analyze_wav_audio(_build_test_wav(), target_duration_seconds=2)
        self.assertEqual(passed_report["status"], "passed")
        self.assertEqual(passed_report["metrics"]["sample_rate"], 24000)
        self.assertLess(passed_report["metrics"]["rms_dbfs"], 0)

        failed_report = analyze_wav_audio(
            _build_test_wav(amplitude=0),
            target_duration_seconds=2,
        )
        self.assertEqual(failed_report["status"], "failed")
        issue_codes = {issue["code"] for issue in failed_report["issues"]}
        self.assertIn("audio_too_quiet", issue_codes)
        self.assertIn("excessive_silence", issue_codes)

        speech_report = build_speech_quality_report(
            "快递员冲进雨夜。",
            "完全不同的内容",
            "glm-asr-2512",
            0.75,
        )
        self.assertEqual(speech_report["status"], "needs_review")
        self.assertLess(speech_report["similarity"], 0.75)

    @override_settings(
        VIDEO_IMAGE_API_URL="https://api.example.com/images/generations",
        VIDEO_IMAGE_API_KEY="image-test-key",
        VIDEO_IMAGE_MODEL="glm-image-test",
        VIDEO_IMAGE_SIZE="960x1728",
        VIDEO_IMAGE_TIMEOUT_SECONDS=10,
        VIDEO_IMAGE_DAILY_JOB_LIMIT=1,
        VIDEO_VISUAL_REGENERATION_DAILY_SCENE_LIMIT=2,
        VIDEO_VISUAL_REGENERATION_PER_SCENE_LIMIT=1,
        VIDEO_TTS_API_URL="https://api.example.com/audio/speech",
        VIDEO_TTS_API_KEY="tts-test-key",
        VIDEO_TTS_MODEL="glm-tts-test",
        VIDEO_TTS_VOICE="tongtong",
        VIDEO_TTS_SPEED=1.0,
        VIDEO_TTS_VOLUME=1.0,
        VIDEO_TTS_TIMEOUT_SECONDS=10,
        VIDEO_TTS_DAILY_JOB_LIMIT=1,
        VIDEO_ASSET_MAX_FILE_BYTES=1024 * 1024,
        VIDEO_JOB_MAX_ATTEMPTS=3,
        VIDEO_JOB_STALE_SECONDS=60,
    )
    @patch("video_generation.providers.urlopen")
    def test_video_asset_jobs_generate_files_permissions_quota_and_recovery(self, mocked_urlopen):
        image_payloads = []
        audio_payloads = []
        image_content = b"\x89PNG\r\n\x1a\n" + b"generated-image" * 8
        audio_content = _build_test_wav()
        image_result_url = "https://media.example.com/generated-scene.png"

        def fake_urlopen(request, timeout):
            if request.full_url == "https://api.example.com/images/generations":
                image_payloads.append(json.loads(request.data.decode("utf-8")))
                body = json.dumps(
                    {
                        "data": [{"url": image_result_url}],
                        "content_filter": [{"level": 0}],
                    }
                ).encode("utf-8")
                return _VideoProviderResponse(body, url=request.full_url)
            if request.full_url == image_result_url:
                return _VideoProviderResponse(image_content, "image/png", image_result_url)
            if request.full_url == "https://api.example.com/audio/speech":
                audio_payloads.append(json.loads(request.data.decode("utf-8")))
                return _VideoProviderResponse(audio_content, "audio/wav", request.full_url)
            raise AssertionError(f"Unexpected provider URL: {request.full_url}")

        mocked_urlopen.side_effect = fake_urlopen
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Provider assets",
            title="Provider assets",
            input_text="A courier follows a light through the sleeping city. " * 20,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        scenes = [
            VideoScene.objects.create(
                project=project,
                scene_no=scene_no,
                title=f"Scene {scene_no}",
                visual_prompt=("vertical cinematic source detail " * 60) + str(scene_no),
                narration_text=("旁白内容" * 300) + str(scene_no),
                subtitle_text=f"字幕 {scene_no}",
                duration_seconds=30,
                status=VideoScene.Status.READY,
            )
            for scene_no in (1, 2)
        ]
        scenes[0].agent_metadata = {
            "prompt_adapter": {
                "version": "2.2",
                "strategy": "canonical_assets_plus_shot_delta",
                "anchor_fingerprint": "anchor-test-001",
                "image_prompt": "统一角色形象与雨夜场景的结构化关键帧提示词",
            },
            "visual_plan": {
                "continuity_group_id": "sequence_01",
                "relationship_to_previous": "opening",
                "inherits_from_scene_no": None,
            },
            "audio_script": {
                "text": "结构化旁白清楚推进剧情。",
                "speaker_id": "narrator",
                "emotion": "克制",
                "voice_profile_id": "voice_narrator",
                "target_duration_ms": 3000,
            },
        }
        scenes[0].save(update_fields=["agent_metadata", "updated_at"])

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            image_job_url = f"/api/video-projects/{project.id}/assets/images/jobs/"
            audio_job_url = f"/api/video-projects/{project.id}/assets/audio/jobs/"
            self.client.force_authenticate(user=None)
            self.assertEqual(self.client.post(image_job_url, {}, format="json").status_code, 401)

            self.client.force_authenticate(user=self.reader)
            capabilities_response = self.client.get("/api/video-projects/capabilities/")
            self.assert_success_envelope(capabilities_response)
            capabilities = capabilities_response.data["data"]
            self.assertTrue(capabilities["image_assets_configured"])
            self.assertTrue(capabilities["narration_audio_configured"])
            self.assertTrue(capabilities["image_assets_continuity_workflow"])
            self.assertEqual(
                capabilities["image_assets_reference_mode"],
                "text_only_canonical_anchors",
            )
            self.assertEqual(
                capabilities["image_assets_visual_review_mode"],
                "manual_required",
            )
            self.assertEqual(capabilities["image_assets_daily_jobs_remaining"], 1)
            self.assertEqual(capabilities["narration_audio_daily_jobs_remaining"], 1)
            self.assertTrue(capabilities["visual_review_available"])
            self.assertEqual(capabilities["visual_regeneration_daily_scene_limit"], 2)
            self.assertEqual(capabilities["visual_regeneration_daily_scenes_remaining"], 2)
            self.assertEqual(capabilities["visual_regeneration_per_scene_limit"], 1)

            image_create_response = self.client.post(image_job_url, {}, format="json")
            self.assert_success_envelope(image_create_response)
            image_job_id = image_create_response.data["data"]["id"]
            self.assertEqual(image_create_response.data["data"]["job_type"], VideoGenerationJob.JobType.IMAGE_ASSETS)
            self.assertEqual(
                VideoAsset.objects.filter(project=project, asset_type=VideoAsset.AssetType.IMAGE, status=VideoAsset.Status.QUEUED).count(),
                2,
            )
            self.assertEqual(self.client.post(image_job_url, {}, format="json").status_code, 400)
            self.assertEqual(
                self.client.patch(
                    f"/api/video-projects/{project.id}/scenes/{scenes[0].id}/",
                    {"visual_prompt": "Changed during active job"},
                    format="json",
                ).status_code,
                400,
            )
            self.assertEqual(
                self.client.post(f"/api/video-projects/{project.id}/storyboard/", {"scene_count": 4}, format="json").status_code,
                400,
            )

            User = get_user_model()
            other_reader = User.objects.create_user(
                username="other_reader_asset_jobs",
                password="password12345Strong!",
                role="reader",
            )
            self.client.force_authenticate(user=other_reader)
            self.assertEqual(self.client.get(image_job_url).status_code, 404)
            self.assertEqual(self.client.get(f"/api/video-generation-jobs/{image_job_id}/").status_code, 404)

            self.client.force_authenticate(user=self.reader)
            completed_image_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(
                completed_image_job.status,
                VideoGenerationJob.Status.SUCCEEDED,
                completed_image_job.error_message,
            )
            self.assertEqual(len(image_payloads), 2)
            self.assertTrue(all(len(payload["prompt"]) <= 1000 for payload in image_payloads))
            self.assertTrue(all(payload["size"] == "960x1728" for payload in image_payloads))
            self.assertEqual(image_payloads[0]["prompt"], "统一角色形象与雨夜场景的结构化关键帧提示词")

            image_latest_response = self.client.get(image_job_url)
            self.assert_success_envelope(image_latest_response)
            self.assertEqual(image_latest_response.data["data"]["id"], image_job_id)

            audio_create_response = self.client.post(audio_job_url, {}, format="json")
            self.assert_success_envelope(audio_create_response)
            completed_audio_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(completed_audio_job.status, VideoGenerationJob.Status.SUCCEEDED)
            self.assertEqual(len(audio_payloads), 2)
            self.assertTrue(all(len(payload["input"]) <= 1024 for payload in audio_payloads))
            self.assertTrue(all(payload["voice"] == "tongtong" for payload in audio_payloads))
            self.assertTrue(all(payload["response_format"] == "wav" for payload in audio_payloads))
            self.assertEqual(audio_payloads[0]["input"], "结构化旁白清楚推进剧情。")

            assets = list(VideoAsset.objects.filter(project=project).order_by("asset_type", "scene_id"))
            self.assertEqual(len(assets), 4)
            self.assertTrue(all(asset.status == VideoAsset.Status.READY for asset in assets))
            self.assertTrue(all((Path(media_root) / asset.storage_path).is_file() for asset in assets))
            self.assertTrue(all(asset.metadata.get("generation_job_id") for asset in assets))
            self.assertTrue(all("visual_prompt" not in asset.metadata for asset in assets))
            audio_asset = next(asset for asset in assets if asset.asset_type == VideoAsset.AssetType.AUDIO)
            image_assets = [asset for asset in assets if asset.asset_type == VideoAsset.AssetType.IMAGE]
            image_asset = image_assets[0]
            rejected_image_asset = image_assets[1]
            self.assertEqual(audio_asset.metadata["sample_rate"], 24000)
            self.assertGreater(audio_asset.metadata["duration_seconds"], 0)
            self.assertEqual(audio_asset.metadata["audio_quality"]["status"], "passed")
            self.assertEqual(audio_asset.metadata["audio_quality"]["version"], "1.0")
            self.assertEqual(audio_asset.metadata["speech_quality"]["status"], "needs_review")
            self.assertEqual(audio_asset.metadata["speech_quality"]["source"], "manual")
            self.assertEqual(audio_asset.metadata["script_source"], "agent_workflow")
            self.assertEqual(audio_asset.metadata["speaker_id"], "narrator")
            self.assertEqual(
                image_asset.metadata["prompt_strategy"],
                "canonical_assets_plus_shot_delta",
            )
            self.assertEqual(image_asset.metadata["prompt_adapter_version"], "2.2")
            self.assertEqual(image_asset.metadata["anchor_fingerprint"], "anchor-test-001")
            self.assertEqual(image_asset.metadata["continuity_group_id"], "sequence_01")
            self.assertEqual(image_asset.metadata["relationship_to_previous"], "opening")
            self.assertEqual(image_asset.metadata["reference_mode"], "text_only_canonical_anchors")
            self.assertEqual(image_asset.metadata["visual_review"]["status"], "pending")
            self.assertEqual(image_asset.metadata["visual_review"]["mode"], "manual_required")
            self.assertNotIn("prompt", image_asset.metadata)

            approve_visual_response = self.client.patch(
                f"/api/video-assets/{image_asset.id}/visual-review/",
                {"decision": "approved"},
                format="json",
            )
            self.assert_success_envelope(approve_visual_response)
            self.assertEqual(
                approve_visual_response.data["data"]["metadata"]["visual_review"]["status"],
                "passed",
            )
            missing_issue_response = self.client.patch(
                f"/api/video-assets/{rejected_image_asset.id}/visual-review/",
                {"decision": "rejected"},
                format="json",
            )
            self.assertEqual(missing_issue_response.status_code, 400)
            reject_visual_response = self.client.patch(
                f"/api/video-assets/{rejected_image_asset.id}/visual-review/",
                {
                    "decision": "rejected",
                    "issue_codes": ["identity_drift", "continuity_break"],
                    "note": "人物与上一镜不一致。",
                },
                format="json",
            )
            self.assert_success_envelope(reject_visual_response)
            self.assertEqual(
                reject_visual_response.data["data"]["metadata"]["visual_review"]["status"],
                "rejected",
            )
            self.assertEqual(
                reject_visual_response.data["data"]["metadata"]["visual_review"]["issue_codes"],
                ["identity_drift", "continuity_break"],
            )
            not_rejected_scene_response = self.client.post(
                image_job_url,
                {
                    "regenerate": True,
                    "scene_ids": [scenes[0].id],
                },
                format="json",
            )
            self.assertEqual(not_rejected_scene_response.status_code, 400)
            self.assertIn("必须先", str(not_rejected_scene_response.data))
            self.assertEqual(
                self.client.patch(
                    f"/api/video-assets/{audio_asset.id}/visual-review/",
                    {"decision": "approved"},
                    format="json",
                ).status_code,
                400,
            )

            self.client.force_authenticate(user=other_reader)
            self.assertEqual(
                self.client.patch(
                    f"/api/video-assets/{image_asset.id}/visual-review/",
                    {"decision": "approved"},
                    format="json",
                ).status_code,
                404,
            )
            self.client.force_authenticate(user=self.reader)

            targeted_response = self.client.post(
                image_job_url,
                {
                    "regenerate": True,
                    "scene_ids": [scenes[1].id],
                },
                format="json",
            )
            self.assert_success_envelope(targeted_response)
            targeted_job_id = targeted_response.data["data"]["id"]
            self.assertEqual(
                targeted_response.data["data"]["request_payload"]["scene_ids"],
                [scenes[1].id],
            )
            targeted_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(targeted_job.id, targeted_job_id)
            self.assertEqual(targeted_job.status, VideoGenerationJob.Status.SUCCEEDED)
            self.assertEqual(len(image_payloads), 3)

            image_asset.refresh_from_db()
            rejected_image_asset.refresh_from_db()
            self.assertEqual(image_asset.metadata["visual_review"]["status"], "passed")
            self.assertEqual(rejected_image_asset.metadata["visual_review"]["status"], "pending")
            self.assertEqual(
                rejected_image_asset.metadata["generation_job_id"],
                targeted_job_id,
            )
            second_reject_response = self.client.patch(
                f"/api/video-assets/{rejected_image_asset.id}/visual-review/",
                {
                    "decision": "rejected",
                    "issue_codes": ["identity_drift"],
                },
                format="json",
            )
            self.assert_success_envelope(second_reject_response)
            exhausted_scene_response = self.client.post(
                image_job_url,
                {
                    "regenerate": True,
                    "scene_ids": [scenes[1].id],
                },
                format="json",
            )
            self.assertEqual(exhausted_scene_response.status_code, 400)
            self.assertIn("单镜重拍上限", str(exhausted_scene_response.data))

            detail_response = self.client.get(f"/api/video-projects/{project.id}/")
            self.assert_success_envelope(detail_response)
            self.assertEqual(len(detail_response.data["data"]["assets"]), 4)
            self.assertNotIn("storage_path", detail_response.data["data"]["assets"][0])

            image_download = self.client.get(f"/api/video-assets/{image_asset.id}/download/")
            audio_download = self.client.get(f"/api/video-assets/{audio_asset.id}/download/")
            self.assertEqual(b"".join(image_download.streaming_content), image_content)
            self.assertEqual(b"".join(audio_download.streaming_content), audio_content)

            capabilities_after = self.client.get("/api/video-projects/capabilities/").data["data"]
            self.assertEqual(capabilities_after["image_assets_daily_jobs_remaining"], 0)
            self.assertEqual(capabilities_after["narration_audio_daily_jobs_remaining"], 0)
            self.assertEqual(capabilities_after["visual_regeneration_daily_scenes_remaining"], 1)

            quota_project = VideoProject.objects.create(
                owner=self.reader,
                source_type=VideoProject.SourceType.TEXT,
                title="Quota project",
                input_text="Quota source text " * 40,
                duration_target=60,
                status=VideoProject.Status.STORYBOARD_READY,
            )
            VideoScene.objects.create(
                project=quota_project,
                scene_no=1,
                title="Quota scene",
                visual_prompt="Quota image",
                narration_text="Quota audio",
                duration_seconds=60,
                status=VideoScene.Status.READY,
            )
            quota_response = self.client.post(
                f"/api/video-projects/{quota_project.id}/assets/images/jobs/",
                {},
                format="json",
            )
            self.assertEqual(quota_response.status_code, 400)

            stale_project = VideoProject.objects.create(
                owner=self.reader,
                source_type=VideoProject.SourceType.TEXT,
                title="Stale asset project",
                input_text="Stale source " * 40,
                duration_target=60,
                status=VideoProject.Status.STORYBOARD_READY,
            )
            stale_scene = VideoScene.objects.create(
                project=stale_project,
                scene_no=1,
                title="Stale scene",
                visual_prompt="Stale image",
                duration_seconds=60,
                status=VideoScene.Status.READY,
            )
            stale_asset = VideoAsset.objects.create(
                project=stale_project,
                scene=stale_scene,
                asset_type=VideoAsset.AssetType.IMAGE,
                status=VideoAsset.Status.RUNNING,
            )
            stale_job = VideoGenerationJob.objects.create(
                project=stale_project,
                requested_by=self.reader,
                job_type=VideoGenerationJob.JobType.IMAGE_ASSETS,
                status=VideoGenerationJob.Status.RUNNING,
                attempt_count=1,
                max_attempts=3,
                started_at=timezone.now() - timedelta(minutes=2),
            )
            self.assertEqual(recover_stale_video_generation_jobs(), 1)
            stale_job.refresh_from_db()
            stale_asset.refresh_from_db()
            stale_project.refresh_from_db()
            self.assertEqual(stale_job.status, VideoGenerationJob.Status.QUEUED)
            self.assertEqual(stale_asset.status, VideoAsset.Status.QUEUED)
            self.assertEqual(stale_project.status, VideoProject.Status.STORYBOARD_READY)

            audit_reasons = AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project.id,
            ).values_list("reason", flat=True)
            self.assertFalse(any("vertical cinematic source detail" in reason for reason in audit_reasons))
            self.assertFalse(any("旁白内容" in reason for reason in audit_reasons))

    @override_settings(
        VIDEO_TTS_API_URL="https://api.example.com/audio/speech",
        VIDEO_TTS_API_KEY="tts-test-key",
        VIDEO_TTS_MODEL="glm-tts-test",
        VIDEO_TTS_VOICE="tongtong",
        VIDEO_TTS_SPEED=1.0,
        VIDEO_TTS_VOLUME=1.0,
        VIDEO_TTS_TIMEOUT_SECONDS=10,
        VIDEO_TTS_DAILY_JOB_LIMIT=2,
        VIDEO_ASR_ENABLED=False,
        VIDEO_ASSET_MAX_FILE_BYTES=1024 * 1024,
        VIDEO_JOB_MAX_ATTEMPTS=3,
    )
    @patch("video_generation.providers.urlopen")
    def test_silent_agent_scene_skips_tts_and_subtitle_block(self, mocked_urlopen):
        audio_content = _build_test_wav()
        provider_payloads = []

        def fake_urlopen(request, timeout):
            provider_payloads.append(json.loads(request.data.decode("utf-8")))
            return _VideoProviderResponse(audio_content, "audio/wav", request.full_url)

        mocked_urlopen.side_effect = fake_urlopen
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="Silent transition project",
            input_text="Silent transition source " * 40,
            duration_target=30,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        silent_scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Silent visual bridge",
            narration_text="",
            subtitle_text="",
            duration_seconds=5,
            agent_metadata={"audio_script": {"text": "", "subtitle_text": ""}},
            status=VideoScene.Status.READY,
        )
        voiced_scene = VideoScene.objects.create(
            project=project,
            scene_no=2,
            title="Narrated continuation",
            narration_text="继续前行。",
            subtitle_text="继续前行。",
            duration_seconds=5,
            agent_metadata={
                "audio_script": {
                    "text": "继续前行。",
                    "subtitle_text": "继续前行。",
                    "speaker_id": "narrator",
                    "voice_profile_id": "voice_narrator",
                    "target_duration_ms": 2000,
                }
            },
            status=VideoScene.Status.READY,
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            self.client.force_authenticate(user=self.reader)
            audio_response = self.client.post(
                f"/api/video-projects/{project.id}/assets/audio/jobs/",
                {},
                format="json",
            )
            self.assert_success_envelope(audio_response)
            self.assertFalse(
                VideoAsset.objects.filter(
                    project=project,
                    scene=silent_scene,
                    asset_type=VideoAsset.AssetType.AUDIO,
                ).exists()
            )
            self.assertTrue(
                VideoAsset.objects.filter(
                    project=project,
                    scene=voiced_scene,
                    asset_type=VideoAsset.AssetType.AUDIO,
                    status=VideoAsset.Status.QUEUED,
                ).exists()
            )

            completed_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(completed_job.status, VideoGenerationJob.Status.SUCCEEDED, completed_job.error_message)
            self.assertEqual(len(provider_payloads), 1)
            self.assertEqual(provider_payloads[0]["input"], "继续前行。")

            subtitle_response = self.client.post(
                f"/api/video-projects/{project.id}/assets/subtitles/",
                {},
                format="json",
            )
            self.assert_success_envelope(subtitle_response)
            subtitle_asset = VideoAsset.objects.get(
                project=project,
                scene__isnull=True,
                asset_type=VideoAsset.AssetType.SUBTITLE,
            )
            subtitle_content = (Path(media_root) / subtitle_asset.storage_path).read_text(encoding="utf-8")
            self.assertNotIn("Silent visual bridge", subtitle_content)
            self.assertIn("00:00:05,000 --> 00:00:10,000", subtitle_content)
            self.assertIn("继续前行。", subtitle_content)

    @override_settings(
        VIDEO_TTS_API_URL="https://api.example.com/audio/speech",
        VIDEO_TTS_API_KEY="tts-test-key",
        VIDEO_TTS_MODEL="glm-tts-test",
        VIDEO_TTS_VOICE="tongtong",
        VIDEO_TTS_SPEED=1.0,
        VIDEO_TTS_VOLUME=1.0,
        VIDEO_TTS_TIMEOUT_SECONDS=10,
        VIDEO_TTS_DAILY_JOB_LIMIT=2,
        VIDEO_ASR_ENABLED=True,
        VIDEO_ASR_API_URL="https://api.example.com/audio/transcriptions",
        VIDEO_ASR_API_KEY="asr-test-key",
        VIDEO_ASR_MODEL="glm-asr-2512",
        VIDEO_ASR_TIMEOUT_SECONDS=10,
        VIDEO_ASR_MIN_SIMILARITY=0.75,
        VIDEO_ASSET_MAX_FILE_BYTES=1024 * 1024,
        VIDEO_JOB_MAX_ATTEMPTS=3,
    )
    @patch("video_generation.providers.urlopen")
    def test_narration_asr_quality_and_manual_review(self, mocked_urlopen):
        audio_content = _build_test_wav()
        provider_requests = []

        def fake_urlopen(request, timeout):
            provider_requests.append(request)
            if request.full_url == "https://api.example.com/audio/speech":
                return _VideoProviderResponse(audio_content, "audio/wav", request.full_url)
            if request.full_url == "https://api.example.com/audio/transcriptions":
                content_type = request.get_header("Content-type") or ""
                self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
                self.assertIn(b'name="model"', request.data)
                self.assertIn(b"glm-asr-2512", request.data)
                self.assertIn(b'filename="narration.wav"', request.data)
                self.assertIn(audio_content, request.data)
                response_body = json.dumps(
                    {
                        "id": "asr-result-1",
                        "model": "glm-asr-2512",
                        "text": "快递员冲进雨夜",
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                return _VideoProviderResponse(response_body, "application/json", request.full_url)
            raise AssertionError(f"Unexpected provider URL: {request.full_url}")

        mocked_urlopen.side_effect = fake_urlopen
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="ASR narration project",
            input_text="ASR narration source " * 40,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Rainy delivery",
            narration_text="快递员冲进雨夜。",
            duration_seconds=60,
            status=VideoScene.Status.READY,
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            self.client.force_authenticate(user=self.reader)
            capabilities = self.client.get("/api/video-projects/capabilities/").data["data"]
            self.assertTrue(capabilities["narration_audio_asr_configured"])
            self.assertEqual(capabilities["narration_audio_asr_model"], "glm-asr-2512")
            self.assertTrue(capabilities["narration_audio_manual_review"])

            job_response = self.client.post(
                f"/api/video-projects/{project.id}/assets/audio/jobs/",
                {},
                format="json",
            )
            self.assert_success_envelope(job_response)
            completed_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(completed_job.status, VideoGenerationJob.Status.SUCCEEDED, completed_job.error_message)
            self.assertEqual(len(provider_requests), 2)

            asset = VideoAsset.objects.get(
                project=project,
                scene=scene,
                asset_type=VideoAsset.AssetType.AUDIO,
            )
            speech_quality = asset.metadata["speech_quality"]
            self.assertEqual(speech_quality["status"], "passed")
            self.assertEqual(speech_quality["source"], "glm_asr")
            self.assertEqual(speech_quality["transcript"], "快递员冲进雨夜")
            self.assertEqual(speech_quality["similarity"], 1.0)
            self.assertEqual(speech_quality["provider_asset_id"], "asr-result-1")

            review_url = f"/api/video-assets/{asset.id}/audio-review/"
            self.client.force_authenticate(user=self.author)
            self.assertEqual(
                self.client.patch(review_url, {"decision": "approved"}, format="json").status_code,
                404,
            )

            self.client.force_authenticate(user=self.reader)
            self.assertEqual(
                self.client.patch(review_url, {"decision": "unknown"}, format="json").status_code,
                400,
            )
            rejected_response = self.client.patch(
                review_url,
                {"decision": "rejected"},
                format="json",
            )
            self.assert_success_envelope(rejected_response)
            self.assertEqual(rejected_response.data["data"]["metadata"]["audio_review"]["status"], "rejected")

            approved_response = self.client.patch(
                review_url,
                {"decision": "approved"},
                format="json",
            )
            self.assert_success_envelope(approved_response)
            self.assertEqual(approved_response.data["data"]["metadata"]["audio_review"]["status"], "approved")
            asset.refresh_from_db()
            self.assertEqual(asset.metadata["audio_review"]["reviewer_id"], self.reader.id)
            audit_reasons = AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project.id,
            ).values_list("reason", flat=True)
            self.assertTrue(any("audio_manual_review" in reason for reason in audit_reasons))

            image_asset = VideoAsset.objects.create(
                project=project,
                scene=scene,
                asset_type=VideoAsset.AssetType.IMAGE,
                status=VideoAsset.Status.READY,
            )
            self.assertEqual(
                self.client.patch(
                    f"/api/video-assets/{image_asset.id}/audio-review/",
                    {"decision": "approved"},
                    format="json",
                ).status_code,
                400,
            )

    @override_settings(
        VIDEO_CLIP_API_URL="https://api.example.com/videos/generations",
        VIDEO_CLIP_RESULT_API_URL="https://api.example.com/async-result/{task_id}",
        VIDEO_CLIP_API_KEY="video-test-key",
        VIDEO_CLIP_MODEL="cogvideox-flash",
        VIDEO_CLIP_SIZE="1080x1920",
        VIDEO_CLIP_DURATION_SECONDS=5,
        VIDEO_CLIP_FPS=30,
        VIDEO_CLIP_WITH_AUDIO=True,
        VIDEO_CLIP_USE_SCENE_IMAGE=True,
        VIDEO_CLIP_USE_PREVIOUS_TAIL_FRAME=True,
        VIDEO_CLIP_REFERENCE_IMAGE_MAX_FILE_BYTES=5 * 1024 * 1024,
        VIDEO_CLIP_TAIL_FRAME_TIMEOUT_SECONDS=10,
        VIDEO_CLIP_REQUEST_TIMEOUT_SECONDS=10,
        VIDEO_CLIP_POLL_INTERVAL_SECONDS=1,
        VIDEO_CLIP_MAX_WAIT_SECONDS=30,
        VIDEO_CLIP_MAX_FILE_BYTES=1024 * 1024,
        VIDEO_CLIP_DAILY_JOB_LIMIT=1,
        VIDEO_JOB_MAX_ATTEMPTS=3,
    )
    @patch("video_generation.services.extract_video_tail_frame")
    @patch("video_generation.providers.time.sleep")
    @patch("video_generation.providers.urlopen")
    def test_video_clip_assets_use_cogvideox_flash_async_flow(
        self,
        mocked_urlopen,
        mocked_sleep,
        mocked_extract_video_tail_frame,
    ):
        provider_payloads = []
        task_id = "video-task-1"
        result_url = f"https://api.example.com/async-result/{task_id}"
        result_query_calls = 0
        video_url = "https://media.example.com/generated-scene.mp4"
        video_content = b"\x00\x00\x00\x18ftypmp42" + b"generated-video" * 8
        reference_image_content = b"\x89PNG\r\n\x1a\n" + b"reference-frame" * 8
        tail_frame_content = b"\xff\xd8\xff\xe0" + b"tail-frame" * 16
        mocked_extract_video_tail_frame.return_value = {
            "content": tail_frame_content,
            "mime_type": "image/jpeg",
            "extension": ".jpg",
            "file_size": len(tail_frame_content),
            "sha256": "tail-frame-sha256",
        }

        def fake_urlopen(request, timeout):
            nonlocal result_query_calls
            if request.full_url == "https://api.example.com/videos/generations":
                provider_payloads.append(json.loads(request.data.decode("utf-8")))
                body = json.dumps(
                    {
                        "id": task_id,
                        "model": "cogvideox-flash",
                        "task_status": "PROCESSING",
                    }
                ).encode("utf-8")
                return _VideoProviderResponse(body, url=request.full_url)
            if request.full_url == result_url:
                result_query_calls += 1
                if result_query_calls == 1:
                    raise URLError(ConnectionResetError(10054, "connection reset"))
                body = json.dumps(
                    {
                        "id": task_id,
                        "model": "cogvideox-flash",
                        "task_status": "SUCCESS",
                        "video_result": [{"url": video_url, "cover_image_url": "https://media.example.com/cover.jpg"}],
                    }
                ).encode("utf-8")
                return _VideoProviderResponse(body, url=request.full_url)
            if request.full_url == video_url:
                return _VideoProviderResponse(video_content, "video/mp4", video_url)
            raise AssertionError(f"Unexpected provider URL: {request.full_url}")

        mocked_urlopen.side_effect = fake_urlopen
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="CogVideoX clip project",
            input_text="Video source text " * 40,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Moving scene",
            visual_prompt=("古代人物面色阴沉，弓弩手放箭，箭矢刺入草人。" * 20),
            narration_text="快递员冲进雨夜。",
            duration_seconds=60,
            camera_direction="Low angle tracking shot",
            mood="tense",
            status=VideoScene.Status.READY,
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            reference_storage_path = Path(
                "video_projects",
                str(project.id),
                "scenes",
                "scene-01",
                "image-reference.png",
            ).as_posix()
            reference_path = Path(media_root) / reference_storage_path
            reference_path.parent.mkdir(parents=True, exist_ok=True)
            reference_path.write_bytes(reference_image_content)
            reference_asset = VideoAsset.objects.create(
                project=project,
                scene=scene,
                asset_type=VideoAsset.AssetType.IMAGE,
                status=VideoAsset.Status.READY,
                storage_path=reference_storage_path,
                file_name="scene-01.png",
                mime_type="image/png",
                file_size=len(reference_image_content),
                provider="test",
            )
            video_job_url = f"/api/video-projects/{project.id}/assets/videos/jobs/"
            self.client.force_authenticate(user=self.reader)
            capabilities = self.client.get("/api/video-projects/capabilities/").data["data"]
            self.assertTrue(capabilities["video_clips_configured"])
            self.assertEqual(capabilities["video_clips_model"], "cogvideox-flash")
            self.assertTrue(capabilities["video_clips_with_audio"])
            self.assertTrue(capabilities["video_clips_reference_frame_enabled"])
            self.assertEqual(
                capabilities["video_clips_reference_frame_mode"],
                "previous_tail_then_scene_image_base64",
            )
            self.assertTrue(capabilities["video_clips_previous_tail_frame_enabled"])
            self.assertTrue(capabilities["video_clips_previous_tail_frame_available"])
            self.assertEqual(capabilities["video_clips_fps"], 30)
            self.assertTrue(capabilities["narration_audio_quality_gate"])
            self.assertFalse(capabilities["narration_audio_asr_configured"])
            self.assertTrue(capabilities["narration_audio_manual_review"])
            self.assertEqual(capabilities["video_clips_daily_jobs_remaining"], 1)

            create_response = self.client.post(video_job_url, {}, format="json")
            self.assert_success_envelope(create_response)
            job_id = create_response.data["data"]["id"]
            self.assertEqual(create_response.data["data"]["job_type"], VideoGenerationJob.JobType.VIDEO_CLIPS)
            self.assertTrue(
                VideoAsset.objects.filter(
                    project=project,
                    scene=scene,
                    asset_type=VideoAsset.AssetType.VIDEO,
                    status=VideoAsset.Status.QUEUED,
                ).exists()
            )

            completed_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(completed_job.status, VideoGenerationJob.Status.SUCCEEDED, completed_job.error_message)
            self.assertEqual(len(provider_payloads), 1)
            payload = provider_payloads[0]
            self.assertEqual(payload["model"], "cogvideox-flash")
            self.assertEqual(payload["size"], "1080x1920")
            self.assertNotIn("duration", payload)
            self.assertEqual(payload["fps"], 30)
            self.assertTrue(payload["with_audio"])
            self.assertTrue(payload["watermark_enabled"])
            self.assertTrue(payload["image_url"].startswith("data:image/png;base64,"))
            encoded_reference = payload["image_url"].split(",", 1)[1]
            self.assertEqual(base64.b64decode(encoded_reference), reference_image_content)
            self.assertLessEqual(len(payload["prompt"]), 512)
            self.assertIn("适合全年龄观看", payload["prompt"])
            self.assertIn("齐射", payload["prompt"])
            for blocked_term in ("阴沉", "弓弩手", "放箭", "箭矢", "刺入"):
                self.assertNotIn(blocked_term, payload["prompt"])
            self.assertEqual(mocked_sleep.call_count, 2)
            mocked_sleep.assert_called_with(1)

            asset = VideoAsset.objects.get(project=project, scene=scene, asset_type=VideoAsset.AssetType.VIDEO)
            self.assertEqual(asset.status, VideoAsset.Status.READY)
            self.assertEqual(asset.mime_type, "video/mp4")
            self.assertEqual(asset.file_name, "scene-01.mp4")
            self.assertEqual(asset.provider_asset_id, task_id)
            self.assertEqual(asset.metadata["model"], "cogvideox-flash")
            self.assertEqual(asset.metadata["poll_count"], 2)
            self.assertEqual(asset.metadata["poll_error_count"], 1)
            self.assertFalse(asset.metadata["resumed_provider_task"])
            self.assertTrue(asset.metadata["with_audio"])
            self.assertEqual(asset.metadata["visual_review"]["status"], "pending")
            self.assertEqual(asset.metadata["visual_review"]["mode"], "manual_required")
            self.assertTrue(asset.metadata["prompt_safety_adjusted"])
            self.assertTrue(asset.metadata["reference_frame_used"])
            self.assertEqual(asset.metadata["reference_frame_mode"], "scene_image_base64")
            self.assertEqual(asset.metadata["reference_frame_asset_id"], reference_asset.id)
            self.assertEqual(asset.metadata["reference_frame_source_scene_no"], 1)
            self.assertEqual(asset.metadata["reference_frame_fallback_reasons"], [])
            self.assertEqual(asset.metadata["tail_frame"]["status"], "ready")
            self.assertEqual(asset.metadata["tail_frame"]["sha256"], "tail-frame-sha256")
            self.assertNotIn("pending_provider_task", asset.metadata)
            self.assertNotIn("image_url", asset.metadata)
            completed_job.refresh_from_db()
            self.assertNotIn("provider_resume_available", completed_job.request_payload)
            self.assertEqual((Path(media_root) / asset.storage_path).read_bytes(), video_content)
            tail_frame_path = (Path(media_root) / asset.storage_path).with_name(
                f"{Path(asset.storage_path).stem}-tail.jpg"
            )
            self.assertEqual(tail_frame_path.read_bytes(), tail_frame_content)

            detail_response = self.client.get(f"/api/video-projects/{project.id}/")
            self.assert_success_envelope(detail_response)
            detail_asset_types = {item["asset_type"] for item in detail_response.data["data"]["assets"]}
            self.assertEqual(detail_asset_types, {VideoAsset.AssetType.IMAGE, VideoAsset.AssetType.VIDEO})
            download_response = self.client.get(f"/api/video-assets/{asset.id}/download/")
            self.assertEqual(b"".join(download_response.streaming_content), video_content)

            self.client.force_authenticate(user=self.author)
            self.assertEqual(self.client.get(video_job_url).status_code, 404)
            self.assertEqual(self.client.get(f"/api/video-generation-jobs/{job_id}/").status_code, 404)

            self.client.force_authenticate(user=self.reader)
            capabilities_after = self.client.get("/api/video-projects/capabilities/").data["data"]
            self.assertEqual(capabilities_after["video_clips_daily_jobs_remaining"], 0)
            update_response = self.client.patch(
                f"/api/video-projects/{project.id}/scenes/{scene.id}/",
                {"visual_prompt": "A revised vertical cinematic scene."},
                format="json",
            )
            self.assert_success_envelope(update_response)
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.STALE)

    def test_video_provider_task_id_is_resumed_only_by_the_same_job(self):
        from video_generation.services import (
            _begin_scene_asset_processing,
            _fail_scene_asset_processing,
            _record_scene_provider_task,
        )

        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="Provider task resume project",
            input_text="Provider task resume source " * 40,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Provider task resume scene",
            visual_prompt="连续跟随同一人物向前移动。",
            duration_seconds=5,
            status=VideoScene.Status.READY,
        )
        job = VideoGenerationJob.objects.create(
            project=project,
            requested_by=self.reader,
            job_type=VideoGenerationJob.JobType.VIDEO_CLIPS,
            status=VideoGenerationJob.Status.RUNNING,
            provider="glm",
            model_name="cogvideox-flash",
            request_payload={"asset_type": VideoAsset.AssetType.VIDEO, "regenerate": False},
            max_attempts=3,
        )
        asset = VideoAsset.objects.create(
            project=project,
            scene=scene,
            asset_type=VideoAsset.AssetType.VIDEO,
            status=VideoAsset.Status.QUEUED,
            provider="glm",
        )

        processing = _begin_scene_asset_processing(job, scene, VideoAsset.AssetType.VIDEO)
        self.assertEqual(processing["resume_provider_task_id"], "")
        _record_scene_provider_task(asset.id, job, "provider-task-resume-1", "cogvideox-flash")
        _fail_scene_asset_processing(asset.id, job, "结果查询网络中断。", False)

        asset.refresh_from_db()
        self.assertEqual(asset.status, VideoAsset.Status.FAILED)
        self.assertEqual(
            asset.metadata["pending_provider_task"]["task_id"],
            "provider-task-resume-1",
        )
        job.status = VideoGenerationJob.Status.FAILED
        job.attempt_count = job.max_attempts
        job.error_message = "短视频画面生成任务等待超时，请稍后重试。"
        job.save(update_fields=["status", "attempt_count", "error_message", "updated_at"])
        job.refresh_from_db()
        self.assertTrue(job.can_resume_provider_task)

        self.client.force_authenticate(user=self.reader)
        detail_response = self.client.get(f"/api/video-generation-jobs/{job.id}/")
        self.assert_success_envelope(detail_response)
        self.assertTrue(detail_response.data["data"]["can_retry"])
        self.assertTrue(detail_response.data["data"]["can_resume_provider_task"])

        retry_response = self.client.post(f"/api/video-generation-jobs/{job.id}/retry/")
        self.assert_success_envelope(retry_response)
        self.assertEqual(retry_response.data["data"]["status"], VideoGenerationJob.Status.QUEUED)
        self.assertFalse(retry_response.data["data"]["can_resume_provider_task"])
        job.refresh_from_db()
        asset.refresh_from_db()
        self.assertEqual(job.attempt_count, job.max_attempts - 1)
        self.assertEqual(asset.status, VideoAsset.Status.QUEUED)

        claimed_job = claim_next_video_generation_job()
        self.assertEqual(claimed_job.id, job.id)
        self.assertEqual(claimed_job.attempt_count, claimed_job.max_attempts)
        resumed_processing = _begin_scene_asset_processing(
            claimed_job,
            scene,
            VideoAsset.AssetType.VIDEO,
        )
        self.assertEqual(
            resumed_processing["resume_provider_task_id"],
            "provider-task-resume-1",
        )

        _fail_scene_asset_processing(asset.id, claimed_job, "再次中断。", False)
        job.status = VideoGenerationJob.Status.FAILED
        job.save(update_fields=["status", "updated_at"])
        new_job = VideoGenerationJob.objects.create(
            project=project,
            requested_by=self.reader,
            job_type=VideoGenerationJob.JobType.VIDEO_CLIPS,
            status=VideoGenerationJob.Status.RUNNING,
            provider="glm",
            model_name="cogvideox-flash",
            request_payload={"asset_type": VideoAsset.AssetType.VIDEO, "regenerate": False},
            max_attempts=3,
        )
        asset.refresh_from_db()
        asset.status = VideoAsset.Status.QUEUED
        asset.failure_reason = ""
        asset.save(update_fields=["status", "failure_reason", "updated_at"])

        fresh_processing = _begin_scene_asset_processing(
            new_job,
            scene,
            VideoAsset.AssetType.VIDEO,
        )
        self.assertEqual(fresh_processing["resume_provider_task_id"], "")
        asset.refresh_from_db()
        self.assertNotIn("pending_provider_task", asset.metadata)

    @override_settings(
        VIDEO_RENDER_ENABLED=True,
        VIDEO_RENDER_WIDTH=720,
        VIDEO_RENDER_HEIGHT=1280,
        VIDEO_RENDER_FPS=30,
        VIDEO_RENDER_CRF=21,
        VIDEO_RENDER_TIMEOUT_SECONDS=60,
        VIDEO_RENDER_MAX_FILE_BYTES=10 * 1024 * 1024,
        VIDEO_JOB_MAX_ATTEMPTS=3,
    )
    @patch("video_generation.services.get_local_render_capabilities")
    @patch("video_generation.services.render_video_project")
    def test_final_video_render_job_uses_clean_audio_subtitles_and_permissions(
        self,
        mocked_render_video_project,
        mocked_render_capabilities,
    ):
        mocked_render_capabilities.return_value = {"available": True, "engine": "ffmpeg"}
        rendered_content = b"\x00\x00\x00\x18ftypmp42" + b"rendered-final-video" * 8

        def fake_render(render_inputs, subtitle_path, output_path, **options):
            self.assertEqual([item.visual_type for item in render_inputs], ["video", "image"])
            self.assertIsNotNone(render_inputs[0].narration_path)
            self.assertIsNone(render_inputs[1].narration_path)
            self.assertTrue(subtitle_path.is_file())
            self.assertEqual(options["width"], 720)
            self.assertEqual(options["height"], 1280)
            self.assertEqual(options["fps"], 30)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(rendered_content)
            return {
                "file_size": len(rendered_content),
                "sha256": "rendered-sha256",
                "subtitle_mode": "burned_in",
                "scene_count": 2,
                "duration_seconds": 2,
                "video_scene_count": 1,
                "image_scene_count": 1,
                "narration_scene_count": 1,
                "width": options["width"],
                "height": options["height"],
                "fps": options["fps"],
                "crf": options["crf"],
            }

        mocked_render_video_project.side_effect = fake_render
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="Local render project",
            input_text="Local render source " * 40,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        scenes = [
            VideoScene.objects.create(
                project=project,
                scene_no=scene_no,
                title=f"Render scene {scene_no}",
                visual_prompt=f"Render visual {scene_no}",
                narration_text=f"清晰旁白 {scene_no}",
                subtitle_text=f"字幕 {scene_no}",
                duration_seconds=1,
                status=VideoScene.Status.READY,
            )
            for scene_no in (1, 2)
        ]
        missing_project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="Missing render assets",
            input_text="Missing render source " * 40,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        VideoScene.objects.create(
            project=missing_project,
            scene_no=1,
            title="Missing visual",
            duration_seconds=1,
            status=VideoScene.Status.READY,
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            visual_specs = ((scenes[0], VideoAsset.AssetType.VIDEO, "scene-01.mp4"), (scenes[1], VideoAsset.AssetType.IMAGE, "scene-02.png"))
            for scene, asset_type, file_name in visual_specs:
                storage_path = Path("video_projects", str(project.id), "test", file_name).as_posix()
                target_path = Path(media_root) / storage_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(b"test-visual")
                VideoAsset.objects.create(
                    project=project,
                    scene=scene,
                    asset_type=asset_type,
                    status=VideoAsset.Status.READY,
                    storage_path=storage_path,
                    file_name=file_name,
                    mime_type="video/mp4" if asset_type == VideoAsset.AssetType.VIDEO else "image/png",
                    file_size=target_path.stat().st_size,
                    provider="test",
                    metadata={
                        "visual_review": {
                            "status": "pending",
                            "mode": "manual_required",
                        }
                    },
                )

            audio_storage_path = Path("video_projects", str(project.id), "test", "scene-01.wav").as_posix()
            audio_target_path = Path(media_root) / audio_storage_path
            audio_content = _build_test_wav()
            audio_target_path.write_bytes(audio_content)
            audio_asset = VideoAsset.objects.create(
                project=project,
                scene=scenes[0],
                asset_type=VideoAsset.AssetType.AUDIO,
                status=VideoAsset.Status.READY,
                storage_path=audio_storage_path,
                file_name="scene-01.wav",
                mime_type="audio/wav",
                file_size=audio_target_path.stat().st_size,
                provider="test",
            )

            render_job_url = f"/api/video-projects/{project.id}/render/jobs/"
            self.client.force_authenticate(user=None)
            self.assertEqual(self.client.post(render_job_url, {}, format="json").status_code, 401)

            self.client.force_authenticate(user=self.reader)
            capabilities = self.client.get("/api/video-projects/capabilities/").data["data"]
            self.assertTrue(capabilities["local_render_available"])
            self.assertEqual(capabilities["local_render_engine"], "ffmpeg")
            self.assertEqual(capabilities["local_render_size"], "720x1280")

            missing_response = self.client.post(
                f"/api/video-projects/{missing_project.id}/render/jobs/",
                {},
                format="json",
            )
            self.assertEqual(missing_response.status_code, 400)

            subtitle_response = self.client.post(
                f"/api/video-projects/{project.id}/assets/subtitles/",
                {},
                format="json",
            )
            self.assert_success_envelope(subtitle_response)
            unreviewed_visual_response = self.client.post(render_job_url, {}, format="json")
            self.assertEqual(unreviewed_visual_response.status_code, 400)
            self.assertIn("人工复核通过", str(unreviewed_visual_response.data))
            for visual_asset in VideoAsset.objects.filter(
                project=project,
                asset_type__in=(VideoAsset.AssetType.VIDEO, VideoAsset.AssetType.IMAGE),
            ):
                approve_response = self.client.patch(
                    f"/api/video-assets/{visual_asset.id}/visual-review/",
                    {"decision": "approved"},
                    format="json",
                )
                self.assert_success_envelope(approve_response)
            unverified_audio_response = self.client.post(render_job_url, {}, format="json")
            self.assertEqual(unverified_audio_response.status_code, 400)
            self.assertIn("缺少通过的波形及语义确认", str(unverified_audio_response.data))
            audio_asset.metadata = {
                "audio_quality": analyze_wav_audio(audio_content, scenes[0].duration_seconds)
            }
            audio_asset.save(update_fields=["metadata", "updated_at"])
            semantic_review_response = self.client.post(render_job_url, {}, format="json")
            self.assertEqual(semantic_review_response.status_code, 400)
            audio_asset.metadata["audio_review"] = {
                "status": "approved",
                "reviewer_id": self.reader.id,
                "reviewed_at": timezone.now().isoformat(),
            }
            audio_asset.save(update_fields=["metadata", "updated_at"])
            create_response = self.client.post(render_job_url, {}, format="json")
            self.assert_success_envelope(create_response)
            job_id = create_response.data["data"]["id"]
            self.assertEqual(create_response.data["data"]["job_type"], VideoGenerationJob.JobType.RENDER)
            project.refresh_from_db()
            self.assertEqual(project.status, VideoProject.Status.RENDERING)

            other_user = get_user_model().objects.create_user(
                username="other_render_reader",
                password="password12345Strong!",
                role="reader",
            )
            self.client.force_authenticate(user=other_user)
            self.assertEqual(self.client.get(render_job_url).status_code, 404)
            self.assertEqual(self.client.get(f"/api/video-generation-jobs/{job_id}/").status_code, 404)
            self.assertEqual(self.client.get("/api/video-projects/999999/render/jobs/").status_code, 404)

            self.client.force_authenticate(user=self.reader)
            completed_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(completed_job.status, VideoGenerationJob.Status.SUCCEEDED, completed_job.error_message)
            mocked_render_video_project.assert_called_once()

            final_asset = VideoAsset.objects.get(
                project=project,
                scene__isnull=True,
                asset_type=VideoAsset.AssetType.FINAL_VIDEO,
            )
            project.refresh_from_db()
            self.assertEqual(project.status, VideoProject.Status.COMPLETED)
            self.assertEqual(final_asset.status, VideoAsset.Status.READY)
            self.assertEqual(final_asset.mime_type, "video/mp4")
            self.assertEqual(final_asset.metadata["narration_scene_count"], 1)
            self.assertEqual(final_asset.metadata["subtitle_mode"], "burned_in")
            self.assertEqual(final_asset.metadata["fps"], 30)
            self.assertEqual((Path(media_root) / final_asset.storage_path).read_bytes(), rendered_content)

            download_response = self.client.get(f"/api/video-assets/{final_asset.id}/download/")
            self.assertEqual(b"".join(download_response.streaming_content), rendered_content)

            update_response = self.client.patch(
                f"/api/video-projects/{project.id}/scenes/{scenes[0].id}/",
                {"visual_prompt": "Updated after final render"},
                format="json",
            )
            self.assert_success_envelope(update_response)
            final_asset.refresh_from_db()
            project.refresh_from_db()
            self.assertEqual(final_asset.status, VideoAsset.Status.STALE)
            self.assertEqual(project.status, VideoProject.Status.STORYBOARD_READY)

    @override_settings(
        VIDEO_IMAGE_API_URL="https://api.example.com/images/generations",
        VIDEO_IMAGE_API_KEY="image-test-key",
        VIDEO_IMAGE_MODEL="glm-image-test",
        VIDEO_IMAGE_SIZE="960x1728",
        VIDEO_IMAGE_TIMEOUT_SECONDS=10,
        VIDEO_IMAGE_DAILY_JOB_LIMIT=3,
        VIDEO_ASSET_MAX_FILE_BYTES=1024 * 1024,
        VIDEO_JOB_MAX_ATTEMPTS=3,
    )
    @patch("video_generation.providers.urlopen")
    def test_video_asset_regeneration_preserves_last_good_file_and_delete_cleans_up(self, mocked_urlopen):
        image_result_url = "https://media.example.com/regenerated.png"
        regenerated_content = b"\x89PNG\r\n\x1a\nregenerated-image"
        image_response = json.dumps({"data": [{"url": image_result_url}]}).encode("utf-8")
        rate_limit_error = json.dumps(
            {"error": {"code": "1302", "message": "provider message must not be persisted"}}
        ).encode("utf-8")
        mocked_urlopen.side_effect = [
            HTTPError(
                "https://api.example.com/images/generations",
                429,
                "too many requests",
                {"Content-Type": "application/json"},
                io.BytesIO(rate_limit_error),
            ),
            _VideoProviderResponse(image_response, url="https://api.example.com/images/generations"),
            _VideoProviderResponse(regenerated_content, "image/png", image_result_url),
        ]
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            title="Regenerate asset",
            input_text="Regenerate source " * 40,
            duration_target=60,
            status=VideoProject.Status.STORYBOARD_READY,
        )
        scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Existing scene",
            visual_prompt="Regenerate this vertical image.",
            duration_seconds=60,
            status=VideoScene.Status.READY,
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            storage_path = Path("video_projects", str(project.id), "scenes", "scene-01", "image.png").as_posix()
            target_path = Path(media_root) / storage_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(b"last-good-image")
            asset = VideoAsset.objects.create(
                project=project,
                scene=scene,
                asset_type=VideoAsset.AssetType.IMAGE,
                status=VideoAsset.Status.READY,
                storage_path=storage_path,
                file_name="scene-01.png",
                mime_type="image/png",
                file_size=len(b"last-good-image"),
                provider="glm",
                metadata={"generation_job_id": 0},
            )
            self.client.force_authenticate(user=self.reader)
            create_response = self.client.post(
                f"/api/video-projects/{project.id}/assets/images/jobs/",
                {"regenerate": True},
                format="json",
            )
            self.assert_success_envelope(create_response)
            job_id = create_response.data["data"]["id"]
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.READY)

            failed_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(failed_job.status, VideoGenerationJob.Status.FAILED)
            self.assertIn("GLM 账户已达到速率限制", failed_job.error_message)
            self.assertIn("业务错误码 1302", failed_job.error_message)
            self.assertNotIn("provider message must not be persisted", failed_job.error_message)
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.READY)
            self.assertEqual(target_path.read_bytes(), b"last-good-image")
            self.assertEqual(asset.metadata["last_failed_job_id"], job_id)

            retry_response = self.client.post(f"/api/video-generation-jobs/{job_id}/retry/", {}, format="json")
            self.assert_success_envelope(retry_response)
            with self.captureOnCommitCallbacks(execute=True):
                succeeded_job = process_video_generation_job(claim_next_video_generation_job())
            self.assertEqual(succeeded_job.status, VideoGenerationJob.Status.SUCCEEDED, succeeded_job.error_message)
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.READY)
            regenerated_path = Path(media_root) / asset.storage_path
            self.assertNotEqual(regenerated_path, target_path)
            self.assertEqual(regenerated_path.read_bytes(), regenerated_content)
            self.assertFalse(target_path.exists())
            self.assertEqual(asset.metadata["generation_job_id"], job_id)

            queued_job = VideoGenerationJob.objects.create(
                project=project,
                requested_by=self.reader,
                job_type=VideoGenerationJob.JobType.NARRATION_AUDIO,
                status=VideoGenerationJob.Status.QUEUED,
            )
            with self.captureOnCommitCallbacks(execute=True):
                delete_response = self.client.delete(f"/api/video-projects/{project.id}/")
            self.assert_success_envelope(delete_response)
            project.refresh_from_db()
            asset.refresh_from_db()
            queued_job.refresh_from_db()
            self.assertIsNotNone(project.deleted_at)
            self.assertEqual(asset.status, VideoAsset.Status.STALE)
            self.assertEqual(queued_job.status, VideoGenerationJob.Status.CANCELED)
            self.assertFalse(target_path.exists())

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
        image_asset = VideoAsset.objects.create(
            project=project,
            scene=scene,
            asset_type=VideoAsset.AssetType.IMAGE,
            status=VideoAsset.Status.READY,
        )
        audio_asset = VideoAsset.objects.create(
            project=project,
            scene=scene,
            asset_type=VideoAsset.AssetType.AUDIO,
            status=VideoAsset.Status.READY,
        )

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
        image_asset.refresh_from_db()
        audio_asset.refresh_from_db()
        self.assertEqual(project.duration_target, 61)
        self.assertEqual(scene.status, VideoScene.Status.READY)
        self.assertEqual(image_asset.status, VideoAsset.Status.STALE)
        self.assertEqual(audio_asset.status, VideoAsset.Status.STALE)
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

    def test_video_subtitle_asset_generation_download_permissions_and_invalidation(self):
        project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Subtitle asset source",
            title="Subtitle asset project",
            input_text="A courier crosses the city before sunrise. " * 20,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )
        first_scene = VideoScene.objects.create(
            project=project,
            scene_no=1,
            title="Departure",
            narration_text="The courier leaves the old station.",
            subtitle_text="旧字幕第一句",
            duration_seconds=30,
            status=VideoScene.Status.READY,
        )
        VideoScene.objects.create(
            project=project,
            scene_no=2,
            title="Arrival",
            narration_text="The package arrives before sunrise.",
            subtitle_text="第二句字幕",
            duration_seconds=30,
            status=VideoScene.Status.READY,
        )
        empty_project = VideoProject.objects.create(
            owner=self.reader,
            source_type=VideoProject.SourceType.TEXT,
            source_title="Empty storyboard",
            title="Empty storyboard",
            input_text="No scenes are available yet. " * 20,
            duration_target=60,
            aspect_ratio="9:16",
            status=VideoProject.Status.STORYBOARD_READY,
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=Path(media_root)):
            generate_url = f"/api/video-projects/{project.id}/assets/subtitles/"
            self.client.force_authenticate(user=None)
            unauthenticated_response = self.client.post(generate_url, {}, format="json")
            self.assertEqual(unauthenticated_response.status_code, 401)

            self.client.force_authenticate(user=self.reader)
            empty_response = self.client.post(
                f"/api/video-projects/{empty_project.id}/assets/subtitles/",
                {},
                format="json",
            )
            self.assertEqual(empty_response.status_code, 400)

            generate_response = self.client.post(generate_url, {}, format="json")
            self.assert_success_envelope(generate_response)
            asset_data = generate_response.data["data"]
            self.assertEqual(asset_data["asset_type"], VideoAsset.AssetType.SUBTITLE)
            self.assertEqual(asset_data["status"], VideoAsset.Status.READY)
            self.assertEqual(asset_data["file_name"], "storyboard.srt")
            self.assertNotIn("storage_path", asset_data)

            asset = VideoAsset.objects.get(id=asset_data["id"])
            self.assertFalse(Path(asset.storage_path).is_absolute())
            subtitle_path = Path(media_root) / asset.storage_path
            self.assertTrue(subtitle_path.is_file())
            subtitle_content = subtitle_path.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 --> 00:00:30,000", subtitle_content)
            self.assertIn("00:00:30,000 --> 00:01:00,000", subtitle_content)
            self.assertIn("旧字幕第一句", subtitle_content)

            repeat_response = self.client.post(generate_url, {}, format="json")
            self.assert_success_envelope(repeat_response)
            self.assertEqual(repeat_response.data["data"]["id"], asset.id)

            detail_response = self.client.get(f"/api/video-projects/{project.id}/")
            self.assert_success_envelope(detail_response)
            self.assertEqual(len(detail_response.data["data"]["assets"]), 1)
            self.assertEqual(detail_response.data["data"]["assets"][0]["id"], asset.id)

            storyboard_response = self.client.post(
                f"/api/video-projects/{project.id}/storyboard/",
                {"scene_count": 4},
                format="json",
            )
            self.assert_success_envelope(storyboard_response)
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.STALE)

            post_storyboard_response = self.client.post(generate_url, {}, format="json")
            self.assert_success_envelope(post_storyboard_response)
            first_scene = VideoScene.objects.filter(project=project).order_by("scene_no").first()
            update_response = self.client.patch(
                f"/api/video-projects/{project.id}/scenes/{first_scene.id}/",
                {"subtitle_text": "更新后的第一句字幕"},
                format="json",
            )
            self.assert_success_envelope(update_response)
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.STALE)

            stale_download_response = self.client.get(f"/api/video-assets/{asset.id}/download/")
            self.assertEqual(stale_download_response.status_code, 400)

            regenerate_response = self.client.post(generate_url, {}, format="json")
            self.assert_success_envelope(regenerate_response)
            self.assertEqual(regenerate_response.data["data"]["id"], asset.id)
            asset.refresh_from_db()
            self.assertEqual(asset.status, VideoAsset.Status.READY)
            regenerated_content = subtitle_path.read_text(encoding="utf-8")
            self.assertIn("更新后的第一句字幕", regenerated_content)
            self.assertNotIn("旧字幕第一句", regenerated_content)

            self.client.force_authenticate(user=None)
            unauthenticated_download = self.client.get(f"/api/video-assets/{asset.id}/download/")
            self.assertEqual(unauthenticated_download.status_code, 401)

            User = get_user_model()
            other_reader = User.objects.create_user(
                username="other_reader_subtitle_asset",
                password="password12345Strong!",
                role="reader",
            )
            self.client.force_authenticate(user=other_reader)
            denied_generate_response = self.client.post(generate_url, {}, format="json")
            self.assertEqual(denied_generate_response.status_code, 404)
            denied_download_response = self.client.get(f"/api/video-assets/{asset.id}/download/")
            self.assertEqual(denied_download_response.status_code, 404)

            self.client.force_authenticate(user=self.admin)
            admin_download_response = self.client.get(f"/api/video-assets/{asset.id}/download/")
            self.assertEqual(admin_download_response.status_code, 200)
            self.assertEqual(b"".join(admin_download_response.streaming_content), regenerated_content.encode("utf-8"))

            asset.storage_path = "../outside.srt"
            asset.save(update_fields=["storage_path", "updated_at"])
            unsafe_path_response = self.client.get(f"/api/video-assets/{asset.id}/download/")
            self.assertEqual(unsafe_path_response.status_code, 404)

            asset_audits = AuditLog.objects.filter(
                content_type=AuditLog.ContentType.VIDEO_PROJECT,
                object_id=project.id,
                reason__contains=f'"asset_id": {asset.id}',
            )
            self.assertGreaterEqual(asset_audits.count(), 3)
            self.assertFalse(any("更新后的第一句字幕" in audit.reason for audit in asset_audits))

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
