"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { RejectDialog } from "@/components/RejectDialog";
import { ReviewerLayout } from "@/components/ReviewerLayout";
import { approveChapter, claimChapter, getReviewerChapterDetail, rejectChapter } from "@/lib/api/reviewer";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { ReviewerChapterDetail, ReviewAuditStatus } from "@/types/reviewer";

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

export default function ReviewerChapterDetailPage() {
  return (
    <ReviewerLayout title="章节审核详情" description="阅读章节正文并执行审核操作。">
      <ReviewerChapterDetailContent />
    </ReviewerLayout>
  );
}

function ReviewerChapterDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [chapter, setChapter] = useState<ReviewerChapterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [operating, setOperating] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadChapter = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setChapter(await getReviewerChapterDetail(id));
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

  async function runAction(action: "claim" | "approve") {
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      const result = action === "claim" ? await claimChapter(id) : await approveChapter(id);
      setNotice(`章节“${result.title}”已${action === "claim" ? "领取" : "通过"}，当前状态：${auditStatusLabels[result.audit_status]}`);
      await loadChapter();
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
      const result = await rejectChapter(id, { reason });
      setNotice(`章节“${result.title}”已驳回。`);
      setRejectOpen(false);
      await loadChapter();
    } catch (rejectError) {
      setError(getApiErrorMessage(rejectError));
    } finally {
      setOperating(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节审核详情...</section>;
  }

  if (!chapter) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error || "章节不存在或无权访问。"}
      </section>
    );
  }

  const canReview = chapter.audit_status === "pending" || chapter.audit_status === "reviewing";
  const canClaim = chapter.audit_status === "pending";
  const reviewerName = chapter.reviewer?.nickname || chapter.reviewer?.username || "暂无";

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">
              第 {chapter.chapter_number} 章 {chapter.title}
            </h2>
            <p className="mt-2 text-sm text-zinc-500">
              小说：{chapter.novel?.title || "未知"} · 作者：{chapter.novel?.author?.nickname || chapter.novel?.author?.username || "未知"}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              {formatWordCount(chapter.word_count)} · {chapter.status} / {auditStatusLabels[chapter.audit_status]} · 更新 {formatDateLabel(chapter.updated_at)}
            </p>
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
        <div className="mt-4 grid gap-2 text-sm text-zinc-500 md:grid-cols-2">
          <p>审核员：{reviewerName}</p>
          <p>审核完成时间：{chapter.reviewed_at ? formatDateLabel(chapter.reviewed_at) : "暂无"}</p>
        </div>
      </section>

      <article className="rounded-xl bg-white p-5 shadow-sm md:p-8">
        <div className="mx-auto max-w-3xl whitespace-pre-wrap text-base leading-8 text-zinc-800">{chapter.content}</div>
      </article>

      <RejectDialog
        open={rejectOpen}
        title={`驳回章节：${chapter.title}`}
        submitting={operating}
        error={error}
        onCancel={() => setRejectOpen(false)}
        onConfirm={handleReject}
      />
    </div>
  );
}
