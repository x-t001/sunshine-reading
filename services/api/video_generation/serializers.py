import re

from rest_framework import serializers

from chapters.models import Chapter
from novels.models import Novel
from users.permissions import is_admin_user

from .models import VideoAsset, VideoGenerationJob, VideoProject, VideoScene


UNSAFE_TEXT_PATTERNS = (
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*/\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"\bon\w+\s*=", re.IGNORECASE),
    re.compile(r"<\s*(iframe|object|embed)", re.IGNORECASE),
)
AGENT_ENTITY_ID_PATTERN = r"^[a-z][a-z0-9_]{1,49}$"
MAX_NOVEL_SOURCE_CHAPTER_RANGE = 10


def _agent_entity_id_field(**kwargs):
    error_messages = {
        "invalid": "标识必须以小写字母开头，且只能包含小写字母、数字和下划线。",
    }
    error_messages.update(kwargs.pop("error_messages", {}))
    return serializers.RegexField(
        regex=AGENT_ENTITY_ID_PATTERN,
        max_length=50,
        trim_whitespace=True,
        error_messages=error_messages,
        **kwargs,
    )


class VideoProjectOwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    nickname = serializers.CharField(read_only=True)


class VideoSceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoScene
        fields = (
            "id",
            "scene_no",
            "title",
            "visual_prompt",
            "narration_text",
            "subtitle_text",
            "duration_seconds",
            "camera_direction",
            "mood",
            "agent_metadata",
            "status",
            "failure_reason",
            "created_at",
            "updated_at",
        )


class VideoAssetSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    scene_id = serializers.IntegerField(read_only=True, allow_null=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoAsset
        fields = (
            "id",
            "project_id",
            "scene_id",
            "asset_type",
            "status",
            "file_name",
            "mime_type",
            "file_size",
            "provider",
            "metadata",
            "failure_reason",
            "download_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_download_url(self, obj):
        if obj.status != VideoAsset.Status.READY:
            return ""
        return f"/api/video-assets/{obj.id}/download/"


class VideoProjectListSerializer(serializers.ModelSerializer):
    owner = VideoProjectOwnerSerializer(read_only=True)
    source_novel_id = serializers.IntegerField(read_only=True, allow_null=True)
    source_chapter_id = serializers.IntegerField(read_only=True, allow_null=True)
    scene_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VideoProject
        fields = (
            "id",
            "owner",
            "source_type",
            "source_novel_id",
            "source_chapter_id",
            "source_title",
            "title",
            "style_preset",
            "duration_target",
            "aspect_ratio",
            "status",
            "failure_reason",
            "scene_count",
            "created_at",
            "updated_at",
            "deleted_at",
        )


class VideoProjectDetailSerializer(VideoProjectListSerializer):
    scenes = VideoSceneSerializer(many=True, read_only=True)
    assets = VideoAssetSerializer(many=True, read_only=True)

    class Meta(VideoProjectListSerializer.Meta):
        fields = VideoProjectListSerializer.Meta.fields + (
            "summary",
            "input_text",
            "source_excerpt_hash",
            "agent_workflow",
            "scenes",
            "assets",
        )


class VideoProjectQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True)
    source_type = serializers.ChoiceField(choices=VideoProject.SourceType.choices, required=False)
    status = serializers.ChoiceField(choices=VideoProject.Status.choices, required=False)


class AdminVideoProjectQuerySerializer(VideoProjectQuerySerializer):
    owner_id = serializers.IntegerField(min_value=1, required=False)
    include_deleted = serializers.BooleanField(required=False, default=False)


class VideoProjectCreateSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=VideoProject.SourceType.choices, required=False, default=VideoProject.SourceType.TEXT)
    input_text = serializers.CharField(min_length=500, max_length=3000, trim_whitespace=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    style_preset = serializers.CharField(max_length=64, required=False, default="cinematic_story", allow_blank=False)
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)
    aspect_ratio = serializers.ChoiceField(choices=("9:16",), required=False, default="9:16")

    def validate_input_text(self, value):
        for pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                raise serializers.ValidationError("Input text contains unsafe HTML or script content.")
        return value

    def validate(self, attrs):
        if attrs["source_type"] != VideoProject.SourceType.TEXT:
            raise serializers.ValidationError({"source_type": ["Only pasted text projects are supported in this iteration."]})
        return attrs


