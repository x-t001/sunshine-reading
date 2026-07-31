import type { PaginatedResponse } from "@/types/api";
import type { UserBasic } from "@/types/user";

export type VideoProjectSourceType = "text" | "chapter" | "novel";

export type VideoProjectStatus =
  | "draft"
  | "analyzing"
  | "storyboard_ready"
  | "asset_generating"
  | "rendering"
  | "completed"
  | "failed"
  | "canceled";

export type VideoSceneStatus = "draft" | "ready" | "failed";
export type VideoAssetType = "image" | "video" | "audio" | "subtitle" | "final_video";
export type VideoAssetStatus = "queued" | "running" | "ready" | "stale" | "failed";
export type VideoGenerationJobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";
export type VideoGenerationJobType = "ai_storyboard" | "image_assets" | "video_clips" | "narration_audio" | "render";
export type VideoAssetJobType = Exclude<VideoGenerationJobType, "ai_storyboard" | "render">;
export type VideoStoryGenre = "fantasy" | "urban" | "romance" | "sci_fi" | "mystery" | "history";
export type VideoStoryTone = "cinematic" | "warm" | "suspense" | "high_energy" | "sad";

export type VideoScene = {
  id: number;
  scene_no: number;
  title: string;
  visual_prompt: string;
  narration_text: string;
  subtitle_text: string;
  duration_seconds: number;
  camera_direction: string;
  mood: string;
  agent_metadata: Record<string, unknown>;
  status: VideoSceneStatus;
  failure_reason: string;
  created_at: string;
  updated_at: string;
};

export type VideoAgentWorkflowStage = {
  id: string;
  label: string;
  executor: "provider" | "local";
  status: "succeeded" | "passed" | "needs_review" | "failed" | "stale";
  model: string;
  usage: Record<string, number>;
  metrics?: Record<string, number | boolean | string>;
  subagents?: Array<{
    id: string;
    label: string;
  }>;
};

export type VideoAgentWorkflowIssue = {
  code: string;
  severity: "warning" | "error";
  scene_no: number | null;
  message: string;
};

export type VideoVisualWorldModel = {
  version?: string;
  style_bible?: {
    id?: string;
    aspect_ratio?: string;
    render_medium?: string;
    canonical_prompt?: string;
    anchor_fingerprint?: string;
    consistency_policy?: string[];
  };
  character_models?: Array<{
    id: string;
    character_id: string;
    look_id: string;
    name: string;
    identity_anchor: string;
    wardrobe_anchor: string;
    face_hair_anchor: string;
    signature_anchor: string;
    palette_anchor: string;
    reference_prompt: string;
    canonical_prompt?: string;
    anchor_fingerprint?: string;
    forbidden_changes?: string[];
  }>;
  scene_models?: Array<{
    id: string;
    location_id: string;
    name: string;
    geometry_anchor: string;
    landmark_anchor: string;
    time_anchor: string;
    weather_anchor: string;
    lighting_anchor: string;
    palette_anchor: string;
    reference_prompt: string;
    canonical_prompt?: string;
    anchor_fingerprint?: string;
    camera_axis_rule: string;
    grounding_rule: string;
  }>;
  prop_models?: Array<{
    id: string;
    prop_id: string;
    name: string;
    owner_character_id?: string;
    canonical_prompt?: string;
    reference_prompt?: string;
    continuity_rule?: string;
    anchor_fingerprint?: string;
  }>;
  generation_policy?: {
    strategy?: string;
    canonical_asset_first?: boolean;
    repeat_anchors_verbatim?: boolean;
    one_shot_one_action?: boolean;
    image_reference_mode?: string;
    post_generation_visual_review_required?: boolean;
  };
  visual_continuity_plan?: {
    version?: string;
    strategy?: string;
    continuity_groups?: Array<{
      id: string;
      scene_nos: number[];
      location_id?: string;
      look_ids?: string[];
      character_model_ids?: string[];
      scene_model_id?: string;
      anchor_fingerprint?: string;
    }>;
    shots?: Array<{
      scene_no: number;
      continuity_group_id: string;
      relationship_to_previous: string;
      inherits_from_scene_no?: number | null;
      immutable_anchor_ids?: string[];
      visual_delta?: string;
      composition?: {
        shot_scale?: string;
        camera_angle?: string;
        camera_direction?: string;
        screen_direction?: string;
        transition_match?: string;
      };
    }>;
    review_policy?: {
      pre_generation_gate?: string;
      post_generation_gate?: string;
      required_checks?: string[];
    };
  };
  physical_rules?: string[];
  logic_rules?: string[];
  frame_policy?: {
    mode?: string;
    target_fps?: number;
    normalization_stage?: string;
    shot_state_policy?: string;
  };
};

