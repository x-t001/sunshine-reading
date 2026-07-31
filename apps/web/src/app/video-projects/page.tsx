"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getVideoProjects } from "@/lib/api/video-projects";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel } from "@/lib/utils/format";
import { useAuth } from "@/hooks/useAuth";
import type { VideoProjectListItem } from "@/types/video-project";

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

function statusClass(status: string): string {
  if (status === "failed") {
    return "bg-red-50 text-red-700";
  }
  if (status === "storyboard_ready" || status === "completed") {
    return "bg-emerald-50 text-emerald-700";
  }
  if (status === "canceled") {
    return "bg-zinc-100 text-zinc-500";
  }
  return "bg-amber-50 text-amber-700";
}

export default function VideoProjectsPage() {
  const { user, loading: authLoading, error: authError } = useAuth();
  const [items, setItems] = useState<VideoProjectListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await getVideoProjects({ page: 1, page_size: 20 });
      setItems(page.results);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadProjects();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadProjects, user]);

  if (authLoading) {
    return <section className="rounded-lg bg-white p-4 text-sm text-zinc-500 shadow-sm">正在检查登录状态...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-lg bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold">短视频项目</h1>
        <p className="mt-3 text-sm text-zinc-600">{authError || "当前未登录，请先登录后创建和查看短视频项目。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-900">短视频项目</h1>
          <p className="mt-1 text-sm text-zinc-500">从故事文本、单个章节或小说章节范围创建 9:16 短视频草稿。</p>
        </div>
        <Link href="/video-projects/create" className="inline-flex justify-center rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          新建项目
        </Link>
      </div>

      {error ? <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-lg bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载短视频项目...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-lg border border-dashed border-zinc-300 bg-white p-6 text-center">
          <p className="text-sm text-zinc-500">还没有短视频项目。先粘贴一段故事文本创建草稿。</p>
          <Link href="/video-projects/create" className="mt-4 inline-flex rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
            创建第一个项目
          </Link>
        </section>
      ) : null}

      <div className="grid gap-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <Link href={`/video-projects/${item.id}`} className="line-clamp-1 text-base font-semibold text-zinc-900 hover:text-emerald-700">
                  {item.title || "未命名短视频项目"}
                </Link>
                <p className="mt-2 text-sm text-zinc-500">
                  {item.aspect_ratio} · {item.duration_target} 秒 · {item.scene_count} 个分镜
                </p>
                {item.source_title ? <p className="mt-1 line-clamp-1 text-xs text-zinc-500">来源：{item.source_title}</p> : null}
                <p className="mt-1 text-xs text-zinc-400">更新于 {formatDateLabel(item.updated_at)}</p>
              </div>
              <span className={`w-fit rounded-full px-3 py-1 text-xs font-medium ${statusClass(item.status)}`}>
                {statusLabels[item.status] || item.status}
              </span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