class VideoProjectStoryboardSerializer(serializers.Serializer):
    scene_count = serializers.IntegerField(min_value=4, max_value=12, required=False)


class VideoAssetJobCreateSerializer(serializers.Serializer):
    regenerate = serializers.BooleanField(required=False, default=False)
    scene_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
        allow_empty=False,
        max_length=12,
    )

    def validate_scene_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("分镜 ID 不得重复。")
        return value


class VideoRenderJobCreateSerializer(serializers.Serializer):
    regenerate = serializers.BooleanField(required=False, default=False)
    include_narration = serializers.BooleanField(required=False, default=True)
    include_subtitles = serializers.BooleanField(required=False, default=True)


class VideoAudioReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "rejected"))


class VideoVisualReviewSerializer(serializers.Serializer):
    ISSUE_CODES = (
        "identity_drift",
        "wardrobe_drift",
        "scene_drift",
        "prop_state_error",
        "anatomy_error",
        "collision_or_clipping",
        "motion_or_physics_error",
        "continuity_break",
        "composition_error",
        "other",
    )

    decision = serializers.ChoiceField(choices=("approved", "rejected"))
    issue_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=ISSUE_CODES),
        required=False,
        default=list,
        allow_empty=True,
        max_length=5,
    )
    note = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        trim_whitespace=True,
        max_length=200,
    )

    def validate(self, attrs):
        issue_codes = attrs["issue_codes"]
        if len(issue_codes) != len(set(issue_codes)):
            raise serializers.ValidationError({"issue_codes": ["问题代码不得重复。"]})
        if attrs["decision"] == "rejected" and not issue_codes:
            raise serializers.ValidationError({"issue_codes": ["标记重拍时至少选择一个画面问题。"]})
        if attrs["decision"] == "approved" and issue_codes:
            raise serializers.ValidationError({"issue_codes": ["画面通过时不得同时提交问题代码。"]})
        return attrs


class VideoSourceChapterQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)


class VideoSourceChapterSerializer(serializers.ModelSerializer):
    novel_id = serializers.IntegerField(read_only=True)
    novel_title = serializers.CharField(source="novel.title", read_only=True)
    source_access = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            "id",
            "novel_id",
            "novel_title",
            "title",
            "chapter_number",
            "word_count",
            "status",
            "audit_status",
            "source_access",
            "published_at",
            "updated_at",
        )

    def get_source_access(self, obj):
        user = self.context.get("user")
        if is_admin_user(user):
            return "admin"
        if obj.novel.author_id == getattr(user, "id", None):
            return "owned"
        return "public"


class VideoProjectChapterCreateSerializer(serializers.Serializer):
    chapter_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    style_preset = serializers.CharField(max_length=64, required=False, default="cinematic_story", allow_blank=False)
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)
    aspect_ratio = serializers.ChoiceField(choices=("9:16",), required=False, default="9:16")


class VideoSourceNovelQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)


class VideoSourceNovelSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(read_only=True)
    author_name = serializers.SerializerMethodField()
    chapter_count = serializers.IntegerField(source="accessible_chapter_count", read_only=True)
    first_chapter_number = serializers.IntegerField(read_only=True)
    last_chapter_number = serializers.IntegerField(read_only=True)
    source_access = serializers.SerializerMethodField()

    class Meta:
        model = Novel
        fields = (
            "id",
            "title",
            "author_id",
            "author_name",
            "chapter_count",
            "first_chapter_number",
            "last_chapter_number",
            "status",
            "audit_status",
            "source_access",
            "updated_at",
        )

    def get_author_name(self, obj):
        return obj.author.nickname or obj.author.username

    def get_source_access(self, obj):
        user = self.context.get("user")
        if is_admin_user(user):
            return "admin"
        if obj.author_id == getattr(user, "id", None):
            return "owned"
        return "public"