export type VideoAgentWorkflow = {
  version?: string;
  mode?: string;
  generated_at?: string;
  stale?: boolean;
  stale_reason?: string;
  stages?: VideoAgentWorkflowStage[];
  visual_world_model?: VideoVisualWorldModel;
  production_plan?: {
    logline?: string;
    theme?: string;
    visual_style?: string;
    characters?: Array<{
      id: string;
      name: string;
      story_role?: string;
      identity?: string;
      appearance: string;
      wardrobe?: string;
      behavior: string;
      voice_profile_id?: string;
    }>;
    character_looks?: Array<{
      id: string;
      character_id: string;
      label: string;
      wardrobe: string;
      hair_makeup: string;
      signature_features: string;
      color_palette: string;
      reference_prompt: string;
    }>;
    locations?: Array<{
      id: string;
      name: string;
      geography?: string;
      visual_anchor: string;
      time_of_day?: string;
      weather?: string;
      lighting: string;
      color_palette?: string;
      reference_prompt?: string;
    }>;
    props?: Array<{
      id: string;
      name: string;
      owner_character_id: string;
      visual_anchor: string;
      initial_state: string;
      continuity_rule: string;
      reference_prompt: string;
    }>;
    dialogue_units?: Array<{
      id: string;
      beat_no: number;
      kind: "narration" | "dialogue";
      speaker_id: string;
      text: string;
      subtitle_text: string;
      emotion: string;
      pause_after_ms: number;
      target_duration_ms: number;
      voice_profile_id: string;
    }>;
    beats?: Array<{
      beat_no: number;
      purpose: string;
      action: string;
      outcome: string;
      location_id: string;
      character_ids: string[];
      look_ids?: string[];
      prop_ids?: string[];
      dialogue_unit_ids?: string[];
    }>;
    continuity_rules?: string[];
  };
  repair_report?: {
    version?: string;
    applied?: boolean;
    removed_out_of_range_dialogue_units?: number;
    rewritten_beat_dialogue_references?: number;
    normalized_dialogue_timing_beats?: number;
    normalized_dialogue_timing_units?: number;
    generated_missing_character_looks?: number;
    removed_unknown_look_references?: number;
    rewritten_beat_look_references?: number;
    provider_schema_repair_applied?: boolean;
    provider_schema_repair_call_count?: number;
    provider_dialogue_repair_applied?: boolean;
    provider_dialogue_repair_call_count?: number;
  };
  quality_report?: {
    status?: "passed" | "needs_review" | "stale";
    score?: number;
    issues?: VideoAgentWorkflowIssue[];
    metrics?: Record<string, number>;
  };
};

export type VideoAudioQualityIssue = {
  code: string;
  severity: "warning" | "error";
  message: string;
};

export type VideoAudioQualityReport = {
  version: string;
  status: "passed" | "failed";
  issues: VideoAudioQualityIssue[];
  metrics: {
    duration_seconds?: number;
    sample_rate?: number;
    channels?: number;
    sample_width_bits?: number;
    rms_dbfs?: number;
    peak_dbfs?: number;
    silence_ratio?: number;
    clipping_ratio?: number;
  };
};

export type VideoSpeechQualityReport = {
  version: string;
  status: "passed" | "needs_review";
  source: "glm_asr" | "manual";
  model: string;
  transcript: string;
  similarity: number | null;
  minimum_similarity: number | null;
  provider_asset_id?: string;
  issues: VideoAudioQualityIssue[];
};

