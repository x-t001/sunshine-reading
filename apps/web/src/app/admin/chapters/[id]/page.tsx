"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { getAdminChapterDetail, updateAdminChapterStatus } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminAuditStatus, AdminChapterDetail, AdminChapterStatus } from "@/types/admin";

const chapterStatusLabels: Record<AdminChapterStatus, string> = {
  draft: "草稿",
  published: "已发布",
  hidden: "已隐藏",
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

export default function AdminChapterDetailPage() {
  return (
    <AdminLayout title="章节详情" description="查看章节正文和状态，并执行隐藏或恢复操作。">
      <AdminChapterDetailContent />
    </AdminLayout>
  );
}

function AdminChapterDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [chapter, setChapter] = useState<AdminChapterDetail | null>(null);
  const [statusDraft, setStatusDraft] = useState<AdminChapterStatus>("draft");
  const [loading, setLoading] = useState(true);
  const [operating, setOperating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadChapter = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminChapterDetail(id);
      setChapter(result);
      setStatusDraft(result.status);
    } catch (loadError) {
      setChapter(null);
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
        await loadChapter();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadChapter]);

  async function handleStatusSave() {
    if (!chapter) {
      return;
    }
    if (statusDraft === "hidden" && !window.confirm(`确认隐藏章节「${chapter.title}」？`)) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await updateAdminChapterStatus(chapter.id, { status: statusDraft });
      setNotice(`章节状态已更新为 ${chapterStatusLabels[statusDraft]}。`);
      await loadChapter();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperating(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节详情...</section>;
  }

  if (!chapter) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error || "章节不存在或无权访问。"}
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
            <h2 className="text-lg font-semibold">
              第 {chapter.chapter_number} 章 {chapter.title}
            </h2>
            <p className="mt-2 text-sm text-zinc-500">
              小说：{chapter.novel_title || chapter.novel?.title || "未知小说"} · 作者：{chapter.author_username || "未知作者"}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              状态：{chapterStatusLabels[chapter.status]} · 审核：{auditStatusLabels[chapter.audit_status]} · {chapter.is_free ? "免费章节" : `付费 ${chapter.price}`}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2 text-sm">
            <Link href="/admin/chapters" className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
              返回列表
            </Link>
            <select
              className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
              value={statusDraft}
              disabled={operating}
              onChange={(event) => setStatusDraft(event.target.value as AdminChapterStatus)}
            >
              {Object.entries(chapterStatusLabels).map(([status, label]) => (
                <option key={status} value={status}>
                  {label}
                </option>
              ))}
            </select>
            <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating || statusDraft === chapter.status} onClick={() => void handleStatusSave()}>
              保存状态
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <StatCard label="章节 ID" value={`${chapter.id}`} />
        <StatCard label="小说 ID" value={`${chapter.novel_id}`} />
        <StatCard label="字数" value={`${chapter.word_count}`} />
        <StatCard label="价格" value={chapter.is_free ? "免费" : chapter.price} />
      </section>

      <section className="rounded-xl bg-white p-4 text-sm leading-7 text-zinc-600 shadow-sm">
        <p>发布时间：{formatDateTime(chapter.published_at)}</p>
        <p>审核员：{chapter.reviewer?.nickname || chapter.reviewer?.username || "暂无"}</p>
        <p>审核完成时间：{formatDateTime(chapter.reviewed_at)}</p>
        <p>创建时间：{formatDateTime(chapter.created_at)}</p>
        <p>更新时间：{formatDateTime(chapter.updated_at)}</p>
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h3 className="text-base font-semibold">章节正文</h3>
        <article className="mt-4 max-w-4xl whitespace-pre-wrap break-words text-sm leading-8 text-zinc-700">
          {chapter.content || "暂无正文"}
        </article>
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
