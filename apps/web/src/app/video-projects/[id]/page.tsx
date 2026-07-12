"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  deleteVideoProject,
  createAiVideoStoryboardJob,
  generateVideoProjectStoryboard,
  getLatestAiVideoStoryboardJob,
  getVideoGenerationCapabilities,
  getVideoGenerationJob,
  getVideoProject,
  retryVideoGenerationJob,
  updateVideoScene,
} from "@/lib/api/video-projects";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel } from "@/lib/utils/format";
import { useAuth } from "@/hooks/useAuth";
import type {
  UpdateVideoScenePayload,
  VideoGenerationCapabilities,
  VideoGenerationJob,
  VideoProjectDetail,
} from "@/types/video-project";
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

const storyboardReadyStatuses = new Set(["draft", "failed", "storyboard_ready"]);
const defaultCapabilities: VideoGenerationCapabilities = {
  ai_storyboard_configured: false,
  ai_storyboard_model: "",
  local_storyboard_available: true,
  durable_storyboard_jobs_available: false,
};

const jobStatusLabels: Record<string, string> = {
  queued: "等待处理",
  running: "正在生成",
  succeeded: "生成成功",
  failed: "生成失败",
  canceled: "已取消",
};

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
  const [savingSceneId, setSavingSceneId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [detail, generationCapabilities, latestJob] = await Promise.all([
        getVideoProject(params.id),
        getVideoGenerationCapabilities().catch(() => defaultCapabilities),
        getLatestAiVideoStoryboardJob(params.id).catch(() => null),
      ]);
      setProject(detail);
      setCapabilities(generationCapabilities);
      setStoryboardJob(latestJob);
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
    if (!storyboardJob || !["queued", "running"].includes(storyboardJob.status)) {
      return;
    }

    let active = true;
    let timer: number | undefined;
    const pollJob = async () => {
      try {
        const nextJob = await getVideoGenerationJob(storyboardJob.id);
        if (!active) {
          return;
        }
        if (["succeeded", "failed", "canceled"].includes(nextJob.status)) {
          const refreshedProject = await getVideoProject(params.id);
          if (!active) {
            return;
          }
          setProject(refreshedProject);
          setStoryboardJob(nextJob);
          if (nextJob.status === "failed") {
            setError(nextJob.error_message || "AI 分镜任务执行失败，请重试。");
          }
          return;
        }
        setStoryboardJob(nextJob);
      } catch (pollError) {
        if (active) {
          setError(getApiErrorMessage(pollError));
        }
      }
      if (active) {
        timer = window.setTimeout(() => void pollJob(), 1500);
      }
    };

    timer = window.setTimeout(() => void pollJob(), 1000);
    return () => {
      active = false;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [params.id, storyboardJob]);

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
    if (!project || storyboardingMode) {
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

  const hasActiveStoryboardJob = storyboardJob?.status === "queued" || storyboardJob?.status === "running";

  async function handleUpdateScene(sceneId: number, payload: UpdateVideoScenePayload) {
    if (!project || savingSceneId !== null) {
      return;
    }

    setSavingSceneId(sceneId);
    setError(null);
    try {
      const updatedScene = await updateVideoScene(project.id, sceneId, payload);
      const scenes = project.scenes.map((scene) => (scene.id === sceneId ? updatedScene : scene));
      setProject({
        ...project,
        scenes,
        duration_target: scenes.reduce((total, scene) => total + scene.duration_seconds, 0),
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
                  AI 模式生成更完整的镜头语言，本地模式可在服务未配置或生成失败时继续工作。
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={Boolean(storyboardingMode) || hasActiveStoryboardJob || !capabilities.ai_storyboard_configured || !storyboardReadyStatuses.has(project.status)}
                  onClick={() => void handleGenerateStoryboard("ai")}
                >
                  {storyboardingMode === "ai"
                    ? "提交中..."
                    : hasActiveStoryboardJob
                      ? storyboardJob.status === "queued"
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
                  disabled={Boolean(storyboardingMode) || hasActiveStoryboardJob || !storyboardReadyStatuses.has(project.status)}
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
            {!storyboardReadyStatuses.has(project.status) ? (
              <p className="mt-3 text-xs text-amber-700">当前状态暂不允许重新生成分镜。</p>
            ) : null}
          </section>

          <section className="rounded-lg bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-zinc-900">原始文本</h2>
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
                    onSave={handleUpdateScene}
                  />
                ))}
              </div>
            )}
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