export type VideoAudioReview = {
  status: "approved" | "rejected";
  reviewer_id: number | null;
  reviewed_at: string;
};

export type VideoAudioReviewDecision = VideoAudioReview["status"];

export type VideoVisualReviewIssueCode =
  | "identity_drift"
  | "wardrobe_drift"
  | "scene_drift"
  | "prop_state_error"
  | "anatomy_error"
  | "collision_or_clipping"
  | "motion_or_physics_error"
  | "continuity_break"
  | "composition_error"
  | "other";

export type VideoVisualReview = {
  status: "pending" | "passed" | "needs_review" | "rejected";
  mode?: string;
  reason?: string;
  required_checks?: string[];
  issue_codes?: VideoVisualReviewIssueCode[];
  note?: string;
  reviewer_id?: number | null;
  reviewed_at?: string;
};

export type VideoVisualReviewDecision = "approved" | "rejected";

export type VideoTailFrameMetadata = {
  status: "ready" | "unavailable" | "disabled";
  reason?: string;
  source_scene_no?: number;
  mime_type?: string;
  file_size?: number;
  sha256?: string;
  source_video_sha256?: string;
  extractor?: string;
};

export type VideoAssetMetadata = Record<string, unknown> & {
  audio_quality?: VideoAudioQualityReport;
  speech_quality?: VideoSpeechQualityReport;
  audio_review?: VideoAudioReview;
  fps?: number;
  reference_frame_used?: boolean;
  reference_frame_mode?: string;
  reference_frame_asset_id?: number | null;
  reference_frame_source_scene_no?: number | null;
  reference_frame_fallback_reason?: string;
  reference_frame_fallback_reasons?: string[];
  tail_frame?: VideoTailFrameMetadata;
  prompt_strategy?: string;
  prompt_adapter_version?: string;
  anchor_fingerprint?: string;
  continuity_group_id?: string;
  relationship_to_previous?: string;
  inherits_from_scene_no?: number | null;
  reference_mode?: string;
  visual_review?: VideoVisualReview;
};

export type VideoAsset = {
  id: number;
  project_id: number;
  scene_id: number | null;
  asset_type: VideoAssetType;
  status: VideoAssetStatus;
  file_name: string;
  mime_type: string;
  file_size: number;
  provider: string;
  metadata: VideoAssetMetadata;
  failure_reason: string;
  download_url: string;
  created_at: string;
  updated_at: string;
};

export type VideoProjectListItem = {
  id: number;
  owner: Pick<UserBasic, "id" | "username" | "nickname">;
  source_type: VideoProjectSourceType;
  source_novel_id: number | null;
  source_chapter_id: number | null;
  source_title: string;
  title: string;
  style_preset: string;
  duration_target: number;
  aspect_ratio: string;
  status: VideoProjectStatus;
  failure_reason: string;
  scene_count: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type VideoProjectDetail = VideoProjectListItem & {
  summary: string;
  input_text: string;
  source_excerpt_hash: string;
  agent_workflow: VideoAgentWorkflow;
  scenes: VideoScene[];
  assets: VideoAsset[];
};

export type VideoProjectPage = PaginatedResponse<VideoProjectListItem>;

export type VideoSourceChapter = {
  id: number;
  novel_id: number;
  novel_title: string;
  title: string;
  chapter_number: number;
  word_count: number;
  status: string;
  audit_status: string;
  source_access: "public" | "owned" | "admin";
  published_at: string | null;
  updated_at: string;
};

export type VideoSourceChapterPage = PaginatedResponse<VideoSourceChapter>;

export type VideoSourceNovel = {
  id: number;
  title: string;
  author_id: number;
  author_name: string;
  chapter_count: number;
  first_chapter_number: number;
  last_chapter_number: number;
  status: string;
  audit_status: string;
  source_access: "public" | "owned" | "admin";
  updated_at: string;
};

export type VideoSourceNovelPage = PaginatedResponse<VideoSourceNovel>;

export type GetVideoProjectParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  source_type?: VideoProjectSourceType;
  status?: VideoProjectStatus;
};

