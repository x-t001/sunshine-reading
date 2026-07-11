"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AuthorLayout } from "@/components/AuthorLayout";
import { getAuthorNovels, submitAuthorNovel } from "@/lib/api/author";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { AuthorNovel, GetAuthorNovelsParams } from "@/types/author";
import type { NovelAuditStatus, NovelStatus } from "@/types/novel";

const PAGE_SIZE = 10;

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

type FilterState = {
  keyword: string;
  status: string;
  audit_status: string;
};

export default function AuthorNovelsPage() {
  return (
    <AuthorLayout title="我的作品" description="管理作品草稿、审核状态和章节入口。">
      <AuthorNovelsContent />
    </AuthorLayout>
  );
}

function AuthorNovelsContent() {
  const [filters, setFilters] = useState<FilterState>({ keyword: "", status: "", audit_status: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AuthorNovel[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submittingId, setSubmittingId] = useState<number | null>(null);

  const loadNovels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: GetAuthorNovelsParams = {
        page,
        page_size: PAGE_SIZE,
        keyword: query.keyword,
        status: query.status,
        audit_status: query.audit_status,
      };
      const novelPage = await getAuthorNovels(params);
      setItems(novelPage.results);
      setCount(novelPage.count);
      setNext(novelPage.next);
      setPrevious(novelPage.previous);
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
        await loadNovels();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadNovels]);

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(filters);
  }

  async function handleSubmitReview(id: number) {
    setSubmittingId(id);
    setError(null);
    setNotice(null);
    try {
      const result = await submitAuthorNovel(id);
      setNotice(`作品已提交审核，当前审核状态：${auditStatusLabels[result.audit_status]}`);
      await loadNovels();
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmittingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="grid gap-3 md:grid-cols-5" onSubmit={handleFilterSubmit}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={filters.keyword}
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="搜索标题或简介"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
          >
            <option value="">全部状态</option>
            <option value="serializing">连载中</option>
            <option value="completed">已完结</option>
            <option value="paused">暂停</option>
          </select>
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={filters.audit_status}
            onChange={(event) => setFilters((current) => ({ ...current, audit_status: event.target.value }))}
          >
            <option value="">全部审核</option>
            <option value="draft">草稿</option>
            <option value="pending">审核中</option>
            <option value="approved">已通过</option>
            <option value="rejected">已拒绝</option>
          </select>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载作品...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">
          暂无作品。可以先创建一本小说草稿。
        </section>
      ) : null}

      <div className="grid gap-3">
        {items.map((novel) => (
          <article key={novel.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <h2 className="line-clamp-1 text-base font-semibold">{novel.title}</h2>
                <p className="mt-1 text-sm text-zinc-500">
                  {novel.category?.name || "未分类"} · {statusLabels[novel.status]} · {auditStatusLabels[novel.audit_status]}
                </p>
                <p className="mt-2 text-xs text-zinc-500">
                  {formatWordCount(novel.word_count)} · 阅读 {novel.view_count} · 评论 {novel.comment_count} · 评分 {novel.rating_score}（{novel.rating_count} 人）
                </p>
                <p className="mt-1 text-xs text-zinc-400">更新：{formatDateLabel(novel.updated_at)}</p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Link href={`/author/novels/${novel.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  查看详情
                </Link>
                <Link href={`/author/novels/${novel.id}/edit`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  编辑作品
                </Link>
                <Link href={`/author/novels/${novel.id}/chapters`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  章节管理
                </Link>
                <button
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={submittingId === novel.id || novel.audit_status === "pending" || novel.audit_status === "approved"}
                  onClick={() => void handleSubmitReview(novel.id)}
                >
                  {submittingId === novel.id ? "提交中..." : "提交审核"}
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
        <button
          className={previous ? "text-emerald-600" : "pointer-events-none text-zinc-400"}
          type="button"
          disabled={!previous}
          onClick={() => setPage((current) => Math.max(1, current - 1))}
        >
          上一页
        </button>
        <span className="text-zinc-500">共 {count} 本</span>
        <button
          className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"}
          type="button"
          disabled={!next}
          onClick={() => setPage((current) => current + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  );
}
