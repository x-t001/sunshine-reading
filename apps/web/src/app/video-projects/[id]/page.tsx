"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  createVideoAssetJob,
  createVideoRenderJob,
  deleteVideoProject,
  createAiVideoStoryboardJob,
  downloadVideoAsset,
  generateVideoProjectStoryboard,
  generateVideoProjectSubtitles,
  getLatestAiVideoStoryboardJob,
  getLatestVideoAssetJob,
  getLatestVideoRenderJob,
  getVideoGenerationCapabilities,
  getVideoGenerationJob,
  getVideoProject,
  reviewVideoAudioAsset,
  reviewVideoVisualAsset,
  retryVideoGenerationJob,
  updateVideoScene,
} from "@/lib/api/video-projects";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel } from "@/lib/utils/format";
import { useAuth } from "@/hooks/useAuth";
import type {
  UpdateVideoScenePayload,
  VideoAsset,
  VideoAssetJobType,
  VideoAudioReviewDecision,
  VideoVisualReviewDecision,
  VideoVisualReviewIssueCode,
  VideoGenerationCapabilities,
  VideoGenerationJob,
  VideoProjectDetail,
  VideoScene,
} from "@/types/video-project";
import VideoAssetPreview from "./VideoAssetPreview";
import VideoAgentWorkflowPanel from "./VideoAgentWorkflowPanel";
import VideoSceneEditor from "./VideoSceneEditor";

const statusLabels: Record<string, string> = {
  draft: "草稿",
  analyzing: "分析中",
  storyboard_ready: "分镜已就绪",
  asset_generating: "素材生成中",
  rendering: "渲染中",
  completed: "已完成",
  failed: "失败",
  canceled: "已取消",
};

const storyboardReadyStatuses = new Set(["draft", "failed", "storyboard_ready", "completed"]);
const assetReadyStatuses = new Set(["storyboard_ready", "completed"]);
const defaultCapabilities: VideoGenerationCapabilities = {
  ai_storyboard_configured: false,
  ai_storyboard_model: "",
  ai_agent_workflow_available: false,
  ai_agent_workflow_version: "",
  local_storyboard_available: true,
  durable_storyboard_jobs_available: false,
  asset_jobs_available: false,
  image_assets_configured: false,
  image_assets_model: "",
  image_assets_size: "",
  image_assets_continuity_workflow: false,
  image_assets_reference_mode: "",
  image_assets_visual_review_mode: "",
  image_assets_daily_job_limit: 0,
  image_assets_daily_jobs_remaining: 0,
  visual_review_available: false,
  visual_regeneration_daily_scene_limit: 0,
  visual_regeneration_daily_scenes_remaining: 0,
  visual_regeneration_per_scene_limit: 0,
  video_clips_configured: false,
  video_clips_model: "",
  video_clips_size: "",
  video_clips_duration_seconds: 0,
  video_clips_fps: 0,
  video_clips_with_audio: false,
  video_clips_reference_frame_enabled: false,
  video_clips_previous_tail_frame_enabled: false,
  video_clips_previous_tail_frame_available: false,
  video_clips_reference_frame_mode: "",
  video_clips_daily_job_limit: 0,
  video_clips_daily_jobs_remaining: 0,
  narration_audio_configured: false,
  narration_audio_model: "",
  narration_audio_voice: "",
  narration_audio_daily_job_limit: 0,
  narration_audio_daily_jobs_remaining: 0,
  narration_audio_quality_gate: false,
  narration_audio_asr_configured: false,
  narration_audio_asr_model: "",
  narration_audio_asr_min_similarity: 0,
  narration_audio_manual_review: true,
  local_render_available: false,
  local_render_engine: "",
  local_render_size: "",
  local_render_fps: 0,
};

const jobStatusLabels: Record<string, string> = {
  queued: "等待处理",
  running: "正在生成",
  succeeded: "生成成功",
  failed: "生成失败",
  canceled: "已取消",
};

const subtitleSourceFields = new Set(["title", "narration_text", "subtitle_text", "duration_seconds"]);
const imageSourceFields = new Set(["title", "visual_prompt", "camera_direction", "mood"]);
const audioSourceFields = new Set(["title", "narration_text", "subtitle_text"]);

const assetStatusLabels: Record<string, string> = {
  queued: "等待处理",
  running: "正在生成",
  ready: "已就绪",
  stale: "需要更新",
  failed: "生成失败",
};

const referenceFrameFallbackLabels: Record<string, string> = {
  disabled: "首帧引用已关闭",
  scene_image_disabled: "本镜静态图引用已关闭，已回退文生视频",
  previous_scene_missing: "缺少上一分镜，已回退本镜静态图",
  previous_video_missing: "上一镜视频未就绪，已回退本镜静态图",
  previous_tail_unavailable: "上一镜尾帧未就绪，已回退本镜静态图",
  previous_tail_path_invalid: "上一镜尾帧路径无效，已回退本镜静态图",
  missing_ready_image: "缺少静态图，已回退文生视频",
  unsupported_image_format: "静态图格式不兼容，已回退文生视频",
  image_file_missing: "静态图文件缺失，已回退文生视频",
  image_file_empty: "静态图为空，已回退文生视频",
  image_file_too_large: "静态图过大，已回退文生视频",
  reference_frame_file_missing: "参考帧文件缺失，已自动降级",
  reference_frame_file_empty: "参考帧文件为空，已自动降级",
  reference_frame_file_too_large: "参考帧文件过大，已自动降级",
  reference_frame_file_invalid: "参考帧文件无效，已自动降级",
  ffmpeg_unavailable: "FFmpeg 不可用，已回退本镜静态图",
  tail_frame_extraction_failed: "上一镜尾帧提取失败，已回退本镜静态图",
};

const tailFrameStatusLabels: Record<string, string> = {
  previous_tail_disabled: "尾帧承接已关闭",
  ffmpeg_unavailable: "FFmpeg 不可用，未提取尾帧",
  tail_frame_path_invalid: "尾帧路径无效",
  tail_frame_extraction_failed: "尾帧提取失败",
};

const visualRelationshipLabels: Record<string, string> = {
  opening: "建立视觉基准",
  continuous_action: "承接上一镜",
  same_location_subject_change: "同场景切换主体",
  location_transition: "地点转场",
  look_transition: "形象转场",
};

