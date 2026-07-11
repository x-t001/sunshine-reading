"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthorAuditHistory } from "@/components/AuthorAuditHistory";
import { AuthorLayout } from "@/components/AuthorLayout";
import { getAuthorNovelDetail, submitAuthorNovel } from "@/lib/api/author";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { AuthorNovelDetail } from "@/types/author";
import type { NovelAuditStatus, NovelStatus } from "@/types/novel";

const statusLabels: Record<NovelStatus, string> = {
  serializing: "连载中",
  completed: "已完结",
  paused: "暂停",
  removed: "已移除",
};

const auditStatusLabels: Record<NovelAuditStatus, string> = {
  draft: "草稿",
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已拒绝",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function AuthorNovelDetailPage() {
  return (
    <AuthorLayout title="作品详情" description="查看作品信息、统计数据和审核状态。">
      <AuthorNovelDetailContent />
    </AuthorLayout>
  );
}

function AuthorNovelDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [novel, setNovel] = useState<AuthorNovelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadNovel = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setNovel(await getAuthorNovelDetail(id));
    } catch (loadError) {
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

  async function handleSubmitReview() {
    if (!novel) {
      return;
    }
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const result = await submitAuthorNovel(novel.id);
      setNotice(`作品已提交审核，当前状态：${auditStatusLabels[result.audit_status]}`);
      await loadNovel();
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载作品详情...</section>;
  }

  if (!novel) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error || "作品不存在或无权访问。"}
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">{novel.title}</h2>
            <p className="mt-2 text-sm text-zinc-500">
              {novel.category?.name || "未分类"} · {statusLabels[novel.status]} · {auditStatusLabels[novel.audit_status]}
            </p>
            <p className="mt-3 text-sm leading-6 text-zinc-700">{novel.description}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2 text-sm">
            <Link href={`/author/novels/${novel.id}/edit`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
              编辑作品
            </Link>
            <Link href={`/author/novels/${novel.id}/chapters`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
              章节管理
            </Link>
            <button
              className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
              type="button"
              disabled={
                submitting ||
                novel.audit_status === "pending" ||
                novel.audit_status === "reviewing" ||
                novel.audit_status === "approved"
              }
              onClick={() => void handleSubmitReview()}
            >
              {submitting ? "提交中..." : "提交审核"}
            </button>
          </div>
        </div>
      </section>

      <AuthorAuditHistory logs={novel.audit_logs} currentStatus={novel.audit_status} />

      <section className="grid gap-3 md:grid-cols-3">
        <StatCard label="字数" value={formatWordCount(novel.word_count)} />
        <StatCard label="章节数" value={`${novel.chapter_count} 章`} />
        <StatCard label="阅读量" value={`${novel.view_count}`} />
        <StatCard label="收藏" value={`${novel.collect_count}`} />
        <StatCard label="评论" value={`${novel.comment_count}`} />
        <StatCard label="评分" value={`${novel.rating_score} / ${novel.rating_count} 人`} />
      </section>

      <section className="rounded-xl bg-white p-4 text-sm text-zinc-600 shadow-sm">
        <p>最新章节：{novel.latest_chapter_title || "暂无"}</p>
        <p className="mt-1">最近更新：{formatDateLabel(novel.updated_at)}</p>
        <p className="mt-1">创建时间：{formatDateLabel(novel.created_at)}</p>
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