export type CreateVideoProjectPayload = {
  source_type: "text";
  title?: string;
  input_text: string;
  style_preset?: string;
  duration_target?: number;
  aspect_ratio?: "9:16";
};

export type CreateVideoProjectFromChapterPayload = {
  chapter_id: number;
  title?: string;
  style_preset?: string;
  duration_target?: number;
  aspect_ratio?: "9:16";
};

export type CreateVideoProjectFromNovelPayload = {
  novel_id: number;
  start_chapter_number: number;
  end_chapter_number: number;
  title?: string;
  style_preset?: string;
  duration_target?: number;
  aspect_ratio?: "9:16";
};

export type GetVideoSourceChapterParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
};

export type GetVideoSourceNovelParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
};

export type GenerateVideoProjectStoryboardPayload = {
  scene_count?: number;
};

export type CreateVideoAssetJobPayload = {
  regenerate?: boolean;
  scene_ids?: number[];
};

export type CreateVideoRenderJobPayload = {
  regenerate?: boolean;
  include_narration?: boolean;
  include_subtitles?: boolean;
};

export type VideoGenerationCapabilities = {
  ai_storyboard_configured: boolean;
  ai_storyboard_model: string;
  ai_agent_workflow_available: boolean;
  ai_agent_workflow_version: string;
  local_storyboard_available: boolean;
  durable_storyboard_jobs_available: boolean;
  asset_jobs_available: boolean;
  image_assets_configured: boolean;
  image_assets_model: string;
  image_assets_size: string;
  image_assets_continuity_workflow: boolean;
  image_assets_reference_mode: string;
  image_assets_visual_review_mode: string;
  image_assets_daily_job_limit: number;
  image_assets_daily_jobs_remaining: number;
  visual_review_available: boolean;
  visual_regeneration_daily_scene_limit: number;
  visual_regeneration_daily_scenes_remaining: number;
  visual_regeneration_per_scene_limit: number;
  video_clips_configured: boolean;
  video_clips_model: string;
  video_clips_size: string;
  video_clips_duration_seconds: number;
  video_clips_fps: number;
  video_clips_with_audio: boolean;
  video_clips_reference_frame_enabled: boolean;
  video_clips_previous_tail_frame_enabled: boolean;
  video_clips_previous_tail_frame_available: boolean;
  video_clips_reference_frame_mode: string;
  video_clips_daily_job_limit: number;
  video_clips_daily_jobs_remaining: number;
  narration_audio_configured: boolean;
  narration_audio_model: string;
  narration_audio_voice: string;
  narration_audio_daily_job_limit: number;
  narration_audio_daily_jobs_remaining: number;
  narration_audio_quality_gate: boolean;
  narration_audio_asr_configured: boolean;
  narration_audio_asr_model: string;
  narration_audio_asr_min_similarity: number;
  narration_audio_manual_review: boolean;
  local_render_available: boolean;
  local_render_engine: string;
  local_render_size: string;
  local_render_fps: number;
};

export type VideoGenerationJob = {
  id: number;
  project_id: number;
  job_type: VideoGenerationJobType;
  status: VideoGenerationJobStatus;
  provider: string;
  model_name: string;
  request_payload: GenerateVideoProjectStoryboardPayload | CreateVideoAssetJobPayload | CreateVideoRenderJobPayload;
  attempt_count: number;
  max_attempts: number;
  can_retry: boolean;
  can_resume_provider_task: boolean;
  error_message: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UpdateVideoScenePayload = Partial<
  Pick<
    VideoScene,
    "title" | "visual_prompt" | "narration_text" | "subtitle_text" | "duration_seconds" | "camera_direction" | "mood"
  >
>;

export type GenerateVideoStoryDraftPayload = {
  prompt: string;
  protagonist?: string;
  key_conflict?: string;
  genre?: VideoStoryGenre;
  tone?: VideoStoryTone;
  duration_target?: number;
};

export type VideoStoryDraft = {
  title: string;
  summary: string;
  input_text: string;
  duration_target: number;
  aspect_ratio: "9:16";
  style_preset: string;
  genre: VideoStoryGenre;
  tone: VideoStoryTone;
};
