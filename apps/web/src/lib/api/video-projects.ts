import { ApiRequestError, apiFileRequest, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  CreateVideoProjectPayload,
  CreateVideoProjectFromChapterPayload,
  CreateVideoProjectFromNovelPayload,
  CreateVideoAssetJobPayload,
  CreateVideoRenderJobPayload,
  GenerateVideoProjectStoryboardPayload,
  GenerateVideoStoryDraftPayload,
  GetVideoProjectParams,
  GetVideoSourceChapterParams,
  GetVideoSourceNovelParams,
  UpdateVideoScenePayload,
  VideoGenerationCapabilities,
  VideoGenerationJob,
  VideoAssetJobType,
  VideoAsset,
  VideoAudioReviewDecision,
  VideoVisualReviewDecision,
  VideoVisualReviewIssueCode,
  VideoScene,
  VideoProjectDetail,
  VideoProjectPage,
  VideoStoryDraft,
  VideoSourceChapterPage,
  VideoSourceNovelPage,
} from "@/types/video-project";

const videoAssetJobPathSegments: Record<VideoAssetJobType, "images" | "videos" | "audio"> = {
  image_assets: "images",
  video_clips: "videos",
  narration_audio: "audio",
};

function requireLogin(message = "请先登录后再使用短视频项目。"): void {
  if (!getAccessToken()) {
    throw new ApiRequestError(message, 401);
  }
}

export function getVideoProjects(params: GetVideoProjectParams = {}): Promise<VideoProjectPage> {
  requireLogin("请先登录后再查看短视频项目。");
  return apiRequest<VideoProjectPage>(`/video-projects/${buildQueryString(params)}`);
}

export function getVideoProject(id: number | string): Promise<VideoProjectDetail> {
  requireLogin("请先登录后再查看短视频项目。");
  return apiRequest<VideoProjectDetail>(`/video-projects/${id}/`);
}

export function getVideoGenerationCapabilities(): Promise<VideoGenerationCapabilities> {
  requireLogin("请先登录后再查看短视频生成能力。");
  return apiRequest<VideoGenerationCapabilities>("/video-projects/capabilities/");
}

