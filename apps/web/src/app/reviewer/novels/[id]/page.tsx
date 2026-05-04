"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { RejectDialog } from "@/components/RejectDialog";
import { ReviewerLayout } from "@/components/ReviewerLayout";
import { approveNovel, claimNovel, getReviewerNovelDetail, rejectNovel } from "@/lib/api/reviewer";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { ReviewerNovelDetail, ReviewAuditStatus } from "@/types/reviewer";

const auditStatusLabels: Record<ReviewAuditStatus, string> = {
  draft: "草稿",
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已驳回",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function ReviewerNovelDetailPage() {
  return (
    <ReviewerLayout title="作品审核详情" description="查看作品详情并执行审核操作。">
      <ReviewerNovelDetailContent />
    </ReviewerLayout>
  );
}

function ReviewerNovelDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [novel, setNovel] = useState<ReviewerNovelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [operating, setOperating] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadNovel = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setNovel(await getReviewerNovelDetail(id));
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

  async function runAction(action: "claim" | "approve") {
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      const result = action === "claim" ? await claimNovel(id) : await approveNovel(id);
      setNotice(`作品“${result.title}”已${action === "claim" ? "领取" : "通过"}，当前状态：${auditStatusLabels[result.audit_status]}`);
      await loadNovel();
    } catch (actionError) {
      setError(getApiErrorMessage(actionError));
    } finally {
      setOperating(false);
    }
  }

  async function handleReject(reason: string) {
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      const result = await rejectNovel(id, { reason });
      setNotice(`作品“${result.title}”已驳回。`);
      setRejectOpen(false);
      await loadNovel();
    } catch (rejectError) {
      setError(getApiErrorMessage(rejectError));
    } finally {
      setOperating(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载作品审核详情...</section>;
  }

  if (!novel) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error || "作品不存在或无权访问。"}
      </section>
    );
  }

  const canReview = novel.audit_status === "pending" || novel.audit_status === "reviewing";
  const canClaim = novel.audit_status === "pending";
  const reviewerName = novel.reviewer?.nickname || novel.reviewer?.username || "暂无";

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">{novel.title}</h2>
            <p className="mt-2 text-sm text-zinc-500">
              作者：{novel.author?.nickname || novel.author?.username || "未知"} · 分类：{novel.category?.name || "未分类"} · {auditStatusLabels[novel.audit_status]}
            </p>
            <p className="mt-3 text-sm leading-6 text-zinc-700">{novel.description || "暂无简介"}</p>
          </div>
          {canReview ? (
            <div className="flex shrink-0 flex-wrap gap-2 text-sm">
              {canClaim ? (
                <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operating} onClick={() => void runAction("claim")}>
                  领取审核
                </button>
              ) : null}
              <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating} onClick={() => void runAction("approve")}>
                审核通过
              </button>
              <button className="rounded-lg bg-red-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating} onClick={() => setRejectOpen(true)}>
                驳回审核
              </button>
            </div>
          ) : null}
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <StatCard label="字数" value={formatWordCount(novel.word_count)} />
        <StatCard label="章节数" value={`${novel.chapter_count} 章`} />
        <StatCard label="阅读量" value={`${novel.view_count}`} />
        <StatCard label="收藏数" value={`${novel.collect_count}`} />
        <StatCard label="评论数" value={`${novel.comment_count}`} />
        <StatCard label="评分" value={`${novel.rating_score} / ${novel.rating_count} 人`} />
      </section>

      <section className="rounded-xl bg-white p-4 text-sm text-zinc-600 shadow-sm">
        <p>创建时间：{formatDateLabel(novel.created_at)}</p>
        <p className="mt-1">更新时间：{formatDateLabel(novel.updated_at)}</p>
        <p className="mt-1">审核员：{reviewerName}</p>
        <p className="mt-1">审核完成时间：{novel.reviewed_at ? formatDateLabel(novel.reviewed_at) : "暂无"}</p>
        <p className="mt-1">最新章节：{novel.latest_chapter_title || "暂无"}</p>
      </section>

      <RejectDialog
        open={rejectOpen}
        title={`驳回作品：${novel.title}`}
        submitting={operating}
        error={error}
        onCancel={() => setRejectOpen(false)}
        onConfirm={handleReject}
      />
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