class VideoProjectNovelCreateSerializer(serializers.Serializer):
    novel_id = serializers.IntegerField(min_value=1)
    start_chapter_number = serializers.IntegerField(min_value=1)
    end_chapter_number = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    style_preset = serializers.CharField(max_length=64, required=False, default="cinematic_story", allow_blank=False)
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)
    aspect_ratio = serializers.ChoiceField(choices=("9:16",), required=False, default="9:16")

    def validate(self, attrs):
        start = attrs["start_chapter_number"]
        end = attrs["end_chapter_number"]
        if end < start:
            raise serializers.ValidationError({"end_chapter_number": ["End chapter must not precede start chapter."]})
        if end - start + 1 > MAX_NOVEL_SOURCE_CHAPTER_RANGE:
            raise serializers.ValidationError(
                {"end_chapter_number": [f"A source range can contain at most {MAX_NOVEL_SOURCE_CHAPTER_RANGE} chapter numbers."]}
            )
        return attrs


class VideoGenerationJobSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(read_only=True)
    can_retry = serializers.SerializerMethodField()
    can_resume_provider_task = serializers.SerializerMethodField()

    class Meta:
        model = VideoGenerationJob
        fields = (
            "id",
            "project_id",
            "job_type",
            "status",
            "provider",
            "model_name",
            "request_payload",
            "attempt_count",
            "max_attempts",
            "can_retry",
            "can_resume_provider_task",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_can_retry(self, obj):
        return (
            obj.status == VideoGenerationJob.Status.FAILED
            and (obj.attempt_count < obj.max_attempts or obj.can_resume_provider_task)
        )

    def get_can_resume_provider_task(self, obj):
        return obj.can_resume_provider_task


class VideoAgentCharacterSerializer(serializers.Serializer):
    id = _agent_entity_id_field()
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    story_role = serializers.CharField(max_length=100, trim_whitespace=True)
    identity = serializers.CharField(max_length=300, trim_whitespace=True)
    appearance = serializers.CharField(max_length=500, trim_whitespace=True)
    behavior = serializers.CharField(max_length=300, trim_whitespace=True)
    voice_profile_id = _agent_entity_id_field()


class VideoAgentCharacterLookSerializer(serializers.Serializer):
    id = _agent_entity_id_field()
    character_id = _agent_entity_id_field()
    label = serializers.CharField(max_length=100, trim_whitespace=True)
    wardrobe = serializers.CharField(max_length=500, trim_whitespace=True)
    hair_makeup = serializers.CharField(max_length=300, trim_whitespace=True)
    signature_features = serializers.CharField(max_length=300, trim_whitespace=True)
    color_palette = serializers.CharField(max_length=200, trim_whitespace=True)
    reference_prompt = serializers.CharField(max_length=700, trim_whitespace=True)


class VideoAgentLocationSerializer(serializers.Serializer):
    id = _agent_entity_id_field()
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    geography = serializers.CharField(max_length=300, trim_whitespace=True)
    visual_anchor = serializers.CharField(max_length=700, trim_whitespace=True)
    time_of_day = serializers.CharField(max_length=100, trim_whitespace=True)
    weather = serializers.CharField(max_length=100, trim_whitespace=True)
    lighting = serializers.CharField(max_length=300, trim_whitespace=True)
    color_palette = serializers.CharField(max_length=200, trim_whitespace=True)
    reference_prompt = serializers.CharField(max_length=700, trim_whitespace=True)


class VideoAgentPropSerializer(serializers.Serializer):
    id = _agent_entity_id_field()
    name = serializers.CharField(max_length=100, trim_whitespace=True)
    owner_character_id = _agent_entity_id_field(required=False, allow_blank=True, default="")
    visual_anchor = serializers.CharField(max_length=500, trim_whitespace=True)
    initial_state = serializers.CharField(max_length=300, trim_whitespace=True)
    continuity_rule = serializers.CharField(max_length=300, trim_whitespace=True)
    reference_prompt = serializers.CharField(max_length=700, trim_whitespace=True)


class VideoAgentDialogueUnitSerializer(serializers.Serializer):
    class Kind:
        NARRATION = "narration"
        DIALOGUE = "dialogue"

    id = _agent_entity_id_field()
    beat_no = serializers.IntegerField(min_value=1, max_value=12)
    kind = serializers.ChoiceField(choices=(Kind.NARRATION, Kind.DIALOGUE))
    speaker_id = _agent_entity_id_field()
    text = serializers.CharField(max_length=160, trim_whitespace=True)
    subtitle_text = serializers.CharField(max_length=160, trim_whitespace=True)
    emotion = serializers.CharField(max_length=100, trim_whitespace=True)
    pause_after_ms = serializers.IntegerField(min_value=0, max_value=2000)
    target_duration_ms = serializers.IntegerField(min_value=500, max_value=15000)
    voice_profile_id = _agent_entity_id_field()


class VideoAgentBeatSerializer(serializers.Serializer):
    beat_no = serializers.IntegerField(min_value=1, max_value=12)
    purpose = serializers.CharField(max_length=300, trim_whitespace=True)
    action = serializers.CharField(max_length=700, trim_whitespace=True)
    outcome = serializers.CharField(max_length=500, trim_whitespace=True)
    location_id = _agent_entity_id_field()
    character_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=8,
    )
    look_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=8,
    )
    prop_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=8,
    )
    dialogue_unit_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=4,
    )