function getAssetContinuitySummary(asset: VideoAsset | undefined): string {
  if (!asset) {
    return "";
  }
  const metadata = asset.metadata;
  const summaries: string[] = [];
  if (asset.asset_type === "image") {
    if (metadata.continuity_group_id) {
      summaries.push(`连续组 ${metadata.continuity_group_id.replace("sequence_", "")}`);
    }
    const relationship = visualRelationshipLabels[metadata.relationship_to_previous || ""];
    if (relationship) {
      summaries.push(relationship);
    }
    if (metadata.reference_mode === "text_only_canonical_anchors") {
      summaries.push("规范文本锚点");
    }
    if (metadata.visual_review?.status === "passed") {
      summaries.push("视觉复核通过");
    } else if (metadata.visual_review?.status === "rejected") {
      summaries.push("需要重拍");
    } else {
      summaries.push("待视觉复核");
    }
    return summaries.join(" · ");
  }
  if (asset.asset_type !== "video") {
    return "";
  }
  const fallbackReasons = metadata.reference_frame_fallback_reasons || [];
  if (metadata.reference_frame_used) {
    if (metadata.reference_frame_mode === "previous_scene_tail_base64") {
      const sourceSceneNo = metadata.reference_frame_source_scene_no;
      summaries.push(sourceSceneNo ? `承接分镜 ${sourceSceneNo} 尾帧` : "承接上一镜尾帧");
    } else {
      summaries.push(fallbackReasons.length > 0 ? "本镜静态图首帧（尾帧不可用）" : "本镜静态图首帧");
    }
  } else {
    const fallbackReason = metadata.reference_frame_fallback_reason || "";
    summaries.push(referenceFrameFallbackLabels[fallbackReason] || "文生视频");
  }

  const tailFrame = metadata.tail_frame;
  if (tailFrame?.status === "ready") {
    summaries.push("已提取尾帧");
  } else if (tailFrame?.status === "unavailable") {
    summaries.push(tailFrameStatusLabels[tailFrame.reason || ""] || "尾帧未提取");
  }
  if (metadata.visual_review?.status === "passed") {
    summaries.push("视觉复核通过");
  } else if (metadata.visual_review?.status === "rejected") {
    summaries.push("需要重拍");
  } else {
    summaries.push("待视觉复核");
  }
  return summaries.join(" · ");
}

function isActiveJob(job: VideoGenerationJob | null): boolean {
  return job?.status === "queued" || job?.status === "running";
}

function sceneRequiresNarration(scene: VideoScene): boolean {
  const audioScript = scene.agent_metadata.audio_script;
  if (audioScript && typeof audioScript === "object" && "text" in audioScript) {
    const text = (audioScript as { text?: unknown }).text;
    return typeof text === "string" && text.trim().length > 0;
  }
  return (scene.narration_text || scene.subtitle_text || scene.title).trim().length > 0;
}

function isNarrationRenderApproved(asset: VideoAsset): boolean {
  if (asset.metadata.audio_quality?.status !== "passed") {
    return false;
  }
  if (asset.metadata.audio_review?.status === "rejected") {
    return false;
  }
  return asset.metadata.audio_review?.status === "approved" || asset.metadata.speech_quality?.status === "passed";
}

function isVisualRenderApproved(asset: VideoAsset): boolean {
  return asset.metadata.visual_review?.status === "passed";
}

function formatFileSize(fileSize: number): string {
  if (fileSize < 1024) {
    return `${fileSize} B`;
  }
  if (fileSize >= 1024 * 1024) {
    return `${(fileSize / 1024 / 1024).toFixed(1)} MB`;
  }
  return `${(fileSize / 1024).toFixed(1)} KB`;
}

type AssetJobBlockProps = {
  title: string;
  description: string;
  assetType: "image" | "video" | "audio";
  jobType: VideoAssetJobType;
  scenes: VideoScene[];
  assets: VideoAsset[];
  job: VideoGenerationJob | null;
  configured: boolean;
  providerSummary: string;
  dailyLimit: number;
  dailyRemaining: number;
  canGenerate: boolean;
  submitting: boolean;
  downloadingAssetId: number | null;
  reviewingAudioAssetId?: number | null;
  reviewingVisualAssetId?: number | null;
  regeneratingSceneId?: number | null;
  visualRegenerationRemaining?: number;
  onGenerate: (jobType: VideoAssetJobType) => void;
  onDownload: (asset: VideoAsset) => void;
  onAudioReview?: (asset: VideoAsset, decision: VideoAudioReviewDecision) => void;
  onVisualReview?: (
    asset: VideoAsset,
    decision: VideoVisualReviewDecision,
    issueCodes?: VideoVisualReviewIssueCode[],
  ) => void;
  onRegenerateScene?: (jobType: VideoAssetJobType, scene: VideoScene) => void;
};

