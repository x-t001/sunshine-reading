"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { RejectDialog } from "@/components/RejectDialog";
import { ReviewerLayout } from "@/components/ReviewerLayout";
import { approveNovel, claimNovel, getPendingNovels, rejectNovel } from "@/lib/api/reviewer";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { GetPendingNovelsParams, PendingNovel, ReviewAuditStatus } from "@/types/reviewer";

const PAGE_SIZE = 10;

const auditStatusLabels: Record<ReviewAuditStatus, string> = {
  draft: "草稿",
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已驳回",
};

type RejectTarget = {
  id: number;
  title: string;
} | null;

export default function ReviewerNovelsPage() {
  return (
    <ReviewerLayout title="待审核作品" description="处理作者提交的作品审核任务。">
      <ReviewerNovelsContent />
    </ReviewerLayout>
  );
}

function ReviewerNovelsContent() {
  const router = useRouter();
  const [keyword, setKeyword] = useState("");
  const [queryKeyword, setQueryKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PendingNovel[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [rejectTarget, setRejectTarget] = useState<RejectTarget>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadNovels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: GetPendingNovelsParams = {
        page,
        page_size: PAGE_SIZE,
        keyword: queryKeyword,
      };
      const result = await getPendingNovels(params);
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [page, queryKeyword]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadNovels();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadNovels]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQueryKeyword(keyword);
  }

  async function runAction(id: number, action: "claim" | "approve") {
    setOperatingId(id);
    setError(null);
    setNotice(null);
    try {
      const result = action === "claim" ? await claimNovel(id) : await approveNovel(id);
      setNotice(`作品“${result.title}”已${action === "claim" ? "领取" : "通过"}，当前状态：${auditStatusLabels[result.audit_status]}`);
      if (action === "claim") {
        router.push(`/reviewer/novels/${id}`);
        return;
      }
      await loadNovels();
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
      const result = await rejectNovel(rejectTarget.id, { reason });
      setNotice(`作品“${result.title}”已驳回。`);
      setRejectTarget(null);
      await loadNovels();
    } catch (rejectError) {
      setError(getApiErrorMessage(rejectError));
    } finally {
      setOperatingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="flex flex-col gap-3 md:flex-row" onSubmit={handleSearch}>
          <input
            className="min-w-0 flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索作品标题、简介或作者"
          />
          <button className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white" type="submit">
            搜索
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载待审核作品...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无待审核作品。</section>
      ) : null}

      <div className="grid gap-3">
        {items.map((novel) => (
          <article key={novel.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <h2 className="line-clamp-1 text-base font-semibold">{novel.title}</h2>
                <p className="mt-1 text-sm text-zinc-500">
                  作者：{novel.author?.nickname || novel.author?.username || "未知"} · 分类：{novel.category?.name || "未分类"} · {auditStatusLabels[novel.audit_status]}
                </p>
                <p className="mt-2 text-xs text-zinc-500">
                  {formatWordCount(novel.word_count)} · 阅读 {novel.view_count} · 评分 {novel.rating_score} / {novel.rating_count} 人
                </p>
                <p className="mt-1 text-xs text-zinc-400">更新：{formatDateLabel(novel.updated_at)}</p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Link href={`/reviewer/novels/${novel.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  查看详情
                </Link>
                <button
                  className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400"
                  type="button"
                  disabled={operatingId === novel.id}
                  onClick={() => void runAction(novel.id, "claim")}
                >
                  领取审核
                </button>
                <button
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={operatingId === novel.id}
                  onClick={() => void runAction(novel.id, "approve")}
                >
                  通过
                </button>
                <button
                  className="rounded-lg bg-red-600 px-3 py-2 text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={operatingId === novel.id}
                  onClick={() => setRejectTarget({ id: novel.id, title: novel.title })}
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
        <span className="text-zinc-500">共 {count} 本</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>

      <RejectDialog
        open={Boolean(rejectTarget)}
        title={`驳回作品${rejectTarget ? `：${rejectTarget.title}` : ""}`}
        submitting={Boolean(rejectTarget && operatingId === rejectTarget.id)}
        error={error}
        onCancel={() => setRejectTarget(null)}
        onConfirm={handleReject}
      />
    </div>
  );
}