class VideoAgentProductionPlanSerializer(serializers.Serializer):
    logline = serializers.CharField(max_length=500, trim_whitespace=True)
    theme = serializers.CharField(max_length=300, trim_whitespace=True)
    visual_style = serializers.CharField(max_length=700, trim_whitespace=True)
    characters = VideoAgentCharacterSerializer(many=True, allow_empty=True)
    character_looks = VideoAgentCharacterLookSerializer(many=True, allow_empty=True)
    locations = VideoAgentLocationSerializer(many=True, allow_empty=False)
    props = VideoAgentPropSerializer(many=True, allow_empty=True)
    dialogue_units = VideoAgentDialogueUnitSerializer(many=True, allow_empty=False)
    continuity_rules = serializers.ListField(
        child=serializers.CharField(max_length=300, trim_whitespace=True),
        allow_empty=False,
        max_length=12,
    )
    beats = VideoAgentBeatSerializer(many=True)

    def validate(self, attrs):
        expected_scene_count = self.context.get("expected_scene_count")
        beats = attrs["beats"]
        if expected_scene_count is not None and len(beats) != expected_scene_count:
            raise serializers.ValidationError(
                {"beats": [f"剧情策划必须包含 {expected_scene_count} 个连续节拍。"]}
            )

        entity_groups = {
            "characters": attrs["characters"],
            "character_looks": attrs["character_looks"],
            "locations": attrs["locations"],
            "props": attrs["props"],
            "dialogue_units": attrs["dialogue_units"],
        }
        for field_name, items in entity_groups.items():
            item_ids = [item["id"] for item in items]
            if len(item_ids) != len(set(item_ids)):
                raise serializers.ValidationError({field_name: ["实体标识不得重复。"]})

        entity_prefixes = {
            "characters": "char_",
            "character_looks": "look_",
            "locations": "loc_",
            "props": "prop_",
            "dialogue_units": "line_",
        }
        for field_name, prefix in entity_prefixes.items():
            if any(not item["id"].startswith(prefix) for item in entity_groups[field_name]):
                raise serializers.ValidationError({field_name: [f"实体标识必须使用 {prefix} 前缀。"]})

        all_entity_ids = [item["id"] for items in entity_groups.values() for item in items]
        if len(all_entity_ids) != len(set(all_entity_ids)):
            raise serializers.ValidationError("角色、形象、场景、道具和台词必须使用全局唯一标识。")

        character_ids = [item["id"] for item in attrs["characters"]]
        location_ids = [item["id"] for item in attrs["locations"]]
        look_by_id = {item["id"]: item for item in attrs["character_looks"]}
        prop_by_id = {item["id"]: item for item in attrs["props"]}
        dialogue_by_id = {item["id"]: item for item in attrs["dialogue_units"]}

        expected_beat_numbers = list(range(1, len(beats) + 1))
        if [beat["beat_no"] for beat in beats] != expected_beat_numbers:
            raise serializers.ValidationError({"beats": ["剧情节拍编号必须从 1 连续递增。"]})
        max_silent_beat_count = max(1, len(beats) // 3)
        if sum(not beat["dialogue_unit_ids"] for beat in beats) > max_silent_beat_count:
            raise serializers.ValidationError(
                {"beats": [f"静默镜头不得超过 {max_silent_beat_count} 个，以保证叙事信息完整。"]}
            )

        known_characters = set(character_ids)
        known_locations = set(location_ids)
        if {item["character_id"] for item in attrs["character_looks"]} - known_characters:
            raise serializers.ValidationError({"character_looks": ["角色形象引用了不存在的角色。"]})
        if known_characters - {item["character_id"] for item in attrs["character_looks"]}:
            raise serializers.ValidationError({"character_looks": ["每个角色必须至少定义一个形象版本。"]})

        unknown_prop_owners = {
            item["owner_character_id"]
            for item in attrs["props"]
            if item["owner_character_id"] and item["owner_character_id"] not in known_characters
        }
        if unknown_prop_owners:
            raise serializers.ValidationError({"props": ["道具归属引用了不存在的角色。"]})

        for dialogue in attrs["dialogue_units"]:
            if dialogue["beat_no"] > len(beats):
                raise serializers.ValidationError({"dialogue_units": ["台词单元引用了不存在的剧情节拍。"]})
            if dialogue["kind"] == VideoAgentDialogueUnitSerializer.Kind.NARRATION:
                if dialogue["speaker_id"] != "narrator":
                    raise serializers.ValidationError({"dialogue_units": ["旁白单元的 speaker_id 必须为 narrator。"]})
            elif dialogue["speaker_id"] not in known_characters:
                raise serializers.ValidationError({"dialogue_units": ["角色台词引用了不存在的角色。"]})

        clip_duration_ms = int(self.context.get("clip_duration_seconds") or 0) * 1000
        for beat in beats:
            for field_name in ("character_ids", "look_ids", "prop_ids", "dialogue_unit_ids"):
                if len(beat[field_name]) != len(set(beat[field_name])):
                    raise serializers.ValidationError({"beats": [f"剧情节拍中的 {field_name} 不得重复。"]})
            if beat["location_id"] not in known_locations:
                raise serializers.ValidationError({"beats": ["剧情节拍引用了不存在的场景。"]})
            if set(beat["character_ids"]) - known_characters:
                raise serializers.ValidationError({"beats": ["剧情节拍引用了不存在的角色。"]})
            if set(beat["look_ids"]) - set(look_by_id):
                raise serializers.ValidationError({"beats": ["剧情节拍引用了不存在的角色形象。"]})
            if set(beat["prop_ids"]) - set(prop_by_id):
                raise serializers.ValidationError({"beats": ["剧情节拍引用了不存在的道具。"]})
            if set(beat["dialogue_unit_ids"]) - set(dialogue_by_id):
                raise serializers.ValidationError({"beats": ["剧情节拍引用了不存在的台词单元。"]})

            look_character_ids = {look_by_id[item_id]["character_id"] for item_id in beat["look_ids"]}
            if look_character_ids != set(beat["character_ids"]):
                raise serializers.ValidationError({"beats": ["剧情节拍中的每个出镜角色必须且只能引用对应形象。"]})

            beat_dialogues = [dialogue_by_id[item_id] for item_id in beat["dialogue_unit_ids"]]
            expected_dialogue_ids = {
                item["id"] for item in attrs["dialogue_units"] if item["beat_no"] == beat["beat_no"]
            }
            if set(beat["dialogue_unit_ids"]) != expected_dialogue_ids:
                raise serializers.ValidationError({"beats": ["剧情节拍必须完整引用归属于它的台词单元。"]})
            if len({item["speaker_id"] for item in beat_dialogues}) > 1:
                raise serializers.ValidationError({"dialogue_units": ["当前单声道配音流程要求每个镜头最多只有一名说话者。"]})
            planned_audio_ms = sum(
                item["target_duration_ms"] + item["pause_after_ms"] for item in beat_dialogues
            )
            if clip_duration_ms and planned_audio_ms > clip_duration_ms:
                raise serializers.ValidationError(
                    {"dialogue_units": ["单镜台词目标时长不得超过视频模型片段时长。"]},
                    code="dialogue_timing_overflow",
                )
            max_text_length = max(8, (clip_duration_ms // 1000) * 5) if clip_duration_ms else 160
            spoken_text_length = len("".join("".join(item["text"].split()) for item in beat_dialogues))
            if spoken_text_length > max_text_length:
                raise serializers.ValidationError(
                    {"dialogue_units": ["单镜台词过长，无法在画面时长内清楚读完。"]},
                    code="dialogue_text_too_long",
                )
        return attrs


class VideoAgentPropStateSerializer(serializers.Serializer):
    prop_id = _agent_entity_id_field()
    state = serializers.CharField(max_length=300, trim_whitespace=True)


class VideoAiStoryboardSceneSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, trim_whitespace=True)
    visual_prompt = serializers.CharField(max_length=2000, trim_whitespace=True)
    narration_text = serializers.CharField(max_length=2000, allow_blank=True, trim_whitespace=True)
    subtitle_text = serializers.CharField(max_length=500, allow_blank=True, trim_whitespace=True)
    duration_seconds = serializers.IntegerField(min_value=1, max_value=30)
    camera_direction = serializers.CharField(max_length=200, allow_blank=True, trim_whitespace=True)
    mood = serializers.CharField(max_length=100, allow_blank=True, trim_whitespace=True)
    story_function = serializers.CharField(max_length=300, trim_whitespace=True)
    location_id = _agent_entity_id_field()
    character_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=8,
    )
    look_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=8,
    )
    prop_states = VideoAgentPropStateSerializer(many=True, allow_empty=True)
    dialogue_unit_ids = serializers.ListField(
        child=_agent_entity_id_field(),
        allow_empty=True,
        max_length=4,
    )
    start_state = serializers.CharField(max_length=700, trim_whitespace=True)
    end_state = serializers.CharField(max_length=700, trim_whitespace=True)
    continuity_anchor = serializers.CharField(max_length=700, trim_whitespace=True)
    transition_out = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)
    motion_prompt = serializers.CharField(max_length=700, trim_whitespace=True)

    def validate(self, attrs):
        for field_name, value in attrs.items():
            if not isinstance(value, str):
                continue
            for pattern in UNSAFE_TEXT_PATTERNS:
                if pattern.search(value):
                    raise serializers.ValidationError({field_name: ["AI scene contains unsafe HTML or script content."]})
        return attrs


class VideoAiStoryboardResultSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)
    scenes = VideoAiStoryboardSceneSerializer(many=True)

    def validate_summary(self, value):
        for pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                raise serializers.ValidationError("AI summary contains unsafe HTML or script content.")
        return value

    def validate_scenes(self, value):
        expected_scene_count = self.context.get("expected_scene_count")
        if expected_scene_count is not None and len(value) != expected_scene_count:
            raise serializers.ValidationError(f"AI storyboard must contain exactly {expected_scene_count} scenes.")

        production_plan = self.context.get("production_plan") or {}
        beats = production_plan.get("beats") or []
        dialogue_by_id = {item["id"]: item for item in production_plan.get("dialogue_units") or []}
        for index, scene in enumerate(value):
            beat = beats[index] if index < len(beats) else {}
            for field_name in ("character_ids", "look_ids", "dialogue_unit_ids"):
                if len(scene[field_name]) != len(set(scene[field_name])):
                    raise serializers.ValidationError(f"AI 镜头 {index + 1} 的 {field_name} 不得重复。")
            references = (
                ("location_id", {scene["location_id"]}, {beat.get("location_id")}),
                ("character_ids", set(scene["character_ids"]), set(beat.get("character_ids") or [])),
                ("look_ids", set(scene["look_ids"]), set(beat.get("look_ids") or [])),
                (
                    "prop_states",
                    {item["prop_id"] for item in scene["prop_states"]},
                    set(beat.get("prop_ids") or []),
                ),
                (
                    "dialogue_unit_ids",
                    set(scene["dialogue_unit_ids"]),
                    set(beat.get("dialogue_unit_ids") or []),
                ),
            )
            for field_name, actual_ids, expected_ids in references:
                if actual_ids != expected_ids:
                    raise serializers.ValidationError(
                        f"AI 镜头 {index + 1} 的 {field_name} 必须与对应剧情节拍完全一致。"
                    )
            if len(scene["prop_states"]) != len({item["prop_id"] for item in scene["prop_states"]}):
                raise serializers.ValidationError(f"AI 镜头 {index + 1} 的道具状态不得重复。")

            dialogue_units = [dialogue_by_id[item_id] for item_id in scene["dialogue_unit_ids"]]
            planned_narration = " ".join(item["text"] for item in dialogue_units).strip()
            planned_subtitle = "\n".join(item["subtitle_text"] for item in dialogue_units).strip()
            if scene["narration_text"] != planned_narration:
                raise serializers.ValidationError(f"AI 镜头 {index + 1} 的旁白必须原样复用台词拆解结果。")
            if scene["subtitle_text"] != planned_subtitle:
                raise serializers.ValidationError(f"AI 镜头 {index + 1} 的字幕必须原样复用台词拆解结果。")
        return value


class VideoSceneUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, trim_whitespace=True)
    visual_prompt = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    narration_text = serializers.CharField(max_length=2000, required=False, allow_blank=True, trim_whitespace=True)
    subtitle_text = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)
    duration_seconds = serializers.IntegerField(min_value=1, max_value=30, required=False)
    camera_direction = serializers.CharField(max_length=200, required=False, allow_blank=True, trim_whitespace=True)
    mood = serializers.CharField(max_length=100, required=False, allow_blank=True, trim_whitespace=True)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one editable scene field is required.")

        for field_name in ("title", "visual_prompt", "narration_text", "subtitle_text", "camera_direction", "mood"):
            value = attrs.get(field_name)
            if value is None:
                continue
            for pattern in UNSAFE_TEXT_PATTERNS:
                if pattern.search(value):
                    raise serializers.ValidationError({field_name: ["Field contains unsafe HTML or script content."]})
        return attrs


class VideoStoryDraftSerializer(serializers.Serializer):
    GENRE_CHOICES = (
        ("fantasy", "Fantasy"),
        ("urban", "Urban"),
        ("romance", "Romance"),
        ("sci_fi", "Sci-fi"),
        ("mystery", "Mystery"),
        ("history", "History"),
    )
    TONE_CHOICES = (
        ("cinematic", "Cinematic"),
        ("warm", "Warm"),
        ("suspense", "Suspense"),
        ("high_energy", "High energy"),
        ("sad", "Sad"),
    )

    prompt = serializers.CharField(min_length=10, max_length=300, trim_whitespace=True)
    protagonist = serializers.CharField(max_length=80, required=False, allow_blank=True, trim_whitespace=True)
    key_conflict = serializers.CharField(max_length=160, required=False, allow_blank=True, trim_whitespace=True)
    genre = serializers.ChoiceField(choices=GENRE_CHOICES, required=False, default="fantasy")
    tone = serializers.ChoiceField(choices=TONE_CHOICES, required=False, default="cinematic")
    duration_target = serializers.IntegerField(min_value=30, max_value=90, required=False, default=60)

    def validate_prompt(self, value):
        for pattern in UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                raise serializers.ValidationError("Prompt contains unsafe HTML or script content.")
        return value
