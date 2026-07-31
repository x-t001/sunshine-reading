from copy import deepcopy
import hashlib

from django.utils import timezone


WORKFLOW_VERSION = "2.2"
WORKFLOW_MODE = "multi_agent"
MULTI_SCENE_MARKERS = ("随后切到", "转场到", "与此同时", "另一边", "画面切换", "镜头切到")
LOOK_CHANGE_MARKERS = ("换装", "更衣", "变装", "穿上", "脱下", "造型变化", "时间流逝")
PHYSICAL_REALISM_RULES = (
    "人物肢体数量、关节方向和身体比例保持正常，面部结构稳定。",
    "人物、衣物、道具和环境表面不得互相穿透，抓握、坐立和脚部接触点必须清楚。",
    "动作遵循重力、惯性和支撑关系，不得无因悬空、瞬移或改变运动方向。",
)
LOGIC_CONTINUITY_RULES = (
    "每镜只允许制作设定和当前节拍明确引用的角色、形象、场景与道具出现。",
    "角色、道具和环境状态必须从上一镜结果演进，不得无因出现、消失、复制或复原。",
    "镜头动作必须从 start_state 开始并以 end_state 结束，不得倒置已确定的因果关系。",
)
PHYSICAL_RISK_MARKERS = (
    "出现穿模",
    "多出一只手",
    "多余手臂",
    "身体互相穿插",
    "道具穿透人物",
    "脚部离地悬空",
)
REPAIR_COUNTER_FIELDS = (
    "removed_out_of_range_dialogue_units",
    "rewritten_beat_dialogue_references",
    "normalized_dialogue_timing_beats",
    "normalized_dialogue_timing_units",
    "generated_missing_character_looks",
    "removed_unknown_look_references",
    "rewritten_beat_look_references",
)


def _empty_repair_report():
    return {
        "version": "1.4",
        "applied": False,
        **{field_name: 0 for field_name in REPAIR_COUNTER_FIELDS},
        "provider_schema_repair_applied": False,
        "provider_schema_repair_call_count": 0,
        "provider_dialogue_repair_applied": False,
        "provider_dialogue_repair_call_count": 0,
    }


def _trim(value, limit):
    normalized = " ".join(str(value or "").split())
    return normalized if len(normalized) <= limit else normalized[:limit].rstrip()


def _is_valid_character_id(value):
    allowed_characters = "abcdefghijklmnopqrstuvwxyz0123456789_"
    return (
        isinstance(value, str)
        and 2 <= len(value) <= 50
        and value.startswith("char_")
        and all(character in allowed_characters for character in value)
    )


def _next_generated_look_id(character_index, used_entity_ids):
    collision_index = 0
    while True:
        suffix = f"_{collision_index:02d}" if collision_index else ""
        candidate = f"look_auto_{character_index:02d}{suffix}"
        if candidate not in used_entity_ids:
            return candidate
        collision_index += 1


