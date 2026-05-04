"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { RejectDialog } from "@/components/RejectDialog";
import { ReviewerLayout } from "@/components/ReviewerLayout";
import { approveChapter, claimChapter, getPendingChapters, rejectChapter } from "@/lib/api/reviewer";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { GetPendingChaptersParams, PendingChapter, ReviewAuditStatus } from "@/types/reviewer";

const PAGE_SIZE = 10;

const auditStatusLabels: Record<ReviewAuditStatus, string> = {
  draft: "草稿",
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已驳回",
};

type FilterState = {
  keyword: string;
  novel_id: string;
};

type RejectTarget = {
  id: number;
  title: string;
} | null;

export default function ReviewerChaptersPage() {
  return (
    <ReviewerLayout title="待审核章节" description="检查章节正文并处理审核状态。">
      <ReviewerChaptersContent />
    </ReviewerLayout>
  );
}

function ReviewerChaptersContent() {
  const router = useRouter();
  const [filters, setFilters] = useState<FilterState>({ keyword: "", novel_id: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PendingChapter[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [rejectTarget, setRejectTarget] = useState<RejectTarget>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadChapters = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: GetPendingChaptersParams = {
        page,
        page_size: PAGE_SIZE,
        keyword: query.keyword,
        novel_id: query.novel_id,
      };
      const result = await getPendingChapters(params);
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [page, query]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadChapters();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadChapters]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(filters);
  }

  async function runAction(id: number, action: "claim" | "approve") {
    setOperatingId(id);
    setError(null);
    setNotice(null);
    try {
      const result = action === "claim" ? await claimChapter(id) : await approveChapter(id);
      setNotice(`章节“${result.title}”已${action === "claim" ? "领取" : "通过"}，当前状态：${auditStatusLabels[result.audit_status]}`);
      if (action === "claim") {
        router.push(`/reviewer/chapters/${id}`);
        return;
      }
      await loadChapters();
    } catch (actionError) {
      setError(getApiErrorMessage(actionError));
    } finally {
      setOperatingId(null);
    }
  }

  async function handleReject(reason: string) {
    if (!rejectTarget) {
      return;
    }
    setOperatingId(rejectTarget.id);
    setError(null);
    setNotice(null);
    try {
      const result = await rejectChapter(rejectTarget.id, { reason });
      setNotice(`章节“${result.title}”已驳回。`);
      setRejectTarget(null);
      await loadChapters();
    } catch (rejectError) {
      setError(getApiErrorMessage(rejectError));
    } finally {
      setOperatingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="grid gap-3 md:grid-cols-5" onSubmit={handleSearch}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={filters.keyword}
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="搜索章节标题或小说标题"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={filters.novel_id}
            onChange={(event) => setFilters((current) => ({ ...current, novel_id: event.target.value }))}
            placeholder="小说 ID，可选"
          />
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载待审核章节...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无待审核章节。</section>
      ) : null}

      <div className="grid gap-3">
        {items.map((chapter) => (
          <article key={chapter.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <h2 className="line-clamp-1 text-base font-semibold">
                  第 {chapter.chapter_number} 章 {chapter.title}
                </h2>
                <p className="mt-1 text-sm text-zinc-500">
                  小说：{chapter.novel?.title || "未知"} · 作者：{chapter.novel?.author?.nickname || chapter.novel?.author?.username || "未知"} · {auditStatusLabels[chapter.audit_status]}
                </p>
                <p className="mt-2 text-xs text-zinc-500">
                  {formatWordCount(chapter.word_count)} · {chapter.is_free ? "免费" : `价格 ${chapter.price}`} · 更新 {formatDateLabel(chapter.updated_at)}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Link href={`/reviewer/chapters/${chapter.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  查看详情
                </Link>
                <button
                  className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400"
                  type="button"
                  disabled={operatingId === chapter.id}
                  onClick={() => void runAction(chapter.id, "claim")}
                >
                  领取审核
                </button>
                <button
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={operatingId === chapter.id}
                  onClick={() => void runAction(chapter.id, "approve")}
                >
                  通过
                </button>
                <button
                  className="rounded-lg bg-red-600 px-3 py-2 text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={operatingId === chapter.id}
                  onClick={() => setRejectTarget({ id: chapter.id, title: chapter.title })}
                >
                  驳回
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
        <button className={previous ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          上一页
        </button>
        <span className="text-zinc-500">共 {count} 章</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>

      <RejectDialog
        open={Boolean(rejectTarget)}
        title={`驳回章节${rejectTarget ? `：${rejectTarget.title}` : ""}`}
        submitting={Boolean(rejectTarget && operatingId === rejectTarget.id)}
        error={error}
        onCancel={() => setRejectTarget(null)}
        onConfirm={handleReject}
      />
    </div>
  );
}
