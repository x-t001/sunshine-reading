"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { getAdminNovelDetail, updateAdminNovelFeatured, updateAdminNovelStatus } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminAuditStatus, AdminNovelDetail, AdminNovelStatus } from "@/types/admin";

const novelStatusLabels: Record<AdminNovelStatus, string> = {
  serializing: "连载中",
  completed: "已完结",
  paused: "暂停更新",
  removed: "已下架",
};

const auditStatusLabels: Record<AdminAuditStatus, string> = {
  draft: "草稿",
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已驳回",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "暂无";
  }
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminNovelDetailPage() {
  return (
    <AdminLayout title="小说详情" description="查看小说信息、统计数据，并调整状态或推荐。">
      <AdminNovelDetailContent />
    </AdminLayout>
  );
}

function AdminNovelDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [novel, setNovel] = useState<AdminNovelDetail | null>(null);
  const [statusDraft, setStatusDraft] = useState<AdminNovelStatus>("serializing");
  const [loading, setLoading] = useState(true);
  const [operating, setOperating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadNovel = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminNovelDetail(id);
      setNovel(result);
      setStatusDraft(result.status);
    } catch (loadError) {
      setNovel(null);
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadNovel();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadNovel]);

  async function handleStatusSave() {
    if (!novel) {
      return;
    }
    if (statusDraft === "removed" && !window.confirm(`确认下架小说「${novel.title}」？`)) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await updateAdminNovelStatus(novel.id, { status: statusDraft });
      setNotice(`小说状态已更新为 ${novelStatusLabels[statusDraft]}。`);
      await loadNovel();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperating(false);
    }
  }

  async function handleFeatured(isFeatured: boolean) {
    if (!novel) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await updateAdminNovelFeatured(novel.id, { is_featured: isFeatured });
      setNotice(`小说已${isFeatured ? "设为推荐" : "取消推荐"}。`);
      await loadNovel();
    } catch (featuredError) {
      setError(getApiErrorMessage(featuredError));
    } finally {
      setOperating(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载小说详情...</section>;
  }

  if (!novel) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error || "小说不存在或无权访问。"}
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">{novel.title}</h2>
            <p className="mt-2 text-sm text-zinc-500">
              作者：{novel.author_nickname || novel.author_username || "未知"} · 分类：{novel.category?.name || "未分类"}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              状态：{novelStatusLabels[novel.status]} · 审核：{auditStatusLabels[novel.audit_status]} · {novel.is_featured ? "已推荐" : "未推荐"}
            </p>
            <p className="mt-3 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-zinc-700">{novel.description || "暂无简介"}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2 text-sm">
            <Link href="/admin/novels" className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
              返回列表
            </Link>
            <select
              className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
              value={statusDraft}
              disabled={operating}
              onChange={(event) => setStatusDraft(event.target.value as AdminNovelStatus)}
            >
              {Object.entries(novelStatusLabels).map(([status, label]) => (
                <option key={status} value={status}>
                  {label}
                </option>
              ))}
            </select>
            <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating || statusDraft === novel.status} onClick={() => void handleStatusSave()}>
              保存状态
            </button>
            <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operating} onClick={() => void handleFeatured(!novel.is_featured)}>
              {novel.is_featured ? "取消推荐" : "设置推荐"}
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <StatCard label="字数" value={`${novel.word_count}`} />
        <StatCard label="章节数" value={`${novel.chapter_count}`} />
        <StatCard label="阅读量" value={`${novel.view_count}`} />
        <StatCard label="收藏数" value={`${novel.collect_count}`} />
        <StatCard label="评论数" value={`${novel.comment_count}`} />
        <StatCard label="平均评分" value={`${novel.rating_score}`} />
        <StatCard label="评分人数" value={`${novel.rating_count}`} />
        <StatCard label="小说 ID" value={`${novel.id}`} />
      </section>

      <section className="rounded-xl bg-white p-4 text-sm leading-7 text-zinc-600 shadow-sm">
        <p>作者 ID：{novel.author_id}</p>
        <p>最新章节：{novel.latest_chapter_title || "暂无"}</p>
        <p>最新章节更新时间：{formatDateTime(novel.latest_chapter_updated_at)}</p>
        <p>审核员：{novel.reviewer?.nickname || novel.reviewer?.username || "暂无"}</p>
        <p>审核完成时间：{formatDateTime(novel.reviewed_at)}</p>
        <p>创建时间：{formatDateTime(novel.created_at)}</p>
        <p>更新时间：{formatDateTime(novel.updated_at)}</p>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
    </div>
  );
}