export function createVideoProject(payload: CreateVideoProjectPayload): Promise<VideoProjectDetail> {
  requireLogin("请先登录后再创建短视频项目。");
  return apiRequest<VideoProjectDetail>("/video-projects/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVideoSourceChapters(params: GetVideoSourceChapterParams = {}): Promise<VideoSourceChapterPage> {
  requireLogin("请先登录后再选择章节来源。");
  return apiRequest<VideoSourceChapterPage>(`/video-source-chapters/${buildQueryString(params)}`);
}

export function createVideoProjectFromChapter(payload: CreateVideoProjectFromChapterPayload): Promise<VideoProjectDetail> {
  requireLogin("请先登录后再从章节创建短视频项目。");
  return apiRequest<VideoProjectDetail>("/video-projects/from-chapter/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getVideoSourceNovels(params: GetVideoSourceNovelParams = {}): Promise<VideoSourceNovelPage> {
  requireLogin("请先登录后再选择小说来源。");
  return apiRequest<VideoSourceNovelPage>(`/video-source-novels/${buildQueryString(params)}`);
}

export function createVideoProjectFromNovel(payload: CreateVideoProjectFromNovelPayload): Promise<VideoProjectDetail> {
  requireLogin("请先登录后再从小说创建短视频项目。");
  return apiRequest<VideoProjectDetail>("/video-projects/from-novel/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateVideoStoryDraft(payload: GenerateVideoStoryDraftPayload): Promise<VideoStoryDraft> {
  requireLogin("请先登录后再生成剧情草稿。");
  return apiRequest<VideoStoryDraft>("/video-projects/story-draft/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteVideoProject(id: number | string): Promise<Record<string, never>> {
  requireLogin("请先登录后再删除短视频项目。");
  return apiRequest<Record<string, never>>(`/video-projects/${id}/`, {
    method: "DELETE",
  });
}

export function generateVideoProjectStoryboard(
  id: number | string,
  payload: GenerateVideoProjectStoryboardPayload = {},
): Promise<VideoProjectDetail> {
  requireLogin("请先登录后再生成短视频分镜。");
  return apiRequest<VideoProjectDetail>(`/video-projects/${id}/storyboard/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateAiVideoProjectStoryboard(
  id: number | string,
  payload: GenerateVideoProjectStoryboardPayload = {},
): Promise<VideoProjectDetail> {
  requireLogin("请先登录后再使用 AI 生成短视频分镜。");
  return apiRequest<VideoProjectDetail>(`/video-projects/${id}/storyboard/ai/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createAiVideoStoryboardJob(
  projectId: number | string,
  payload: GenerateVideoProjectStoryboardPayload = {},
): Promise<VideoGenerationJob> {
  requireLogin("请先登录后再创建 AI 分镜任务。");
  return apiRequest<VideoGenerationJob>(`/video-projects/${projectId}/storyboard/jobs/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getLatestAiVideoStoryboardJob(projectId: number | string): Promise<VideoGenerationJob | null> {
  requireLogin("请先登录后再查看 AI 分镜任务。");
  const result = await apiRequest<Partial<VideoGenerationJob>>(`/video-projects/${projectId}/storyboard/jobs/latest/`);
  return typeof result.id === "number" ? (result as VideoGenerationJob) : null;
}

export function getVideoGenerationJob(jobId: number | string): Promise<VideoGenerationJob> {
  requireLogin("请先登录后再查看 AI 分镜任务。");
  return apiRequest<VideoGenerationJob>(`/video-generation-jobs/${jobId}/`);
}

export function retryVideoGenerationJob(jobId: number | string): Promise<VideoGenerationJob> {
  requireLogin("请先登录后再重试短视频生成任务。");
  return apiRequest<VideoGenerationJob>(`/video-generation-jobs/${jobId}/retry/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function createVideoAssetJob(
  projectId: number | string,
  jobType: VideoAssetJobType,
  payload: CreateVideoAssetJobPayload = {},
): Promise<VideoGenerationJob> {
  requireLogin("请先登录后再创建短视频素材任务。");
  const pathSegment = videoAssetJobPathSegments[jobType];
  return apiRequest<VideoGenerationJob>(`/video-projects/${projectId}/assets/${pathSegment}/jobs/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getLatestVideoAssetJob(
  projectId: number | string,
  jobType: VideoAssetJobType,
): Promise<VideoGenerationJob | null> {
  requireLogin("请先登录后再查看短视频素材任务。");
  const pathSegment = videoAssetJobPathSegments[jobType];
  const result = await apiRequest<Partial<VideoGenerationJob>>(
    `/video-projects/${projectId}/assets/${pathSegment}/jobs/`,
  );
  return typeof result.id === "number" ? (result as VideoGenerationJob) : null;
}

export function createVideoRenderJob(
  projectId: number | string,
  payload: CreateVideoRenderJobPayload = {},
): Promise<VideoGenerationJob> {
  requireLogin("请先登录后再渲染短视频成片。");
  return apiRequest<VideoGenerationJob>(`/video-projects/${projectId}/render/jobs/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getLatestVideoRenderJob(projectId: number | string): Promise<VideoGenerationJob | null> {
  requireLogin("请先登录后再查看成片渲染任务。");
  const result = await apiRequest<Partial<VideoGenerationJob>>(`/video-projects/${projectId}/render/jobs/`);
  return typeof result.id === "number" ? (result as VideoGenerationJob) : null;
}

export function updateVideoScene(
  projectId: number | string,
  sceneId: number | string,
  payload: UpdateVideoScenePayload,
): Promise<VideoScene> {
  requireLogin("请先登录后再编辑短视频分镜。");
  return apiRequest<VideoScene>(`/video-projects/${projectId}/scenes/${sceneId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function generateVideoProjectSubtitles(projectId: number | string): Promise<VideoAsset> {
  requireLogin("请先登录后再生成短视频字幕。");
  return apiRequest<VideoAsset>(`/video-projects/${projectId}/assets/subtitles/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function downloadVideoAsset(assetId: number | string, fallbackFileName = "video-asset.bin") {
  requireLogin("请先登录后再下载短视频素材。");
  return apiFileRequest(`/video-assets/${assetId}/download/`, fallbackFileName);
}

export function reviewVideoAudioAsset(
  assetId: number | string,
  decision: VideoAudioReviewDecision,
): Promise<VideoAsset> {
  requireLogin("请先登录后再确认旁白音频。");
  return apiRequest<VideoAsset>(`/video-assets/${assetId}/audio-review/`, {
    method: "PATCH",
    body: JSON.stringify({ decision }),
  });
}

export function reviewVideoVisualAsset(
  assetId: number | string,
  decision: VideoVisualReviewDecision,
  issueCodes: VideoVisualReviewIssueCode[] = [],
): Promise<VideoAsset> {
  requireLogin("请先登录后再复核画面素材。");
  return apiRequest<VideoAsset>(`/video-assets/${assetId}/visual-review/`, {
    method: "PATCH",
    body: JSON.stringify({ decision, issue_codes: issueCodes }),
  });
}