function AssetJobBlock({
  title,
  description,
  assetType,
  jobType,
  scenes,
  assets,
  job,
  configured,
  providerSummary,
  dailyLimit,
  dailyRemaining,
  canGenerate,
  submitting,
  downloadingAssetId,
  reviewingAudioAssetId = null,
  reviewingVisualAssetId = null,
  regeneratingSceneId = null,
  visualRegenerationRemaining = 0,
  onGenerate,
  onDownload,
  onAudioReview,
  onVisualReview,
  onRegenerateScene,
}: AssetJobBlockProps) {
  const assetScenes = assetType === "audio" ? scenes.filter(sceneRequiresNarration) : scenes;
  const assetSceneIds = new Set(assetScenes.map((scene) => scene.id));
  const relevantAssets = assets.filter((asset) => asset.scene_id !== null && assetSceneIds.has(asset.scene_id));
  const readyCount = relevantAssets.filter((asset) => asset.status === "ready").length;
  const failedCount = relevantAssets.filter((asset) => asset.status === "failed").length;
  const staleCount = relevantAssets.filter((asset) => asset.status === "stale").length;
  const silentCount = scenes.length - assetScenes.length;
  const noNarration = assetType === "audio" && assetScenes.length === 0;
  const active = isActiveJob(job);
  const retrying = job?.status === "failed" && job.can_retry;
  const resumingProviderTask = retrying && job.can_resume_provider_task;
  const allReady = scenes.length > 0 && readyCount === assetScenes.length;
  const quotaAvailable = retrying || dailyRemaining > 0;
  const buttonDisabled = submitting || active || !configured || !canGenerate || !quotaAvailable || noNarration;
  const baseStatusSummary = noNarration
    ? `${silentCount} 个静默镜头，无需旁白`
    : active && job
      ? jobStatusLabels[job.status] || job.status
      : allReady
        ? `${readyCount}/${assetScenes.length} 个分镜已就绪`
        : failedCount > 0
          ? `${failedCount} 个失败，${readyCount} 个已就绪`
          : staleCount > 0
            ? `${staleCount} 个需要更新，${readyCount} 个已就绪`
            : relevantAssets.length > 0
              ? `${readyCount}/${assetScenes.length} 个分镜已就绪`
              : "尚未生成";
  const statusSummary = assetType === "audio" && silentCount > 0 && !noNarration
    ? `${baseStatusSummary} · ${silentCount} 个静默镜头`
    : baseStatusSummary;
  const buttonLabel = submitting
    ? "提交中..."
    : active
      ? job?.status === "queued"
        ? "任务已排队"
        : "素材生成中..."
      : retrying
        ? resumingProviderTask
          ? "恢复并继续"
          : "重试失败任务"
        : noNarration
          ? "无需生成旁白"
          : allReady
            ? `重新生成${title}`
            : relevantAssets.length > 0
              ? `继续生成${title}`
              : `生成${title}`;

  return (
    <div className="py-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-zinc-900">{title}</p>
          <p className="mt-1 text-xs leading-5 text-zinc-500">{description}</p>
          <p className={`mt-1 text-xs ${failedCount > 0 || job?.status === "failed" ? "text-red-700" : staleCount > 0 ? "text-amber-700" : "text-zinc-600"}`}>
            {statusSummary}
            {configured && providerSummary ? ` · ${providerSummary}` : ""}
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            {configured
              ? `本地每日任务额度 ${dailyRemaining}/${dailyLimit}${
                assetType === "image" || assetType === "video"
                  ? ` · 局部重拍剩余 ${visualRegenerationRemaining}`
                  : ""
              }`
              : "服务端尚未配置此素材服务"}
          </p>
        </div>
        <button
          className="self-start rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
          type="button"
          disabled={buttonDisabled}
          onClick={() => onGenerate(jobType)}
        >
          {buttonLabel}
        </button>
      </div>

      {job ? (
        <div className="mt-3 flex flex-col gap-1 border-t border-zinc-100 pt-3 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
          <p>
            任务 #{job.id} · {jobStatusLabels[job.status] || job.status}
          </p>
          <p>
            尝试 {job.attempt_count}/{job.max_attempts}
            {job.model_name ? ` · ${job.model_name}` : ""}
          </p>
        </div>
      ) : null}
      {job?.status === "failed" && job.error_message ? (
        <div className="mt-2 space-y-1 text-xs text-red-700">
          <p>{job.error_message}</p>
          {job.error_message.includes("HTTP 429") ? (
            <p className="text-amber-700">
              请先检查智谱账户余额、API Key 类型、当前模型权限和请求频率，处理后再重试。
            </p>
          ) : null}
          {job.can_resume_provider_task ? (
            <p className="text-amber-700">
              已保存外部任务编号；恢复时会继续查询原任务，不会重复提交当前超时镜头。
            </p>
          ) : null}
        </div>
      ) : null}

      {assets.length > 0 ? (
        <div className="mt-3 divide-y divide-zinc-100 border-t border-zinc-100">
          {scenes.map((scene) => {
            const asset = assets.find((item) => item.scene_id === scene.id);
            const silentNarration = assetType === "audio" && !sceneRequiresNarration(scene);
            const continuitySummary = getAssetContinuitySummary(asset);
            const needsVisualRegeneration = Boolean(
              asset
                && (assetType === "image" || assetType === "video")
                && asset.status === "ready"
                && asset.metadata.visual_review?.status === "rejected",
            );
            return (
              <div className="grid gap-3 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(180px,2fr)_auto] sm:items-center" key={scene.id}>
                <div>
                  <p className="text-xs font-medium text-zinc-800">
                    分镜 {scene.scene_no} · {scene.title || "未命名"}
                  </p>
                  <p className={`mt-1 text-xs ${asset?.status === "failed" ? "text-red-700" : asset?.status === "stale" ? "text-amber-700" : "text-zinc-500"}`}>
                    {silentNarration ? "静默镜头，无需旁白" : asset ? assetStatusLabels[asset.status] || asset.status : "未生成"}
                    {!silentNarration && asset?.status === "ready" ? ` · ${formatFileSize(asset.file_size)}` : ""}
                    {!silentNarration && asset?.status === "ready" && continuitySummary ? ` · ${continuitySummary}` : ""}
                    {!silentNarration && asset?.failure_reason ? ` · ${asset.failure_reason}` : ""}
                  </p>
                </div>
                <div>
                  {!silentNarration && asset?.status === "ready" ? (
                    <VideoAssetPreview
                      asset={asset}
                      sceneNo={scene.scene_no}
                      reviewingAudio={reviewingAudioAssetId === asset.id}
                      reviewingVisual={reviewingVisualAssetId === asset.id}
                      onAudioReview={assetType === "audio" ? onAudioReview : undefined}
                      onVisualReview={assetType === "image" || assetType === "video" ? onVisualReview : undefined}
                    />
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2 sm:justify-end">
                  {!silentNarration && asset?.status === "ready" ? (
                    <button
                      className="rounded-md border border-zinc-300 px-3 py-2 text-xs font-medium text-zinc-700 disabled:text-zinc-400"
                      type="button"
                      disabled={downloadingAssetId !== null}
                      onClick={() => onDownload(asset)}
                    >
                      {downloadingAssetId === asset.id
                        ? "下载中..."
                        : assetType === "image"
                          ? "下载图片"
                        : assetType === "video"
                            ? "下载视频"
                            : "下载音频"}
                    </button>
                  ) : null}
                  {needsVisualRegeneration && onRegenerateScene ? (
                    <button
                      className="rounded-md border border-red-300 px-3 py-2 text-xs font-medium text-red-700 disabled:border-zinc-200 disabled:text-zinc-400"
                      type="button"
                      disabled={
                        active
                        || submitting
                        || regeneratingSceneId !== null
                        || visualRegenerationRemaining <= 0
                      }
                      onClick={() => onRegenerateScene(jobType, scene)}
                    >
                      {regeneratingSceneId === scene.id ? "提交中..." : "重拍此镜"}
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export default function VideoProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, loading: authLoading, error: authError } = useAuth();
  const [project, setProject] = useState<VideoProjectDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [storyboardingMode, setStoryboardingMode] = useState<"ai" | "local" | null>(null);
  const [capabilities, setCapabilities] = useState<VideoGenerationCapabilities>(defaultCapabilities);
  const [storyboardJob, setStoryboardJob] = useState<VideoGenerationJob | null>(null);
  const [imageJob, setImageJob] = useState<VideoGenerationJob | null>(null);
  const [videoJob, setVideoJob] = useState<VideoGenerationJob | null>(null);
  const [audioJob, setAudioJob] = useState<VideoGenerationJob | null>(null);
  const [renderJob, setRenderJob] = useState<VideoGenerationJob | null>(null);
  const [savingSceneId, setSavingSceneId] = useState<number | null>(null);
  const [generatingSubtitles, setGeneratingSubtitles] = useState(false);
  const [submittingAssetJob, setSubmittingAssetJob] = useState<VideoAssetJobType | null>(null);
  const [submittingRender, setSubmittingRender] = useState(false);
  const [downloadingAssetId, setDownloadingAssetId] = useState<number | null>(null);
  const [reviewingAudioAssetId, setReviewingAudioAssetId] = useState<number | null>(null);
  const [reviewingVisualAssetId, setReviewingVisualAssetId] = useState<number | null>(null);
  const [regeneratingSceneId, setRegeneratingSceneId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        detail,
        generationCapabilities,
        latestJob,
        latestImageJob,
        latestVideoJob,
        latestAudioJob,
        latestRenderJob,
      ] = await Promise.all([
        getVideoProject(params.id),
        getVideoGenerationCapabilities().catch(() => defaultCapabilities),
        getLatestAiVideoStoryboardJob(params.id).catch(() => null),
        getLatestVideoAssetJob(params.id, "image_assets").catch(() => null),
        getLatestVideoAssetJob(params.id, "video_clips").catch(() => null),
        getLatestVideoAssetJob(params.id, "narration_audio").catch(() => null),
        getLatestVideoRenderJob(params.id).catch(() => null),
      ]);
      setProject(detail);
      setCapabilities(generationCapabilities);
      setStoryboardJob(latestJob);
      setImageJob(latestImageJob);
      setVideoJob(latestVideoJob);
      setAudioJob(latestAudioJob);
      setRenderJob(latestRenderJob);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    if (!user) {
      return;
    }
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadProject();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadProject, user]);

  useEffect(() => {
    const activeJobs = [storyboardJob, imageJob, videoJob, audioJob, renderJob].filter(
      (job): job is VideoGenerationJob => Boolean(job && isActiveJob(job)),
    );
    if (activeJobs.length === 0) {
      return;
    }

    let active = true;
    let timer: number | undefined;
    const pollJobs = async () => {
      try {
        const nextJobs = await Promise.all(activeJobs.map((job) => getVideoGenerationJob(job.id)));
        if (!active) {
          return;
        }

        for (const nextJob of nextJobs) {
          if (nextJob.job_type === "ai_storyboard") {
            setStoryboardJob(nextJob);
          } else if (nextJob.job_type === "image_assets") {
            setImageJob(nextJob);
          } else if (nextJob.job_type === "video_clips") {
            setVideoJob(nextJob);
          } else if (nextJob.job_type === "narration_audio") {
            setAudioJob(nextJob);
          } else {
            setRenderJob(nextJob);
          }
        }

        if (nextJobs.some((job) => !isActiveJob(job))) {
          const [refreshedProject, refreshedCapabilities] = await Promise.all([
            getVideoProject(params.id),
            getVideoGenerationCapabilities().catch(() => null),
          ]);
          if (!active) {
            return;
          }
          setProject(refreshedProject);
          if (refreshedCapabilities) {
            setCapabilities(refreshedCapabilities);
          }
        }

        const failedJob = nextJobs.find((job) => job.status === "failed");
        if (failedJob) {
          const fallbackMessage = failedJob.job_type === "ai_storyboard"
            ? "AI 分镜任务执行失败，请重试。"
            : failedJob.job_type === "render"
              ? "成片渲染任务执行失败，请重试。"
              : "素材生成任务执行失败，请重试。";
          setError(failedJob.error_message || fallbackMessage);
        }

        if (nextJobs.some((job) => isActiveJob(job))) {
          timer = window.setTimeout(() => void pollJobs(), 1500);
        }
      } catch (pollError) {
        if (active) {
          setError(getApiErrorMessage(pollError));
          timer = window.setTimeout(() => void pollJobs(), 2500);
        }
      }
    };

    timer = window.setTimeout(() => void pollJobs(), 1000);
    return () => {
      active = false;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [audioJob, imageJob, params.id, renderJob, storyboardJob, videoJob]);

  async function handleDelete() {
    if (!project || deleting) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await deleteVideoProject(project.id);
      router.push("/video-projects");
    } catch (deleteError) {
      setError(getApiErrorMessage(deleteError));
      setDeleting(false);
    }
  }

  async function handleGenerateStoryboard(mode: "ai" | "local") {
    if (
      !project
      || storyboardingMode
      || isActiveJob(imageJob)
      || isActiveJob(videoJob)
      || isActiveJob(audioJob)
      || isActiveJob(renderJob)
    ) {
      return;
    }

    setStoryboardingMode(mode);
    setError(null);
    try {
      if (mode === "ai") {
        const job =
          storyboardJob?.status === "failed" && storyboardJob.can_retry
            ? await retryVideoGenerationJob(storyboardJob.id)
            : await createAiVideoStoryboardJob(project.id);
        setStoryboardJob(job);
      } else {
        setProject(await generateVideoProjectStoryboard(project.id));
        setStoryboardJob(null);
      }
    } catch (storyboardError) {
      setError(getApiErrorMessage(storyboardError));
    } finally {
      setStoryboardingMode(null);
    }
  }

  const hasActiveStoryboardJob = isActiveJob(storyboardJob);
  const hasActiveAssetJob =
    isActiveJob(imageJob) || isActiveJob(videoJob) || isActiveJob(audioJob) || isActiveJob(renderJob);

  async function handleGenerateAssetJob(jobType: VideoAssetJobType) {
    if (!project || submittingAssetJob || hasActiveStoryboardJob || isActiveJob(renderJob)) {
      return;
    }

    const currentJob = jobType === "image_assets" ? imageJob : jobType === "video_clips" ? videoJob : audioJob;
    if (isActiveJob(currentJob)) {
      return;
    }
    const configured =
      jobType === "image_assets"
        ? capabilities.image_assets_configured
        : jobType === "video_clips"
          ? capabilities.video_clips_configured
          : capabilities.narration_audio_configured;
    if (!configured) {
      setError("服务端尚未配置对应的素材生成服务。");
      return;
    }

    const assetType = jobType === "image_assets" ? "image" : jobType === "video_clips" ? "video" : "audio";
    const sceneAssets = project.assets.filter((asset) => asset.asset_type === assetType);
    const assetScenes = jobType === "narration_audio"
      ? project.scenes.filter(sceneRequiresNarration)
      : project.scenes;
    if (assetScenes.length === 0) {
      setError("当前分镜均为静默镜头，无需生成旁白。");
      return;
    }
    const assetSceneIds = new Set(assetScenes.map((scene) => scene.id));
    const readyCount = sceneAssets.filter(
      (asset) => asset.status === "ready" && asset.scene_id !== null && assetSceneIds.has(asset.scene_id),
    ).length;
    const retrying = currentJob?.status === "failed" && currentJob.can_retry;
    const resumingProviderTask = retrying && currentJob.can_resume_provider_task;
    const regenerate = readyCount === assetScenes.length;
    const expectedCalls = regenerate ? assetScenes.length : assetScenes.length - readyCount;
    const assetLabel = jobType === "image_assets" ? "静态分镜图" : jobType === "video_clips" ? "动态镜头" : "旁白配音";
    const actionLabel = resumingProviderTask ? "恢复并继续" : retrying ? "重试" : regenerate ? "重新生成" : "生成";
    const confirmationMessage = resumingProviderTask
      ? `${actionLabel}${assetLabel}会先查询已提交的超时镜头，不会重复创建该镜头任务；其余 ${Math.max(0, expectedCalls - 1)} 个未提交分镜仍可能调用外部 AI 服务并产生费用。确认提交吗？`
      : `${actionLabel}${assetLabel}将调用外部 AI 服务，预计处理 ${expectedCalls} 个分镜，可能产生费用。确认提交吗？`;
    const confirmed = window.confirm(
      confirmationMessage,
    );
    if (!confirmed) {
      return;
    }

    setSubmittingAssetJob(jobType);
    setError(null);
    try {
      const nextJob = retrying
        ? await retryVideoGenerationJob(currentJob.id)
        : await createVideoAssetJob(project.id, jobType, { regenerate });
      if (jobType === "image_assets") {
        setImageJob(nextJob);
      } else if (jobType === "video_clips") {
        setVideoJob(nextJob);
      } else {
        setAudioJob(nextJob);
      }
      const [refreshedProject, refreshedCapabilities] = await Promise.all([
        getVideoProject(project.id),
        getVideoGenerationCapabilities().catch(() => null),
      ]);
      setProject(refreshedProject);
      if (refreshedCapabilities) {
        setCapabilities(refreshedCapabilities);
      }
    } catch (assetError) {
      setError(getApiErrorMessage(assetError));
    } finally {
      setSubmittingAssetJob(null);
    }
  }

  async function handleGenerateSubtitles() {
    if (!project || generatingSubtitles) {
      return;
    }

    setGeneratingSubtitles(true);
    setError(null);
    try {
      await generateVideoProjectSubtitles(project.id);
      setProject(await getVideoProject(project.id));
    } catch (subtitleError) {
      setError(getApiErrorMessage(subtitleError));
    } finally {
      setGeneratingSubtitles(false);
    }
  }

  async function handleRenderFinalVideo() {
    if (!project || submittingRender || hasActiveStoryboardJob || hasActiveAssetJob) {
      return;
    }
    const currentFinalAsset = project.assets.find((asset) => asset.asset_type === "final_video") || null;
    const retrying = renderJob?.status === "failed" && renderJob.can_retry;
    const regenerate = currentFinalAsset?.status === "ready";
    const confirmed = window.confirm(
      "本地渲染会丢弃视频模型原音，只保留独立旁白，并将缺失旁白的镜头补为静音。确认开始吗？",
    );
    if (!confirmed) {
      return;
    }

    setSubmittingRender(true);
    setError(null);
    try {
      const nextJob = retrying
        ? await retryVideoGenerationJob(renderJob.id)
        : await createVideoRenderJob(project.id, {
            regenerate,
            include_narration: true,
            include_subtitles: true,
          });
      setRenderJob(nextJob);
      setProject(await getVideoProject(project.id));
    } catch (renderError) {
      setError(getApiErrorMessage(renderError));
    } finally {
      setSubmittingRender(false);
    }
  }

  async function handleDownloadAsset(asset: VideoAsset) {
    if (downloadingAssetId !== null) {
      return;
    }

    setDownloadingAssetId(asset.id);
    setError(null);
    try {
      const file = await downloadVideoAsset(asset.id, asset.file_name || "storyboard.srt");
      const objectUrl = window.URL.createObjectURL(file.blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = file.fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 0);
    } catch (downloadError) {
      setError(getApiErrorMessage(downloadError));
    } finally {
      setDownloadingAssetId(null);
    }
  }

  async function handleReviewAudioAsset(asset: VideoAsset, decision: VideoAudioReviewDecision) {
    if (!project || reviewingAudioAssetId !== null || hasActiveAssetJob) {
      return;
    }
    setReviewingAudioAssetId(asset.id);
    setError(null);
    try {
      await reviewVideoAudioAsset(asset.id, decision);
      setProject(await getVideoProject(project.id));
    } catch (reviewError) {
      setError(getApiErrorMessage(reviewError));
    } finally {
      setReviewingAudioAssetId(null);
    }
  }

  async function handleReviewVisualAsset(
    asset: VideoAsset,
    decision: VideoVisualReviewDecision,
    issueCodes: VideoVisualReviewIssueCode[] = [],
  ) {
    if (!project || reviewingVisualAssetId !== null || hasActiveAssetJob) {
      return;
    }
    setReviewingVisualAssetId(asset.id);
    setError(null);
    try {
      await reviewVideoVisualAsset(asset.id, decision, issueCodes);
      setProject(await getVideoProject(project.id));
    } catch (reviewError) {
      setError(getApiErrorMessage(reviewError));
    } finally {
      setReviewingVisualAssetId(null);
    }
  }

  async function handleRegenerateSceneAsset(jobType: VideoAssetJobType, scene: VideoScene) {
    if (
      !project
      || !["image_assets", "video_clips"].includes(jobType)
      || submittingAssetJob !== null
      || hasActiveAssetJob
      || capabilities.visual_regeneration_daily_scenes_remaining <= 0
    ) {
      return;
    }
    const assetLabel = jobType === "image_assets" ? "静态分镜图" : "动态镜头";
    const confirmed = window.confirm(
      `将只重新生成分镜 ${scene.scene_no} 的${assetLabel}，会调用一次外部 AI 服务并消耗局部重拍额度。确认提交吗？`,
    );
    if (!confirmed) {
      return;
    }

    setSubmittingAssetJob(jobType);
    setRegeneratingSceneId(scene.id);
    setError(null);
    try {
      const nextJob = await createVideoAssetJob(project.id, jobType, {
        regenerate: true,
        scene_ids: [scene.id],
      });
      if (jobType === "image_assets") {
        setImageJob(nextJob);
      } else {
        setVideoJob(nextJob);
      }
      const [refreshedProject, refreshedCapabilities] = await Promise.all([
        getVideoProject(project.id),
        getVideoGenerationCapabilities(),
      ]);
      setProject(refreshedProject);
      setCapabilities(refreshedCapabilities);
    } catch (assetError) {
      setError(getApiErrorMessage(assetError));
    } finally {
      setSubmittingAssetJob(null);
      setRegeneratingSceneId(null);
    }
  }

  async function handleUpdateScene(sceneId: number, payload: UpdateVideoScenePayload) {
    if (!project || savingSceneId !== null) {
      return;
    }
    if (hasActiveAssetJob) {
      setError("素材任务运行期间暂不能修改分镜。");
      throw new Error("Asset generation is active.");
    }

    setSavingSceneId(sceneId);
    setError(null);
    try {
      const updatedScene = await updateVideoScene(project.id, sceneId, payload);
      const scenes = project.scenes.map((scene) => (scene.id === sceneId ? updatedScene : scene));
      const changedFields = Object.keys(payload);
      const invalidatesSubtitles = changedFields.some((fieldName) => subtitleSourceFields.has(fieldName));
      const invalidatesImage = changedFields.some((fieldName) => imageSourceFields.has(fieldName));
      const invalidatesAudio = changedFields.some((fieldName) => audioSourceFields.has(fieldName));
      setProject({
        ...project,
        scenes,
        assets: project.assets.map((asset) => {
          if (asset.status !== "ready") {
            return asset;
          }
          if (asset.asset_type === "subtitle" && invalidatesSubtitles) {
            return { ...asset, status: "stale", failure_reason: "分镜已更新，请重新生成字幕。", download_url: "" };
          }
          if (asset.asset_type === "final_video") {
            return { ...asset, status: "stale", failure_reason: "项目素材已更新，请重新渲染成片。", download_url: "" };
          }
          if (asset.scene_id !== sceneId) {
            return asset;
          }
          if (
            ((asset.asset_type === "image" || asset.asset_type === "video") && invalidatesImage)
            || (asset.asset_type === "audio" && invalidatesAudio)
          ) {
            return { ...asset, status: "stale", failure_reason: "分镜内容已更新，请重新生成素材。", download_url: "" };
          }
          return asset;
        }),
        duration_target: scenes.reduce((total, scene) => total + scene.duration_seconds, 0),
        status: project.status === "completed" ? "storyboard_ready" : project.status,
        updated_at: updatedScene.updated_at,
      });
    } catch (sceneError) {
      setError(getApiErrorMessage(sceneError));
      throw sceneError;
    } finally {
      setSavingSceneId(null);
    }
  }

  if (authLoading) {
    return <section className="rounded-lg bg-white p-4 text-sm text-zinc-500 shadow-sm">正在检查登录状态...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-lg bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold">短视频项目详情</h1>
        <p className="mt-3 text-sm text-zinc-600">{authError || "当前未登录，请先登录后查看短视频项目。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  const subtitleAsset = project?.assets.find((asset) => asset.asset_type === "subtitle") || null;
  const imageAssets = project?.assets.filter((asset) => asset.asset_type === "image") || [];
  const videoAssets = project?.assets.filter((asset) => asset.asset_type === "video") || [];
  const audioAssets = project?.assets.filter((asset) => asset.asset_type === "audio") || [];
  const finalVideoAsset = project?.assets.find((asset) => asset.asset_type === "final_video") || null;
  const generatedVisualSceneIds = new Set(
    [...videoAssets, ...imageAssets]
      .filter((asset) => asset.status === "ready" && asset.scene_id !== null)
      .map((asset) => asset.scene_id),
  );
  const readyVisualSceneIds = new Set(
    [...videoAssets, ...imageAssets]
      .filter(
        (asset) => asset.status === "ready"
          && asset.scene_id !== null
          && isVisualRenderApproved(asset),
      )
      .map((asset) => asset.scene_id),
  );
  const unreviewedVisualSceneCount = [...generatedVisualSceneIds]
    .filter((sceneId) => !readyVisualSceneIds.has(sceneId))
    .length;
  const readyNarrationAssets = audioAssets.filter((asset) => asset.status === "ready");
  const readyNarrationCount = readyNarrationAssets.length;
  const verifiedNarrationCount = readyNarrationAssets.filter(isNarrationRenderApproved).length;
  const unverifiedNarrationCount = readyNarrationCount - verifiedNarrationCount;
  const allVisualsReady = Boolean(
    project && project.scenes.length > 0 && project.scenes.every((scene) => readyVisualSceneIds.has(scene.id)),
  );
  const subtitleReady = subtitleAsset?.status === "ready";
  const canGenerateSubtitles = Boolean(
    project && assetReadyStatuses.has(project.status) && project.scenes.length > 0 && !hasActiveAssetJob,
  );
  const canGenerateAssets = Boolean(
    capabilities.asset_jobs_available
      && project
      && assetReadyStatuses.has(project.status)
      && project.scenes.length > 0
      && !hasActiveStoryboardJob
      && !isActiveJob(renderJob),
  );
  const canRenderFinalVideo = Boolean(
    capabilities.local_render_available
      && project
      && assetReadyStatuses.has(project.status)
      && allVisualsReady
      && subtitleReady
      && unverifiedNarrationCount === 0
      && !hasActiveStoryboardJob
      && !hasActiveAssetJob,
  );

  return (
    <section className="space-y-4">
      <div className="rounded-lg bg-white p-4 shadow-sm">
        <Link href="/video-projects" className="text-sm font-medium text-emerald-700">
          返回项目列表
        </Link>
        <h1 className="mt-3 text-lg font-semibold text-zinc-900">{project?.title || "短视频项目详情"}</h1>
        <p className="mt-1 text-sm text-zinc-500">检查剧情内容、生成分镜，并在进入素材制作前逐镜调整。</p>
      </div>

      {error ? <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-lg bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载项目详情...</p> : null}

      {!loading && project ? (
        <>
          <section className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-lg bg-white p-4 shadow-sm">
              <p className="text-xs text-zinc-500">状态</p>
              <p className="mt-1 text-sm font-semibold text-zinc-900">{statusLabels[project.status] || project.status}</p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow-sm">
              <p className="text-xs text-zinc-500">画幅</p>
              <p className="mt-1 text-sm font-semibold text-zinc-900">{project.aspect_ratio}</p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow-sm">
              <p className="text-xs text-zinc-500">目标时长</p>
              <p className="mt-1 text-sm font-semibold text-zinc-900">{project.duration_target} 秒</p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow-sm">
              <p className="text-xs text-zinc-500">更新时间</p>
              <p className="mt-1 text-sm font-semibold text-zinc-900">{formatDateLabel(project.updated_at)}</p>
            </div>
          </section>

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold text-zinc-900">分镜生成</h2>
                <p className="mt-1 text-sm text-zinc-500">
                  AI 模式按剧情策划、必要修复、人物与场景建模、原子镜头、状态链适配和质量门禁依次执行；本地模式保留为降级路径。
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={Boolean(storyboardingMode) || hasActiveStoryboardJob || hasActiveAssetJob || !capabilities.ai_storyboard_configured || !storyboardReadyStatuses.has(project.status)}
                  onClick={() => void handleGenerateStoryboard("ai")}
                >
                  {storyboardingMode === "ai"
                    ? "提交中..."
                    : hasActiveStoryboardJob
                      ? storyboardJob?.status === "queued"
                        ? "AI 已排队"
                        : "AI 生成中..."
                      : storyboardJob?.status === "failed" && storyboardJob.can_retry
                        ? "重试 AI 生成"
                        : project.scenes.length > 0
                          ? "AI 重新生成"
                          : "AI 生成分镜"}
                </button>
                <button
                  className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 disabled:text-zinc-400"
                  type="button"
                  disabled={Boolean(storyboardingMode) || hasActiveStoryboardJob || hasActiveAssetJob || !storyboardReadyStatuses.has(project.status)}
                  onClick={() => void handleGenerateStoryboard("local")}
                >
                  {storyboardingMode === "local" ? "本地生成中..." : "本地生成"}
                </button>
              </div>
            </div>
            {!capabilities.ai_storyboard_configured ? (
              <p className="mt-3 text-xs text-zinc-500">服务端 AI 尚未配置，当前可使用本地生成。</p>
            ) : null}
            {storyboardJob ? (
              <div className="mt-3 flex flex-col gap-1 border-t border-zinc-200 pt-3 text-xs text-zinc-600 sm:flex-row sm:items-center sm:justify-between">
                <p>
                  AI 任务 #{storyboardJob.id} · {jobStatusLabels[storyboardJob.status] || storyboardJob.status}
                </p>
                <p>
                  尝试 {storyboardJob.attempt_count}/{storyboardJob.max_attempts}
                  {storyboardJob.model_name ? ` · ${storyboardJob.model_name}` : ""}
                </p>
              </div>
            ) : null}
            {storyboardJob?.status === "failed" && storyboardJob.error_message ? (
              <p className="mt-2 text-xs text-red-700">{storyboardJob.error_message}</p>
            ) : null}
            {storyboardJob?.status === "failed" && storyboardJob.error_message.includes("单镜台词过长") ? (
              <p className="mt-2 text-xs text-amber-700">
                已启用台词预算精编 Agent；重试时会按具体超限节拍压缩台词，并保留原剧情含义。
              </p>
            ) : null}
            {storyboardJob?.status === "failed" && !storyboardJob.can_retry ? (
              <p className="mt-2 text-xs text-amber-700">
                该任务已达到重试上限；再次点击“AI 生成分镜”会创建新任务，并保留当前失败记录。
              </p>
            ) : null}
            {hasActiveAssetJob ? (
              <p className="mt-2 text-xs text-amber-700">素材任务运行期间，分镜生成与编辑暂时锁定。</p>
            ) : null}
            {!storyboardReadyStatuses.has(project.status) ? (
              <p className="mt-3 text-xs text-amber-700">当前状态暂不允许重新生成分镜。</p>
            ) : null}
          </section>

          {project.agent_workflow?.version ? (
            <VideoAgentWorkflowPanel workflow={project.agent_workflow} />
          ) : null}

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-base font-semibold text-zinc-900">来源快照</h2>
              {project.source_title ? <p className="text-xs text-zinc-500">{project.source_title}</p> : null}
            </div>
            <p className="mt-3 max-h-80 overflow-y-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-sm leading-6 text-zinc-700">
              {project.input_text}
            </p>
          </section>

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-base font-semibold text-zinc-900">分镜草稿</h2>
              {project.scenes.length > 0 ? (
                <p className="text-xs text-zinc-500">总时长 {project.scenes.reduce((total, scene) => total + scene.duration_seconds, 0)} 秒</p>
              ) : null}
            </div>
            {project.scenes.length === 0 ? (
              <div className="mt-3 rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-5 text-sm text-zinc-500">
                还没有生成分镜。点击上方按钮可先生成 4 到 8 个本地分镜占位。
              </div>
            ) : (
              <div className="mt-3 grid gap-3">
                {project.scenes.map((scene) => (
                  <VideoSceneEditor
                    key={scene.id}
                    scene={scene}
                    saving={savingSceneId === scene.id}
                    disabled={hasActiveAssetJob}
                    onSave={handleUpdateScene}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <div>
              <h2 className="text-base font-semibold text-zinc-900">素材准备</h2>
              <p className="mt-1 text-sm text-zinc-500">动态镜头可携带实验性模型音效；独立旁白通过波形检查，并由 ASR 或人工试听确认语义。</p>
            </div>
            <div className="mt-3 divide-y divide-zinc-200 border-y border-zinc-200">
              <div className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-zinc-900">字幕文件</p>
                  <p className={`mt-1 text-xs ${subtitleAsset?.status === "stale" ? "text-amber-700" : "text-zinc-500"}`}>
                    {!subtitleAsset
                      ? canGenerateSubtitles
                        ? "尚未生成"
                        : "需先完成分镜"
                      : subtitleAsset.status === "ready"
                        ? `${subtitleAsset.file_name} · ${formatFileSize(subtitleAsset.file_size)}`
                        : subtitleAsset.status === "stale"
                          ? subtitleAsset.failure_reason || "分镜已更新，请重新生成字幕。"
                          : subtitleAsset.failure_reason || "字幕暂不可用"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {subtitleAsset?.status === "ready" ? (
                    <button
                      className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 disabled:text-zinc-400"
                      type="button"
                      disabled={downloadingAssetId !== null}
                      onClick={() => void handleDownloadAsset(subtitleAsset)}
                    >
                      {downloadingAssetId === subtitleAsset.id ? "下载中..." : "下载 SRT"}
                    </button>
                  ) : null}
                  <button
                    className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
                    type="button"
                    disabled={!canGenerateSubtitles || generatingSubtitles}
                    onClick={() => void handleGenerateSubtitles()}
                  >
                    {generatingSubtitles
                      ? "生成中..."
                      : subtitleAsset
                        ? "重新生成字幕"
                        : "生成字幕"}
                  </button>
                </div>
              </div>
              <AssetJobBlock
                title="动态镜头"
                description={[
                  capabilities.video_clips_previous_tail_frame_enabled
                    ? capabilities.video_clips_previous_tail_frame_available
                      ? "首镜使用本镜静态图；后续镜头优先承接上一镜尾帧，尾帧不可用时回退本镜静态图或文生视频。"
                      : "当前 FFmpeg 不可用，无法提取上一镜尾帧；将回退本镜静态图或文生视频。"
                    : capabilities.video_clips_reference_frame_enabled
                      ? "优先使用同分镜已就绪的静态图作为首帧，缺图时自动回退文生视频。"
                    : "按分镜提示词生成竖屏 MP4。",
                  capabilities.video_clips_with_audio
                    ? "模型内嵌音频仅作为实验性环境音，不作为清晰旁白。"
                    : "输出不含模型音频，旁白使用下方独立配音。",
                ].join(" ")}
                assetType="video"
                jobType="video_clips"
                scenes={project.scenes}
                assets={videoAssets}
                job={videoJob}
                configured={capabilities.video_clips_configured}
                providerSummary={[
                  capabilities.video_clips_model,
                  capabilities.video_clips_size,
                  capabilities.video_clips_duration_seconds ? `${capabilities.video_clips_duration_seconds} 秒` : "",
                  capabilities.video_clips_fps ? `${capabilities.video_clips_fps} FPS` : "",
                  capabilities.video_clips_previous_tail_frame_enabled
                    ? capabilities.video_clips_previous_tail_frame_available
                      ? "尾帧连续"
                      : "尾帧提取不可用"
                    : capabilities.video_clips_reference_frame_enabled
                      ? "静态图首帧"
                      : "文生视频",
                  capabilities.video_clips_with_audio ? "实验性 AI 音效" : "无模型音频",
                  capabilities.visual_review_available ? "人工视觉复核" : "",
                ].filter(Boolean).join(" · ")}
                dailyLimit={capabilities.video_clips_daily_job_limit}
                dailyRemaining={capabilities.video_clips_daily_jobs_remaining}
                canGenerate={canGenerateAssets}
                submitting={submittingAssetJob === "video_clips"}
                downloadingAssetId={downloadingAssetId}
                reviewingVisualAssetId={reviewingVisualAssetId}
                regeneratingSceneId={regeneratingSceneId}
                visualRegenerationRemaining={capabilities.visual_regeneration_daily_scenes_remaining}
                onGenerate={(jobType) => void handleGenerateAssetJob(jobType)}
                onDownload={(asset) => void handleDownloadAsset(asset)}
                onVisualReview={(asset, decision, issueCodes) => void handleReviewVisualAsset(asset, decision, issueCodes)}
                onRegenerateScene={(jobType, scene) => void handleRegenerateSceneAsset(jobType, scene)}
              />
              <AssetJobBlock
                title="静态分镜图"
                description={
                  capabilities.image_assets_continuity_workflow
                    ? "按视觉圣经、角色/场景/道具规范锚点、连续镜头组和逐镜视觉差量生成关键帧；当前模型仅支持文本输入，出图后仍需人工复核身份与场景一致性。"
                    : "生成统一构图关键帧；先完成此任务后再生成动态镜头，可将图片作为对应镜头首帧。"
                }
                assetType="image"
                jobType="image_assets"
                scenes={project.scenes}
                assets={imageAssets}
                job={imageJob}
                configured={capabilities.image_assets_configured}
                providerSummary={[
                  capabilities.image_assets_model,
                  capabilities.image_assets_size,
                  capabilities.image_assets_continuity_workflow ? "连续性工作流 2.2" : "",
                  capabilities.image_assets_reference_mode === "text_only_canonical_anchors"
                    ? "规范文本锚点"
                    : "",
                  capabilities.image_assets_visual_review_mode === "manual_required"
                    ? "人工视觉复核"
                    : "",
                ].filter(Boolean).join(" · ")}
                dailyLimit={capabilities.image_assets_daily_job_limit}
                dailyRemaining={capabilities.image_assets_daily_jobs_remaining}
                canGenerate={canGenerateAssets}
                submitting={submittingAssetJob === "image_assets"}
                downloadingAssetId={downloadingAssetId}
                reviewingVisualAssetId={reviewingVisualAssetId}
                regeneratingSceneId={regeneratingSceneId}
                visualRegenerationRemaining={capabilities.visual_regeneration_daily_scenes_remaining}
                onGenerate={(jobType) => void handleGenerateAssetJob(jobType)}
                onDownload={(asset) => void handleDownloadAsset(asset)}
                onVisualReview={(asset, decision, issueCodes) => void handleReviewVisualAsset(asset, decision, issueCodes)}
                onRegenerateScene={(jobType, scene) => void handleRegenerateSceneAsset(jobType, scene)}
              />
              <AssetJobBlock
                title="清晰旁白（推荐）"
                description="按分镜生成独立 WAV，检查响度、静音、削波和时长；ASR 未启用或差异较大时需要人工试听确认。"
                assetType="audio"
                jobType="narration_audio"
                scenes={project.scenes}
                assets={audioAssets}
                job={audioJob}
                configured={capabilities.narration_audio_configured}
                providerSummary={[
                  capabilities.narration_audio_model,
                  capabilities.narration_audio_voice,
                  capabilities.narration_audio_asr_configured
                    ? `${capabilities.narration_audio_asr_model} 语义质检`
                    : "人工语义确认",
                ].filter(Boolean).join(" · ")}
                dailyLimit={capabilities.narration_audio_daily_job_limit}
                dailyRemaining={capabilities.narration_audio_daily_jobs_remaining}
                canGenerate={canGenerateAssets}
                submitting={submittingAssetJob === "narration_audio"}
                downloadingAssetId={downloadingAssetId}
                reviewingAudioAssetId={reviewingAudioAssetId}
                onGenerate={(jobType) => void handleGenerateAssetJob(jobType)}
                onDownload={(asset) => void handleDownloadAsset(asset)}
                onAudioReview={(asset, decision) => void handleReviewAudioAsset(asset, decision)}
              />
            </div>
          </section>

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-base font-semibold text-zinc-900">成片输出</h2>
                <p className="mt-1 text-sm text-zinc-500">
                  本地合并逐镜画面、独立旁白和字幕；视频模型原音不会进入最终音轨。
                </p>
              </div>
              <button
                className="self-start rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
                type="button"
                disabled={submittingRender || isActiveJob(renderJob) || !canRenderFinalVideo}
                onClick={() => void handleRenderFinalVideo()}
              >
                {submittingRender
                  ? "提交中..."
                  : isActiveJob(renderJob)
                    ? renderJob?.status === "queued"
                      ? "渲染任务已排队"
                      : "正在渲染成片..."
                    : renderJob?.status === "failed" && renderJob.can_retry
                      ? "重试成片渲染"
                      : finalVideoAsset
                        ? "重新渲染成片"
                        : "生成成片"}
              </button>
            </div>

            <div className="mt-4 grid gap-2 border-y border-zinc-200 py-3 text-xs text-zinc-600 sm:grid-cols-4">
              <p className={readyVisualSceneIds.size < project.scenes.length ? "text-amber-700" : ""}>
                已审核画面 {readyVisualSceneIds.size}/{project.scenes.length}
              </p>
              <p className={verifiedNarrationCount < project.scenes.length ? "text-amber-700" : ""}>
                旁白 {verifiedNarrationCount}/{project.scenes.length}
              </p>
              <p className={subtitleReady ? "" : "text-amber-700"}>字幕 {subtitleReady ? "已就绪" : "未就绪"}</p>
              <p>
                {[capabilities.local_render_engine, capabilities.local_render_size, capabilities.local_render_fps
                  ? `${capabilities.local_render_fps} FPS`
                  : ""].filter(Boolean).join(" · ") || "渲染程序不可用"}
              </p>
            </div>

            {readyNarrationCount < project.scenes.length ? (
              <p className="mt-3 text-xs text-amber-700">
                缺少 {project.scenes.length - readyNarrationCount} 个镜头的独立旁白，这些镜头会使用静音并保留字幕。
              </p>
            ) : null}
            {unverifiedNarrationCount > 0 ? (
              <p className="mt-3 text-xs text-red-700">
                {unverifiedNarrationCount} 个已生成旁白尚未通过语义确认，请逐镜试听后确认或重新生成。
              </p>
            ) : null}
            {!allVisualsReady ? (
              <p className="mt-3 text-xs text-amber-700">
                {unreviewedVisualSceneCount > 0
                  ? `${unreviewedVisualSceneCount} 个已生成镜头尚未通过视觉复核；拒绝后可只重拍该镜。`
                  : "每个镜头至少需要一份已就绪且视觉复核通过的动态视频或静态分镜图。"}
              </p>
            ) : null}
            {!subtitleReady ? (
              <p className="mt-3 text-xs text-amber-700">请先在素材准备中生成或更新字幕文件。</p>
            ) : null}

            {renderJob ? (
              <div className="mt-3 flex flex-col gap-1 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
                <p>任务 #{renderJob.id} · {jobStatusLabels[renderJob.status] || renderJob.status}</p>
                <p>尝试 {renderJob.attempt_count}/{renderJob.max_attempts}</p>
              </div>
            ) : null}
            {renderJob?.status === "failed" && renderJob.error_message ? (
              <p className="mt-2 text-xs text-red-700">{renderJob.error_message}</p>
            ) : null}

            {finalVideoAsset?.status === "ready" ? (
              <div className="mt-4 flex flex-col gap-4 border-t border-zinc-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <VideoAssetPreview asset={finalVideoAsset} />
                  <p className="mt-2 text-xs text-zinc-500">
                    {finalVideoAsset.file_name} · {formatFileSize(finalVideoAsset.file_size)}
                  </p>
                </div>
                <button
                  className="self-start rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 disabled:text-zinc-400"
                  type="button"
                  disabled={downloadingAssetId !== null}
                  onClick={() => void handleDownloadAsset(finalVideoAsset)}
                >
                  {downloadingAssetId === finalVideoAsset.id ? "下载中..." : "下载成片"}
                </button>
              </div>
            ) : finalVideoAsset ? (
              <p className={`mt-3 text-xs ${finalVideoAsset.status === "failed" ? "text-red-700" : "text-amber-700"}`}>
                {finalVideoAsset.failure_reason || assetStatusLabels[finalVideoAsset.status] || finalVideoAsset.status}
              </p>
            ) : null}
          </section>

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <button
              className="rounded-md border border-red-200 px-4 py-2 text-sm font-medium text-red-700 disabled:text-zinc-400"
              type="button"
              disabled={deleting}
              onClick={() => void handleDelete()}
            >
              {deleting ? "删除中..." : "删除项目"}
            </button>
          </section>
        </>
      ) : null}
    </section>
  );
}
