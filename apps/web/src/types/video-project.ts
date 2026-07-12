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
export type VideoGenerationJobStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";
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
  status: VideoSceneStatus;
  failure_reason: string;
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
  scenes: VideoScene[];
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

export type GetVideoSourceChapterParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
};

export type GenerateVideoProjectStoryboardPayload = {
  scene_count?: number;
};

export type VideoGenerationCapabilities = {
  ai_storyboard_configured: boolean;
  ai_storyboard_model: string;
  local_storyboard_available: boolean;
  durable_storyboard_jobs_available: boolean;
};

export type VideoGenerationJob = {
  id: number;
  project_id: number;
  job_type: "ai_storyboard";
  status: VideoGenerationJobStatus;
  provider: string;
  model_name: string;
  request_payload: GenerateVideoProjectStoryboardPayload;
  attempt_count: number;
  max_attempts: number;
  can_retry: boolean;
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