def _allocate_proportional_budget(weights, budget):
    if budget <= 0 or not weights:
        return [0] * len(weights)
    total_weight = sum(weights)
    if total_weight <= 0:
        return [0] * len(weights)

    bounded_budget = min(budget, total_weight)
    allocations = [bounded_budget * weight // total_weight for weight in weights]
    remainder = bounded_budget - sum(allocations)
    ranked_indexes = sorted(
        range(len(weights)),
        key=lambda index: (bounded_budget * weights[index] % total_weight, -index),
        reverse=True,
    )
    for index in ranked_indexes[:remainder]:
        allocations[index] += 1
    return allocations


def _normalize_dialogue_timing(dialogue_units, clip_duration_ms):
    if not dialogue_units or clip_duration_ms < len(dialogue_units) * 500:
        return 0

    original_timings = []
    target_durations = []
    pauses = []
    for unit in dialogue_units:
        if not isinstance(unit, dict):
            return 0
        target_duration_ms = unit.get("target_duration_ms")
        pause_after_ms = unit.get("pause_after_ms")
        if (
            not isinstance(target_duration_ms, int)
            or isinstance(target_duration_ms, bool)
            or not isinstance(pause_after_ms, int)
            or isinstance(pause_after_ms, bool)
        ):
            return 0
        original_timings.append((target_duration_ms, pause_after_ms))
        target_durations.append(min(15000, max(500, target_duration_ms)))
        pauses.append(min(2000, max(0, pause_after_ms)))

    if sum(target_durations) + sum(pauses) > clip_duration_ms:
        target_extra_weights = [duration - 500 for duration in target_durations]
        target_extra_budget = clip_duration_ms - len(dialogue_units) * 500
        target_allocations = _allocate_proportional_budget(target_extra_weights, target_extra_budget)
        target_durations = [500 + allocation for allocation in target_allocations]

        remaining_pause_budget = clip_duration_ms - sum(target_durations)
        pauses = _allocate_proportional_budget(pauses, remaining_pause_budget)

    normalized_unit_count = 0
    for unit, original_timing, target_duration_ms, pause_after_ms in zip(
        dialogue_units,
        original_timings,
        target_durations,
        pauses,
    ):
        normalized_timing = (target_duration_ms, pause_after_ms)
        if normalized_timing == original_timing:
            continue
        unit["target_duration_ms"] = target_duration_ms
        unit["pause_after_ms"] = pause_after_ms
        normalized_unit_count += 1
    return normalized_unit_count


def repair_production_plan(payload, expected_scene_count, clip_duration_seconds=None):
    report = _empty_repair_report()
    if (
        not isinstance(payload, dict)
        or isinstance(expected_scene_count, bool)
        or not isinstance(expected_scene_count, int)
        or expected_scene_count < 1
    ):
        return payload, report

    repaired = deepcopy(payload)
    dialogue_units = repaired.get("dialogue_units")
    beats = repaired.get("beats")
    if not isinstance(dialogue_units, list) or not isinstance(beats, list):
        return repaired, report

    retained_dialogue_units = []
    for unit in dialogue_units:
        beat_no = unit.get("beat_no") if isinstance(unit, dict) else None
        is_integer_beat_no = isinstance(beat_no, int) and not isinstance(beat_no, bool)
        if is_integer_beat_no and not 1 <= beat_no <= expected_scene_count:
            report["removed_out_of_range_dialogue_units"] += 1
            continue
        retained_dialogue_units.append(unit)
    repaired["dialogue_units"] = retained_dialogue_units

    if (
        isinstance(clip_duration_seconds, int)
        and not isinstance(clip_duration_seconds, bool)
        and clip_duration_seconds > 0
    ):
        dialogue_units_by_beat = {beat_no: [] for beat_no in range(1, expected_scene_count + 1)}
        for unit in retained_dialogue_units:
            beat_no = unit.get("beat_no") if isinstance(unit, dict) else None
            if (
                isinstance(beat_no, int)
                and not isinstance(beat_no, bool)
                and 1 <= beat_no <= expected_scene_count
            ):
                dialogue_units_by_beat[beat_no].append(unit)
        for beat_dialogue_units in dialogue_units_by_beat.values():
            normalized_unit_count = _normalize_dialogue_timing(
                beat_dialogue_units,
                clip_duration_seconds * 1000,
            )
            if normalized_unit_count:
                report["normalized_dialogue_timing_beats"] += 1
                report["normalized_dialogue_timing_units"] += normalized_unit_count

    characters = repaired.get("characters")
    character_looks = repaired.get("character_looks")
    generated_look_by_character = {}
    if isinstance(characters, list) and isinstance(character_looks, list):
        entity_groups = [
            items
            for field_name in ("characters", "character_looks", "locations", "props", "dialogue_units")
            if isinstance((items := repaired.get(field_name)), list)
        ]
        used_entity_ids = {
            item.get("id")
            for items in entity_groups
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        covered_character_ids = {
            item.get("character_id")
            for item in character_looks
            if isinstance(item, dict) and isinstance(item.get("character_id"), str)
        }
        for character_index, character in enumerate(characters, start=1):
            if not isinstance(character, dict):
                continue
            character_id = character.get("id")
            name = character.get("name")
            identity = character.get("identity")
            appearance = character.get("appearance")
            if (
                character_id in covered_character_ids
                or not _is_valid_character_id(character_id)
                or not all(isinstance(value, str) and value.strip() for value in (name, identity, appearance))
            ):
                continue

            look_id = _next_generated_look_id(character_index, used_entity_ids)
            used_entity_ids.add(look_id)
            generated_look = {
                "id": look_id,
                "character_id": character_id,
                "label": "默认连续形象",
                "wardrobe": _trim(
                    f"符合{identity}身份的固定基础服装，款式、颜色和穿着状态在所有出镜节拍保持一致",
                    500,
                ),
                "hair_makeup": _trim(f"{appearance}；发型和面部特征保持固定", 300),
                "signature_features": _trim(f"{appearance}；作为跨镜头稳定识别特征", 300),
                "color_palette": _trim(repaired.get("visual_style"), 200) or "遵循项目统一视觉风格",
                "reference_prompt": _trim(
                    f"{name}，{identity}，{appearance}，固定基础服装，竖屏角色设定图，"
                    "面容、发型、服装和配色在后续镜头保持一致",
                    700,
                ),
            }
            character_looks.append(generated_look)
            generated_look_by_character[character_id] = look_id
            report["generated_missing_character_looks"] += 1

        known_look_ids = {
            item.get("id")
            for item in character_looks
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for beat in beats:
            if not isinstance(beat, dict):
                continue
            look_ids = beat.get("look_ids")
            character_ids = beat.get("character_ids")
            if not isinstance(look_ids, list) or not isinstance(character_ids, list):
                continue
            normalized_look_ids = []
            for look_id in look_ids:
                if isinstance(look_id, str) and look_id not in known_look_ids:
                    report["removed_unknown_look_references"] += 1
                    continue
                normalized_look_ids.append(look_id)
            for character_id in character_ids:
                generated_look_id = generated_look_by_character.get(character_id)
                if generated_look_id and generated_look_id not in normalized_look_ids:
                    normalized_look_ids.append(generated_look_id)
            if look_ids != normalized_look_ids:
                beat["look_ids"] = normalized_look_ids
                report["rewritten_beat_look_references"] += 1

    dialogue_ids_by_beat = {beat_no: [] for beat_no in range(1, expected_scene_count + 1)}
    for unit in retained_dialogue_units:
        if not isinstance(unit, dict):
            continue
        beat_no = unit.get("beat_no")
        unit_id = unit.get("id")
        if (
            isinstance(beat_no, int)
            and not isinstance(beat_no, bool)
            and 1 <= beat_no <= expected_scene_count
            and isinstance(unit_id, str)
        ):
            dialogue_ids_by_beat[beat_no].append(unit_id)

    for beat in beats:
        if not isinstance(beat, dict):
            continue
        beat_no = beat.get("beat_no")
        if (
            not isinstance(beat_no, int)
            or isinstance(beat_no, bool)
            or not 1 <= beat_no <= expected_scene_count
        ):
            continue
        canonical_ids = dialogue_ids_by_beat[beat_no]
        if beat.get("dialogue_unit_ids") != canonical_ids:
            beat["dialogue_unit_ids"] = canonical_ids
            report["rewritten_beat_dialogue_references"] += 1

    report["applied"] = any(report[field_name] for field_name in REPAIR_COUNTER_FIELDS)
    return repaired, report


def merge_production_plan_repair_reports(
    *reports,
    provider_schema_repair_call_count=0,
    provider_dialogue_repair_call_count=0,
):
    merged = _empty_repair_report()
    for report in reports:
        if not isinstance(report, dict):
            continue
        merged["applied"] = merged["applied"] or report.get("applied") is True
        for field_name in REPAIR_COUNTER_FIELDS:
            value = report.get(field_name)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                merged[field_name] += value

    bounded_provider_call_count = 1 if provider_schema_repair_call_count else 0
    merged["provider_schema_repair_applied"] = bool(bounded_provider_call_count)
    merged["provider_schema_repair_call_count"] = bounded_provider_call_count
    bounded_dialogue_call_count = 1 if provider_dialogue_repair_call_count else 0
    merged["provider_dialogue_repair_applied"] = bool(bounded_dialogue_call_count)
    merged["provider_dialogue_repair_call_count"] = bounded_dialogue_call_count
    merged["applied"] = (
        merged["applied"]
        or merged["provider_schema_repair_applied"]
        or merged["provider_dialogue_repair_applied"]
    )
    return merged


def _find_by_id(items, item_id):
    return next((item for item in items if item.get("id") == item_id), None)


def _find_many_by_id(items, item_ids):
    item_by_id = {item.get("id"): item for item in items}
    return [item_by_id[item_id] for item_id in item_ids if item_id in item_by_id]


def _anchor_fingerprint(*values):
    normalized = "|".join(" ".join(str(value or "").split()) for value in values)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _compile_prompt_segments(segments, limit):
    prompt_parts = []
    for label, value, value_limit in segments:
        normalized_value = _trim(value, value_limit)
        if not normalized_value:
            continue
        prompt_parts.append(f"{label}：{normalized_value}" if label else normalized_value)
    return _trim("。".join(prompt_parts), limit)


def build_visual_world_model(production_plan, render_fps=30):
    if not isinstance(render_fps, int) or isinstance(render_fps, bool) or render_fps <= 0:
        render_fps = 30
    characters = production_plan.get("characters") or []
    character_by_id = {item.get("id"): item for item in characters}
    character_models = []
    for look in production_plan.get("character_looks") or []:
        character = character_by_id.get(look.get("character_id")) or {}
        if not character:
            continue
        canonical_prompt = _trim(
            (
                f"同一位{character.get('name') or '角色'}，{character.get('identity') or ''}，"
                f"{character.get('appearance') or ''}，固定穿着{look.get('wardrobe') or ''}，"
                f"{look.get('hair_makeup') or ''}，标志特征{look.get('signature_features') or ''}，"
                f"固定配色{look.get('color_palette') or ''}"
            ),
            320,
        )
        character_models.append(
            {
                "id": f"model_{look.get('id')}",
                "character_id": character.get("id") or "",
                "look_id": look.get("id") or "",
                "name": character.get("name") or "",
                "identity_anchor": "；".join(
                    part
                    for part in (character.get("identity"), character.get("appearance"))
                    if part
                ),
                "wardrobe_anchor": look.get("wardrobe") or "",
                "face_hair_anchor": look.get("hair_makeup") or "",
                "signature_anchor": look.get("signature_features") or "",
                "palette_anchor": look.get("color_palette") or "",
                "reference_prompt": look.get("reference_prompt") or "",
                "canonical_prompt": canonical_prompt,
                "anchor_fingerprint": _anchor_fingerprint(
                    character.get("id"),
                    look.get("id"),
                    canonical_prompt,
                ),
                "forbidden_changes": [
                    "不得改变年龄、脸型、五官、发型、体态和身份特征。",
                    "未切换 look_id 时不得改变服装、配色和标志性细节。",
                ],
            }
        )

    scene_models = []
    for location in production_plan.get("locations") or []:
        canonical_prompt = _trim(
            (
                f"同一地点{location.get('name') or '场景'}，固定空间结构为{location.get('geography') or ''}，"
                f"固定地标{location.get('visual_anchor') or ''}，时间{location.get('time_of_day') or ''}，"
                f"天气{location.get('weather') or ''}，固定光线{location.get('lighting') or ''}，"
                f"固定配色{location.get('color_palette') or ''}"
            ),
            360,
        )
        scene_models.append(
            {
                "id": f"model_{location.get('id')}",
                "location_id": location.get("id") or "",
                "name": location.get("name") or "",
                "geometry_anchor": location.get("geography") or "",
                "landmark_anchor": location.get("visual_anchor") or "",
                "time_anchor": location.get("time_of_day") or "",
                "weather_anchor": location.get("weather") or "",
                "lighting_anchor": location.get("lighting") or "",
                "palette_anchor": location.get("color_palette") or "",
                "reference_prompt": location.get("reference_prompt") or "",
                "canonical_prompt": canonical_prompt,
                "anchor_fingerprint": _anchor_fingerprint(location.get("id"), canonical_prompt),
                "camera_axis_rule": "相邻镜头保持地理方向、前后景关系和 180 度轴线，除非转场明确改变观察方向。",
                "grounding_rule": "人物脚部、家具、建筑和道具必须落在合理空间表面，不得重叠或穿透。",
            }
        )
    prop_models = []
    for prop in production_plan.get("props") or []:
        canonical_prompt = _trim(
            (
                f"同一件{prop.get('name') or '道具'}，固定外观{prop.get('visual_anchor') or ''}，"
                f"连续性规则{prop.get('continuity_rule') or ''}"
            ),
            240,
        )
        prop_models.append(
            {
                "id": f"model_{prop.get('id')}",
                "prop_id": prop.get("id") or "",
                "name": prop.get("name") or "",
                "owner_character_id": prop.get("owner_character_id") or "",
                "canonical_prompt": canonical_prompt,
                "reference_prompt": prop.get("reference_prompt") or "",
                "continuity_rule": prop.get("continuity_rule") or "",
                "anchor_fingerprint": _anchor_fingerprint(prop.get("id"), canonical_prompt),
            }
        )
    style_anchor = _trim(production_plan.get("visual_style"), 240)
    return {
        "version": "1.1",
        "style_bible": {
            "id": "style_main",
            "aspect_ratio": "9:16",
            "render_medium": "电影预演关键帧",
            "canonical_prompt": style_anchor,
            "anchor_fingerprint": _anchor_fingerprint("style_main", style_anchor),
            "consistency_policy": [
                "所有镜头原样复用同一视觉风格、材质语言、色彩逻辑和成像介质描述。",
                "镜头只改变剧情动作、景别和机位，不重新设计角色、地点或道具。",
                "同一连续镜头组保持时间、天气、光源方向、空间轴线和屏幕运动方向。",
            ],
        },
        "character_models": character_models,
        "scene_models": scene_models,
        "prop_models": prop_models,
        "physical_rules": list(PHYSICAL_REALISM_RULES),
        "logic_rules": list(LOGIC_CONTINUITY_RULES),
        "generation_policy": {
            "strategy": "canonical_assets_plus_shot_delta",
            "canonical_asset_first": True,
            "repeat_anchors_verbatim": True,
            "one_shot_one_action": True,
            "image_reference_mode": "text_only_canonical_anchors",
            "post_generation_visual_review_required": True,
        },
        "frame_policy": {
            "mode": "constant_frame_rate",
            "target_fps": render_fps,
            "normalization_stage": "final_render",
            "shot_state_policy": "previous_end_to_next_start",
        },
    }


def _resolve_shot_scale(scene, is_group_start):
    camera_text = f"{scene.get('camera_direction') or ''} {scene.get('visual_prompt') or ''}"
    scale_markers = (
        (("大特写", "极近特写", "extreme close"), "extreme_close_up"),
        (("特写", "close-up", "close up"), "close_up"),
        (("近景", "medium close"), "medium_close_up"),
        (("中景", "medium shot"), "medium"),
        (("全景", "远景", "wide shot", "long shot"), "wide"),
    )
    for markers, value in scale_markers:
        if any(marker in camera_text for marker in markers):
            return value
    return "establishing_wide" if is_group_start else "medium"


def _resolve_camera_angle(scene):
    camera_text = f"{scene.get('camera_direction') or ''} {scene.get('visual_prompt') or ''}"
    angle_markers = (
        (("俯拍", "鸟瞰", "high angle", "overhead"), "high_angle"),
        (("仰拍", "低角度", "low angle"), "low_angle"),
        (("侧面", "侧拍", "profile"), "profile"),
        (("背面", "背拍", "from behind"), "rear"),
    )
    for markers, value in angle_markers:
        if any(marker in camera_text for marker in markers):
            return value
    return "eye_level"


def build_visual_continuity_plan(scenes, production_plan, visual_world_model):
    character_model_by_look = {
        item.get("look_id"): item
        for item in visual_world_model.get("character_models") or []
    }
    scene_model_by_location = {
        item.get("location_id"): item
        for item in visual_world_model.get("scene_models") or []
    }
    prop_model_by_prop = {
        item.get("prop_id"): item
        for item in visual_world_model.get("prop_models") or []
    }
    continuity_groups = []
    shots = []
    previous_scene = None
    previous_group_key = None
    current_group = None

    for scene_no, scene in enumerate(scenes, start=1):
        location_id = scene.get("location_id") or ""
        look_ids = tuple(sorted(scene.get("look_ids") or []))
        group_key = (location_id, look_ids)
        if current_group is None or group_key != previous_group_key:
            group_id = f"sequence_{len(continuity_groups) + 1:02d}"
            scene_model = scene_model_by_location.get(location_id) or {}
            character_models = [
                character_model_by_look[look_id]
                for look_id in look_ids
                if look_id in character_model_by_look
            ]
            current_group = {
                "id": group_id,
                "scene_nos": [],
                "location_id": location_id,
                "look_ids": list(look_ids),
                "character_model_ids": [
                    item.get("id") for item in character_models if item.get("id")
                ],
                "scene_model_id": scene_model.get("id") or "",
                "anchor_fingerprint": _anchor_fingerprint(
                    scene_model.get("anchor_fingerprint"),
                    *(item.get("anchor_fingerprint") for item in character_models),
                ),
            }
            continuity_groups.append(current_group)
        current_group["scene_nos"].append(scene_no)

        previous_location_id = previous_scene.get("location_id") if previous_scene else ""
        previous_look_ids = set(previous_scene.get("look_ids") or []) if previous_scene else set()
        current_character_ids = set(scene.get("character_ids") or [])
        previous_character_ids = set(previous_scene.get("character_ids") or []) if previous_scene else set()
        if previous_scene is None:
            relationship = "opening"
        elif previous_location_id != location_id:
            relationship = "location_transition"
        elif previous_look_ids != set(look_ids):
            relationship = "look_transition"
        elif current_character_ids & previous_character_ids:
            relationship = "continuous_action"
        else:
            relationship = "same_location_subject_change"

        prop_ids = [
            item.get("prop_id")
            for item in scene.get("prop_states") or []
            if item.get("prop_id")
        ]
        immutable_anchor_ids = [
            *current_group["character_model_ids"],
            *([current_group["scene_model_id"]] if current_group["scene_model_id"] else []),
            *[
                prop_model_by_prop[prop_id].get("id")
                for prop_id in prop_ids
                if prop_id in prop_model_by_prop and prop_model_by_prop[prop_id].get("id")
            ],
        ]
        is_group_start = len(current_group["scene_nos"]) == 1
        shots.append(
            {
                "scene_no": scene_no,
                "continuity_group_id": current_group["id"],
                "relationship_to_previous": relationship,
                "inherits_from_scene_no": scene_no - 1 if previous_scene else None,
                "immutable_anchor_ids": immutable_anchor_ids,
                "visual_delta": _trim(
                    (
                        f"{scene.get('visual_prompt') or ''}；"
                        f"从{scene.get('start_state') or ''}发展到{scene.get('end_state') or ''}"
                    ),
                    700,
                ),
                "composition": {
                    "shot_scale": _resolve_shot_scale(scene, is_group_start),
                    "camera_angle": _resolve_camera_angle(scene),
                    "camera_direction": scene.get("camera_direction") or "",
                    "screen_direction": (
                        "依据场景空间模型建立轴线和主体运动方向"
                        if is_group_start
                        else "继承上一镜轴线、主体屏幕位置和运动方向"
                    ),
                    "transition_match": (
                        previous_scene.get("transition_out") or ""
                        if previous_scene
                        else ""
                    ),
                },
            }
        )
        previous_scene = scene
        previous_group_key = group_key

    return {
        "version": "1.0",
        "strategy": "canonical_assets_then_shot_delta",
        "continuity_groups": continuity_groups,
        "shots": shots,
        "review_policy": {
            "pre_generation_gate": "deterministic",
            "post_generation_gate": "manual_required",
            "required_checks": [
                "角色身份与服装",
                "场景地标与光源方向",
                "道具外观与状态",
                "相邻镜头屏幕方向",
                "肢体结构与接触关系",
            ],
        },
    }


def _build_scene_continuity_contract(
    scene_data,
    scene_no,
    visual_world_model,
    previous_scene_data=None,
):
    look_ids = scene_data.get("look_ids") or []
    location_id = scene_data.get("location_id") or ""
    character_model_ids = [
        item.get("id")
        for item in visual_world_model.get("character_models") or []
        if item.get("look_id") in look_ids
    ]
    scene_model = next(
        (
            item
            for item in visual_world_model.get("scene_models") or []
            if item.get("location_id") == location_id
        ),
        {},
    )
    previous_end_state = (
        previous_scene_data.get("end_state") or ""
        if previous_scene_data
        else ""
    )
    prop_ids = [
        item.get("prop_id")
        for item in scene_data.get("prop_states") or []
        if item.get("prop_id")
    ]
    return {
        "version": "1.0",
        "scene_no": scene_no,
        "previous_scene_no": scene_no - 1 if previous_scene_data else None,
        "previous_end_state": previous_end_state,
        "required_start_state": previous_end_state or scene_data.get("start_state") or "",
        "declared_start_state": scene_data.get("start_state") or "",
        "required_end_state": scene_data.get("end_state") or "",
        "character_model_ids": character_model_ids,
        "scene_model_id": scene_model.get("id") or "",
        "allowed_entity_ids": [
            *(scene_data.get("character_ids") or []),
            *look_ids,
            *prop_ids,
            *([location_id] if location_id else []),
        ],
        "physical_rules": visual_world_model.get("physical_rules") or [],
        "logic_rules": visual_world_model.get("logic_rules") or [],
    }


def _build_audio_script(dialogue_units):
    if not dialogue_units:
        return {
            "text": "",
            "subtitle_text": "",
            "speaker_id": "",
            "kind": "",
            "emotion": "",
            "voice_profile_id": "",
            "pause_after_ms": 0,
            "target_duration_ms": 0,
        }
    return {
        "text": " ".join(item.get("text") or "" for item in dialogue_units).strip(),
        "subtitle_text": "\n".join(item.get("subtitle_text") or "" for item in dialogue_units).strip(),
        "speaker_id": dialogue_units[0].get("speaker_id") or "",
        "kind": dialogue_units[0].get("kind") or "",
        "emotion": dialogue_units[0].get("emotion") or "",
        "voice_profile_id": dialogue_units[0].get("voice_profile_id") or "",
        "pause_after_ms": sum(item.get("pause_after_ms") or 0 for item in dialogue_units),
        "target_duration_ms": sum(item.get("target_duration_ms") or 0 for item in dialogue_units),
    }


def build_scene_agent_metadata(
    scene_data,
    production_plan,
    scene_no,
    previous_scene_data=None,
    visual_world_model=None,
):
    visual_world_model = visual_world_model or build_visual_world_model(production_plan)
    continuity_contract = _build_scene_continuity_contract(
        scene_data,
        scene_no,
        visual_world_model,
        previous_scene_data,
    )
    visual_continuity_plan = visual_world_model.get("visual_continuity_plan") or {}
    shot_plan = next(
        (
            item
            for item in visual_continuity_plan.get("shots") or []
            if item.get("scene_no") == scene_no
        ),
        None,
    )
    if shot_plan is None:
        shot_plan = {
            "scene_no": scene_no,
            "continuity_group_id": f"sequence_{scene_no:02d}",
            "relationship_to_previous": "continuous_action" if previous_scene_data else "opening",
            "inherits_from_scene_no": scene_no - 1 if previous_scene_data else None,
            "immutable_anchor_ids": [
                *(continuity_contract.get("character_model_ids") or []),
                *(
                    [continuity_contract.get("scene_model_id")]
                    if continuity_contract.get("scene_model_id")
                    else []
                ),
            ],
            "visual_delta": _trim(
                (
                    f"{scene_data.get('visual_prompt') or ''}；"
                    f"从{scene_data.get('start_state') or ''}发展到{scene_data.get('end_state') or ''}"
                ),
                700,
            ),
            "composition": {
                "shot_scale": _resolve_shot_scale(scene_data, not previous_scene_data),
                "camera_angle": _resolve_camera_angle(scene_data),
                "camera_direction": scene_data.get("camera_direction") or "",
                "screen_direction": (
                    "继承上一镜轴线、主体屏幕位置和运动方向"
                    if previous_scene_data
                    else "依据场景空间模型建立轴线和主体运动方向"
                ),
                "transition_match": (
                    previous_scene_data.get("transition_out") or ""
                    if previous_scene_data
                    else ""
                ),
            },
        }
    characters = production_plan.get("characters") or []
    character_looks = production_plan.get("character_looks") or []
    locations = production_plan.get("locations") or []
    props = production_plan.get("props") or []
    dialogue_units = production_plan.get("dialogue_units") or []
    character_ids = scene_data.get("character_ids") or []
    look_ids = scene_data.get("look_ids") or []
    dialogue_unit_ids = scene_data.get("dialogue_unit_ids") or []
    location_id = scene_data.get("location_id") or ""
    prop_states = scene_data.get("prop_states") or []

    character_reference_anchors = []
    for look in _find_many_by_id(character_looks, look_ids):
        character = _find_by_id(characters, look.get("character_id")) or {}
        if not character:
            continue
        character_reference_anchors.append(
            f"{character.get('name', '')}：{look.get('reference_prompt', '')}"
        )

    location = _find_by_id(locations, location_id) or {}
    prop_state_by_id = {item.get("prop_id"): item.get("state") or "" for item in prop_states}
    prop_anchors = []
    prop_reference_anchors = []
    for prop in _find_many_by_id(props, list(prop_state_by_id)):
        prop_anchors.append(
            f"{prop.get('name', '')}：{prop.get('visual_anchor', '')}，状态为{prop_state_by_id.get(prop.get('id'), '')}"
        )
        prop_reference_anchors.append(
            f"{prop.get('name', '')}：{prop.get('reference_prompt', '')}，当前状态{prop_state_by_id.get(prop.get('id'), '')}"
        )

    character_model_by_id = {
        item.get("id"): item
        for item in visual_world_model.get("character_models") or []
    }
    scene_model_by_id = {
        item.get("id"): item
        for item in visual_world_model.get("scene_models") or []
    }
    prop_model_by_prop_id = {
        item.get("prop_id"): item
        for item in visual_world_model.get("prop_models") or []
    }
    canonical_character_anchors = [
        character_model_by_id[model_id].get("canonical_prompt") or ""
        for model_id in continuity_contract.get("character_model_ids") or []
        if model_id in character_model_by_id
    ]
    canonical_scene_model = scene_model_by_id.get(
        continuity_contract.get("scene_model_id")
    ) or {}
    canonical_prop_anchors = [
        (
            f"{prop_model_by_prop_id[prop_id].get('canonical_prompt') or ''}，"
            f"本镜状态{prop_state_by_id.get(prop_id) or ''}"
        )
        for prop_id in prop_state_by_id
        if prop_id in prop_model_by_prop_id
    ]
    if not canonical_character_anchors:
        canonical_character_anchors = character_reference_anchors
    canonical_scene_anchor = (
        canonical_scene_model.get("canonical_prompt")
        or location.get("reference_prompt")
        or location_anchor
    )
    if not canonical_prop_anchors:
        canonical_prop_anchors = prop_reference_anchors

    resolved_dialogue_units = _find_many_by_id(dialogue_units, dialogue_unit_ids)
    audio_script = _build_audio_script(resolved_dialogue_units)
    location_anchor = (
        f"{location.get('name', '')}，{location.get('geography', '')}，{location.get('visual_anchor', '')}，"
        f"{location.get('time_of_day', '')}{location.get('weather', '')}，{location.get('lighting', '')}"
        if location
        else ""
    )
    style_bible = visual_world_model.get("style_bible") or {}
    state_anchor = (
        f"{continuity_contract.get('required_start_state') or ''} → "
        f"{continuity_contract.get('required_end_state') or ''}"
    )
    relationship_labels = {
        "opening": "建立连续镜头组的角色、场景、光线和屏幕方向基准",
        "continuous_action": "直接承接上一镜动作、构图轴线、主体位置和光线",
        "same_location_subject_change": "保持同一场景构图轴线，切换到已声明主体",
        "location_transition": "按转场进入新地点，重新建立场景轴线但保持角色身份",
        "look_transition": "仅按已声明形象版本变化，角色身份和场景关系不变",
    }
    relationship_anchor = relationship_labels.get(
        shot_plan.get("relationship_to_previous"),
        "保持与上一镜可见元素连续",
    )
    if shot_plan.get("inherits_from_scene_no"):
        relationship_anchor = (
            f"承接分镜{shot_plan['inherits_from_scene_no']}；{relationship_anchor}；"
            f"上一镜结束状态{continuity_contract.get('previous_end_state') or ''}"
        )
    composition = shot_plan.get("composition") or {}
    composition_anchor = "，".join(
        part
        for part in (
            composition.get("shot_scale") or "",
            composition.get("camera_angle") or "",
            composition.get("camera_direction") or "",
            composition.get("screen_direction") or "",
            (
                f"转场匹配{composition.get('transition_match')}"
                if composition.get("transition_match")
                else ""
            ),
        )
        if part
    )
    physical_guard = "肢体完整、双脚落地、接触清楚，禁止人物/衣物/道具互相穿透，动作符合重力与惯性"
    logic_guard = "只出现已绑定实体，不无因瞬移，不凭空增删或复制人物与道具"
    video_prompt_parts = (
        f"物理约束：{physical_guard}",
        f"逻辑约束：{logic_guard}",
        f"风格：{_trim(production_plan.get('visual_style'), 40)}",
        f"角色固定：{_trim('；'.join(canonical_character_anchors), 70)}" if canonical_character_anchors else "",
        f"场景固定：{_trim(canonical_scene_anchor, 50)}" if canonical_scene_anchor else "",
        f"镜头关系：{_trim(relationship_anchor, 55)}",
        f"状态链：{_trim(state_anchor, 65)}",
        f"核心动作：{_trim(scene_data.get('motion_prompt'), 52)}",
        f"运镜：{_trim(composition_anchor, 38)}",
        f"道具固定：{_trim('；'.join(prop_anchors), 28)}" if prop_anchors else "",
        "单一连续镜头，不切换地点，保持面容、服装、空间方向和光线一致",
    )
    image_prompt = _compile_prompt_segments(
        (
            ("", "竖屏9:16电影预演关键帧，单格画面", 28),
            ("视觉圣经", style_bible.get("canonical_prompt") or production_plan.get("visual_style"), 80),
            ("角色不可变", "；".join(canonical_character_anchors), 210),
            ("场景不可变", canonical_scene_anchor, 125),
            ("道具不可变", "；".join(canonical_prop_anchors), 65),
            ("镜头关系", relationship_anchor, 80),
            ("本镜仅变化", shot_plan.get("visual_delta") or scene_data.get("visual_prompt"), 145),
            ("构图执行", composition_anchor, 75),
            (
                "硬约束",
                (
                    f"{physical_guard}；{logic_guard}；"
                    "面容、服装、道具结构、空间方向和光线不得漂移，不添加文字、水印、边框或分格"
                ),
                80,
            ),
        ),
        980,
    )
    video_prompt = "。".join(part for part in video_prompt_parts if part)
    anchor_fingerprint = _anchor_fingerprint(
        style_bible.get("anchor_fingerprint"),
        *(
            character_model_by_id[model_id].get("anchor_fingerprint")
            for model_id in continuity_contract.get("character_model_ids") or []
            if model_id in character_model_by_id
        ),
        canonical_scene_model.get("anchor_fingerprint"),
        *(
            prop_model_by_prop_id[prop_id].get("anchor_fingerprint")
            for prop_id in prop_state_by_id
            if prop_id in prop_model_by_prop_id
        ),
        shot_plan.get("continuity_group_id"),
    )

    return {
        "beat_no": scene_no,
        "story_function": scene_data.get("story_function") or "",
        "location_id": location_id,
        "character_ids": character_ids,
        "look_ids": look_ids,
        "prop_states": prop_states,
        "dialogue_unit_ids": dialogue_unit_ids,
        "start_state": scene_data.get("start_state") or "",
        "end_state": scene_data.get("end_state") or "",
        "continuity_anchor": scene_data.get("continuity_anchor") or "",
        "transition_out": scene_data.get("transition_out") or "",
        "motion_prompt": scene_data.get("motion_prompt") or "",
        "continuity_contract": continuity_contract,
        "visual_plan": shot_plan,
        "audio_script": audio_script,
        "prompt_adapter": {
            "version": "2.2",
            "strategy": "canonical_assets_plus_shot_delta",
            "targets": ["image_asset", "video_clip"],
            "image_prompt": image_prompt,
            "video_prompt": _trim(video_prompt, 460),
            "negative_prompt": "多余肢体、面部变形、身份漂移、服装突变、身体穿模、衣物穿插、道具穿透、脚部悬空、无因瞬移、实体复制",
            "anchor_fingerprint": anchor_fingerprint,
            "frame_policy": visual_world_model.get("frame_policy") or {},
            "reference_entities": {
                "character_ids": character_ids,
                "look_ids": look_ids,
                "location_id": location_id,
                "prop_ids": list(prop_state_by_id),
                "character_model_ids": continuity_contract.get("character_model_ids") or [],
                "scene_model_id": continuity_contract.get("scene_model_id") or "",
            },
        },
    }


def build_quality_report(
    scenes,
    production_plan,
    duration_target,
    clip_duration_seconds,
    provider_call_count=2,
    visual_world_model=None,
    render_fps=30,
):
    visual_world_model = visual_world_model or build_visual_world_model(production_plan, render_fps)
    visual_continuity_plan = (
        visual_world_model.get("visual_continuity_plan")
        or build_visual_continuity_plan(scenes, production_plan, visual_world_model)
    )
    issues = []
    score = 100
    generated_duration = sum(scene.get("duration_seconds") or 0 for scene in scenes)
    overlong_scenes = 0
    state_link_count = 0
    unexplained_look_changes = 0
    physical_logic_risk_scenes = 0

    if generated_duration != duration_target:
        issues.append(
            {
                "code": "duration_mismatch",
                "severity": "error",
                "scene_no": None,
                "message": f"分镜总时长为 {generated_duration} 秒，与目标 {duration_target} 秒不一致。",
            }
        )
        score -= 25

    known_locations = {item.get("id") for item in production_plan.get("locations") or []}
    known_characters = {item.get("id") for item in production_plan.get("characters") or []}
    look_by_id = {item.get("id"): item for item in production_plan.get("character_looks") or []}
    known_props = {item.get("id") for item in production_plan.get("props") or []}
    dialogue_by_id = {item.get("id"): item for item in production_plan.get("dialogue_units") or []}
    for index, scene in enumerate(scenes, start=1):
        duration = scene.get("duration_seconds") or 0
        if duration > clip_duration_seconds:
            overlong_scenes += 1
            issues.append(
                {
                    "code": "clip_duration_gap",
                    "severity": "warning",
                    "scene_no": index,
                    "message": (
                        f"镜头时长 {duration} 秒超过当前视频模型 {clip_duration_seconds} 秒输出，"
                        "成片可能需要补帧。"
                    ),
                }
            )
            score -= 4

        prompt_text = f"{scene.get('visual_prompt', '')} {scene.get('motion_prompt', '')}"
        if any(marker in prompt_text for marker in MULTI_SCENE_MARKERS):
            issues.append(
                {
                    "code": "multiple_scenes_in_shot",
                    "severity": "warning",
                    "scene_no": index,
                    "message": "单个镜头包含疑似地点或时间切换，建议拆分为独立镜头。",
                }
            )
            score -= 6

        if any(marker in prompt_text for marker in PHYSICAL_RISK_MARKERS):
            physical_logic_risk_scenes += 1
            issues.append(
                {
                    "code": "physical_logic_risk",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头描述包含肢体、接触或穿透异常，必须修改后才能进入素材生成。",
                }
            )
            score -= 15

        if scene.get("location_id") not in known_locations:
            issues.append(
                {
                    "code": "unknown_location",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头引用了连续性设定中不存在的场景。",
                }
            )
            score -= 15

        unknown_characters = set(scene.get("character_ids") or []) - known_characters
        if unknown_characters:
            issues.append(
                {
                    "code": "unknown_character",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头引用了连续性设定中不存在的角色。",
                }
            )
            score -= 15
        if len(scene.get("character_ids") or []) > 3:
            issues.append(
                {
                    "code": "crowded_storyboard_frame",
                    "severity": "warning",
                    "scene_no": index,
                    "message": "单镜出镜角色超过 3 个，文本生图容易丢失身份锚点，建议拆成反应镜头。",
                }
            )
            score -= 4

        scene_character_ids = set(scene.get("character_ids") or [])
        scene_look_ids = set(scene.get("look_ids") or [])
        unknown_looks = scene_look_ids - set(look_by_id)
        if unknown_looks:
            issues.append(
                {
                    "code": "unknown_character_look",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头引用了制作设定中不存在的角色形象。",
                }
            )
            score -= 15
        elif {look_by_id[item_id].get("character_id") for item_id in scene_look_ids} != scene_character_ids:
            issues.append(
                {
                    "code": "character_look_mismatch",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头中的出镜角色与形象版本没有一一对应。",
                }
            )
            score -= 15

        scene_prop_ids = {item.get("prop_id") for item in scene.get("prop_states") or []}
        if scene_prop_ids - known_props:
            issues.append(
                {
                    "code": "unknown_prop",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头引用了制作设定中不存在的道具。",
                }
            )
            score -= 12

        scene_dialogue_ids = scene.get("dialogue_unit_ids") or []
        if set(scene_dialogue_ids) - set(dialogue_by_id):
            issues.append(
                {
                    "code": "unknown_dialogue_unit",
                    "severity": "error",
                    "scene_no": index,
                    "message": "镜头引用了制作设定中不存在的台词单元。",
                }
            )
            score -= 12
        else:
            scene_dialogues = [dialogue_by_id[item_id] for item_id in scene_dialogue_ids]
            planned_audio_ms = sum(
                (item.get("target_duration_ms") or 0) + (item.get("pause_after_ms") or 0)
                for item in scene_dialogues
            )
            if planned_audio_ms > duration * 1000:
                issues.append(
                    {
                        "code": "dialogue_timing_overflow",
                        "severity": "error",
                        "scene_no": index,
                        "message": "镜头台词目标时长超过画面时长，旁白将被截断或挤压。",
                    }
                )
                score -= 12
            dialogue_text_length = len("".join(item.get("text") or "" for item in scene_dialogues).replace(" ", ""))
            if dialogue_text_length > max(8, duration * 5):
                issues.append(
                    {
                        "code": "dialogue_density_high",
                        "severity": "warning",
                        "scene_no": index,
                        "message": "镜头台词密度偏高，建议缩短文本以保持配音清晰。",
                    }
                )
                score -= 4

        if index < len(scenes) and not scene.get("transition_out"):
            issues.append(
                {
                    "code": "missing_transition",
                    "severity": "warning",
                    "scene_no": index,
                    "message": "镜头缺少通向下一镜的动作或画面衔接说明。",
                }
            )
            score -= 3

        if index > 1:
            previous_scene = scenes[index - 2]
            if previous_scene.get("end_state") and scene.get("start_state"):
                state_link_count += 1
            previous_look_by_character = {
                look_by_id[look_id].get("character_id"): look_id
                for look_id in previous_scene.get("look_ids") or []
                if look_id in look_by_id
            }
            current_look_by_character = {
                look_by_id[look_id].get("character_id"): look_id
                for look_id in scene.get("look_ids") or []
                if look_id in look_by_id
            }
            changed_look_characters = {
                character_id
                for character_id in set(previous_look_by_character) & set(current_look_by_character)
                if previous_look_by_character[character_id] != current_look_by_character[character_id]
            }
            transition_text = (
                f"{previous_scene.get('transition_out', '')} {scene.get('start_state', '')}"
            )
            if changed_look_characters and not any(marker in transition_text for marker in LOOK_CHANGE_MARKERS):
                unexplained_look_changes += 1
                issues.append(
                    {
                        "code": "unexplained_character_look_change",
                        "severity": "warning",
                        "scene_no": index,
                        "message": "相邻镜头中的角色形象发生变化，但状态链没有说明换装或时间变化。",
                    }
                )
                score -= 5

    issues.append(
        {
            "code": "visual_semantic_review_required",
            "severity": "warning",
            "scene_no": None,
            "message": "文本连续性门禁不能证明生成像素一致；静态图需复核身份、场景、道具和构图，动态画面还需复核肢体、接触与运动常理。",
        }
    )

    score = max(0, score)
    has_errors = any(issue["severity"] == "error" for issue in issues)
    continuity_groups = visual_continuity_plan.get("continuity_groups") or []
    continuity_shots = visual_continuity_plan.get("shots") or []
    return {
        "status": "passed" if not has_errors and score >= 80 else "needs_review",
        "score": score,
        "issues": issues,
        "metrics": {
            "scene_count": len(scenes),
            "duration_target": duration_target,
            "generated_duration": generated_duration,
            "video_clip_duration": clip_duration_seconds,
            "scenes_over_clip_duration": overlong_scenes,
            "provider_call_count": provider_call_count,
            "render_target_fps": (visual_world_model.get("frame_policy") or {}).get("target_fps", render_fps),
            "state_link_count": state_link_count,
            "unexplained_look_changes": unexplained_look_changes,
            "physical_logic_risk_scenes": physical_logic_risk_scenes,
            "visual_prompt_strategy": visual_continuity_plan.get("strategy") or "",
            "continuity_group_count": len(continuity_groups),
            "linked_shot_count": sum(
                bool(item.get("inherits_from_scene_no"))
                for item in continuity_shots
            ),
            "character_model_count": len(visual_world_model.get("character_models") or []),
            "scene_model_count": len(visual_world_model.get("scene_models") or []),
            "prop_model_count": len(visual_world_model.get("prop_models") or []),
            "character_count": len(production_plan.get("characters") or []),
            "character_look_count": len(production_plan.get("character_looks") or []),
            "location_count": len(production_plan.get("locations") or []),
            "prop_count": len(production_plan.get("props") or []),
            "dialogue_unit_count": len(production_plan.get("dialogue_units") or []),
        },
    }


def build_workflow_record(
    production_plan,
    scenes,
    duration_target,
    clip_duration_seconds,
    model,
    stage_usage,
    repair_report=None,
    provider_call_count=None,
    visual_world_model=None,
    render_fps=30,
):
    repair_report = {**_empty_repair_report(), **(repair_report or {})}
    provider_schema_repair_applied = repair_report["provider_schema_repair_applied"] is True
    provider_dialogue_repair_applied = repair_report["provider_dialogue_repair_applied"] is True
    local_repair_applied = any(repair_report.get(field_name, 0) > 0 for field_name in REPAIR_COUNTER_FIELDS)
    if not isinstance(provider_call_count, int) or isinstance(provider_call_count, bool):
        provider_call_count = (
            2
            + int(provider_schema_repair_applied)
            + int(provider_dialogue_repair_applied)
        )
    visual_world_model = deepcopy(
        visual_world_model or build_visual_world_model(production_plan, render_fps)
    )
    visual_world_model["visual_continuity_plan"] = (
        visual_world_model.get("visual_continuity_plan")
        or build_visual_continuity_plan(scenes, production_plan, visual_world_model)
    )
    quality_report = build_quality_report(
        scenes,
        production_plan,
        duration_target,
        clip_duration_seconds,
        provider_call_count=provider_call_count,
        visual_world_model=visual_world_model,
        render_fps=render_fps,
    )
    stages = [
        {
            "id": "story_architect",
            "label": "制作设定编排",
            "executor": "provider",
            "status": "succeeded",
            "model": model,
            "usage": stage_usage.get("story_architect") or {},
            "subagents": [
                {"id": "story_breakdown", "label": "剧情拆解"},
                {"id": "character_breakdown", "label": "角色拆解"},
                {"id": "appearance_design", "label": "形象拆解"},
                {"id": "location_design", "label": "场景拆解"},
                {"id": "prop_continuity", "label": "道具拆解"},
                {"id": "dialogue_editor", "label": "台词拆解"},
            ],
        }
    ]
    if provider_schema_repair_applied:
        stages.append(
            {
                "id": "schema_repair",
                "label": "制作设定结构修复",
                "executor": "provider",
                "status": "succeeded",
                "model": model,
                "usage": stage_usage.get("schema_repair") or {},
                "subagents": [{"id": "contract_repair", "label": "结构契约修复"}],
            }
        )
    if provider_dialogue_repair_applied:
        stages.append(
            {
                "id": "dialogue_repair",
                "label": "台词预算精编",
                "executor": "provider",
                "status": "succeeded",
                "model": model,
                "usage": stage_usage.get("dialogue_repair") or {},
                "subagents": [{"id": "dialogue_budget_editor", "label": "台词预算编辑"}],
            }
        )
    stages.extend(
        [
            {
                "id": "schema_guard",
                "label": "制作设定结构规范化",
                "executor": "local",
                "status": "succeeded" if local_repair_applied else "passed",
                "model": "deterministic",
                "usage": {},
                "metrics": repair_report,
            },
            {
                "id": "visual_modeler",
                "label": "人物与场景建模",
                "executor": "local",
                "status": "passed",
                "model": "deterministic",
                "usage": {},
                "metrics": {
                    "character_model_count": len(visual_world_model.get("character_models") or []),
                    "scene_model_count": len(visual_world_model.get("scene_models") or []),
                    "prop_model_count": len(visual_world_model.get("prop_models") or []),
                    "target_fps": (visual_world_model.get("frame_policy") or {}).get("target_fps", render_fps),
                },
                "subagents": [
                    {"id": "style_bible_keeper", "label": "视觉圣经"},
                    {"id": "character_modeler", "label": "人物模型卡"},
                    {"id": "scene_modeler", "label": "场景空间模型"},
                    {"id": "prop_modeler", "label": "道具规范模型"},
                    {"id": "state_ledger", "label": "镜头状态链"},
                    {"id": "physics_supervisor", "label": "物理常理约束"},
                ],
            },
            {
                "id": "shot_director",
                "label": "原子镜头导演",
                "executor": "provider",
                "status": "succeeded",
                "model": model,
                "usage": stage_usage.get("shot_director") or {},
                "metrics": stage_usage.get("shot_director_batches") or {},
                "subagents": [
                    {"id": "continuity_director", "label": "连续性导演"},
                    {"id": "camera_director", "label": "镜头导演"},
                ],
            },
            {
                "id": "visual_sequence_planner",
                "label": "视觉序列规划",
                "executor": "local",
                "status": "passed",
                "model": "deterministic",
                "usage": {},
                "metrics": {
                    "continuity_group_count": len(
                        (visual_world_model.get("visual_continuity_plan") or {}).get(
                            "continuity_groups"
                        )
                        or []
                    ),
                    "linked_shot_count": sum(
                        bool(item.get("inherits_from_scene_no"))
                        for item in (
                            (visual_world_model.get("visual_continuity_plan") or {}).get("shots")
                            or []
                        )
                    ),
                },
                "subagents": [
                    {"id": "continuity_group_editor", "label": "连续镜头分组"},
                    {"id": "shot_relation_editor", "label": "镜头关系拆解"},
                    {"id": "composition_director", "label": "构图与轴线导演"},
                    {"id": "visual_delta_editor", "label": "逐镜视觉差量"},
                ],
            },
            {
                "id": "prompt_adapter",
                "label": "多模态素材适配",
                "executor": "local",
                "status": "succeeded",
                "model": "deterministic",
                "usage": {},
                "subagents": [
                    {"id": "image_prompt_compiler", "label": "静态图提示词编译"},
                    {"id": "motion_prompt_compiler", "label": "运动提示词编译"},
                    {"id": "negative_constraint_compiler", "label": "负面约束编译"},
                ],
            },
            {
                "id": "quality_supervisor",
                "label": "制作一致性质检",
                "executor": "local",
                "status": quality_report["status"],
                "model": "deterministic",
                "usage": {},
                "subagents": [
                    {"id": "storyboard_preflight", "label": "静态分镜预检"},
                    {"id": "continuity_gate", "label": "跨镜连续性门禁"},
                    {"id": "visual_review_queue", "label": "生成后视觉复核队列"},
                ],
            },
        ]
    )
    return {
        "version": WORKFLOW_VERSION,
        "mode": WORKFLOW_MODE,
        "generated_at": timezone.now().isoformat(),
        "stages": stages,
        "production_plan": production_plan,
        "visual_world_model": visual_world_model,
        "repair_report": repair_report,
        "quality_report": quality_report,
    }


def mark_workflow_stale(workflow, reason):
    if not workflow:
        return {}
    next_workflow = deepcopy(workflow)
    next_workflow["stale"] = True
    next_workflow["stale_reason"] = reason
    quality_report = next_workflow.setdefault("quality_report", {})
    quality_report["status"] = "stale"
    return next_workflow
