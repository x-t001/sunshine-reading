import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  CreateVideoProjectPayload,
  CreateVideoProjectFromChapterPayload,
  GenerateVideoProjectStoryboardPayload,
  GenerateVideoStoryDraftPayload,
  GetVideoProjectParams,
  GetVideoSourceChapterParams,
  UpdateVideoScenePayload,
  VideoGenerationCapabilities,
  VideoGenerationJob,
  VideoScene,
  VideoProjectDetail,
  VideoProjectPage,
  VideoStoryDraft,
  VideoSourceChapterPage,
} from "@/types/video-project";

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
  requireLogin("请先登录后再重试 AI 分镜任务。");
  return apiRequest<VideoGenerationJob>(`/video-generation-jobs/${jobId}/retry/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
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
