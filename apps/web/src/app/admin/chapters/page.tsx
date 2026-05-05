"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { getAdminChapters, updateAdminChapterStatus } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminAuditStatus, AdminChapter, AdminChapterListParams, AdminChapterStatus } from "@/types/admin";

const PAGE_SIZE = 10;

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

type FilterState = {
  keyword: string;
  novel_id: string;
  author_id: string;
  status: AdminChapterStatus | "";
  audit_status: AdminAuditStatus | "";
};

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

function buildParams(page: number, filters: FilterState): AdminChapterListParams {
  return {
    page,
    page_size: PAGE_SIZE,
    keyword: filters.keyword,
    novel_id: filters.novel_id,
    author_id: filters.author_id,
    status: filters.status,
    audit_status: filters.audit_status,
  };
}

export default function AdminChaptersPage() {
  return (
    <AdminLayout title="章节管理" description="查看章节内容，隐藏或恢复章节状态。">
      <AdminChaptersContent />
    </AdminLayout>
  );
}

function AdminChaptersContent() {
  const [filters, setFilters] = useState<FilterState>({ keyword: "", novel_id: "", author_id: "", status: "", audit_status: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AdminChapter[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [statusDrafts, setStatusDrafts] = useState<Record<number, AdminChapterStatus>>({});
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadChapters = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminChapters(buildParams(page, query));
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
      setStatusDrafts(
        result.results.reduce<Record<number, AdminChapterStatus>>((drafts, chapter) => {
          drafts[chapter.id] = chapter.status;
          return drafts;
        }, {}),
      );
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

  async function handleStatusSave(chapter: AdminChapter) {
    const nextStatus = statusDrafts[chapter.id] || chapter.status;
    if (nextStatus === "hidden" && !window.confirm(`确认隐藏章节「${chapter.title}」？`)) {
      return;
    }
    setOperatingId(chapter.id);
    setError(null);
    setNotice(null);
    try {
      await updateAdminChapterStatus(chapter.id, { status: nextStatus });
      setNotice(`章节「${chapter.title}」状态已更新为 ${chapterStatusLabels[nextStatus]}。`);
      await loadChapters();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperatingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="grid gap-3 md:grid-cols-6" onSubmit={handleSearch}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={filters.keyword}
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="搜索章节、小说或作者"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.novel_id}
            onChange={(event) => setFilters((current) => ({ ...current, novel_id: event.target.value }))}
            placeholder="小说 ID"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.author_id}
            onChange={(event) => setFilters((current) => ({ ...current, author_id: event.target.value }))}
            placeholder="作者 ID"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as AdminChapterStatus | "" }))}
          >
            <option value="">全部状态</option>
            {Object.entries(chapterStatusLabels).map(([status, label]) => (
              <option key={status} value={status}>
                {label}
              </option>
            ))}
          </select>
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.audit_status}
            onChange={(event) => setFilters((current) => ({ ...current, audit_status: event.target.value as AdminAuditStatus | "" }))}
          >
            <option value="">全部审核</option>
            {Object.entries(auditStatusLabels).map(([status, label]) => (
              <option key={status} value={status}>
                {label}
              </option>
            ))}
          </select>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white md:col-span-6" type="submit">
            筛选
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节列表...</p> : null}

      {!loading && items.length === 0 ? <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无数据</section> : null}

      {items.length > 0 ? (
        <section className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="min-w-[1120px] text-left text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500">
              <tr>
                <th className="px-4 py-3">章节</th>
                <th className="px-4 py-3">小说/作者</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">属性</th>
                <th className="px-4 py-3">时间</th>
                <th className="px-4 py-3">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {items.map((chapter) => {
                const draftStatus = statusDrafts[chapter.id] || chapter.status;
                return (
                  <tr key={chapter.id} className="align-top">
                    <td className="px-4 py-3">
                      <p className="max-w-xs font-medium text-zinc-900">第 {chapter.chapter_number} 章 {chapter.title}</p>
                      <p className="mt-1 text-xs text-zinc-500">{chapter.word_count} 字</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-600">
                      <p>{chapter.novel_title || chapter.novel?.title || "未知小说"}</p>
                      <p className="mt-1 text-xs text-zinc-400">{chapter.author_username || "未知作者"}</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-600">
                      <p>{chapterStatusLabels[chapter.status]}</p>
                      <p className="mt-1 text-xs text-zinc-400">{auditStatusLabels[chapter.audit_status]}</p>
                    </td>
                    <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                      <p>{chapter.is_free ? "免费" : `付费 ${chapter.price}`}</p>
                      <p>发布：{formatDateTime(chapter.published_at)}</p>
                    </td>
                    <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                      <p>创建 {formatDateTime(chapter.created_at)}</p>
                      <p>更新 {formatDateTime(chapter.updated_at)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Link href={`/admin/chapters/${chapter.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                          查看详情
                        </Link>
                        <select
                          className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                          value={draftStatus}
                          disabled={operatingId === chapter.id}
                          onChange={(event) => setStatusDrafts((current) => ({ ...current, [chapter.id]: event.target.value as AdminChapterStatus }))}
                        >
                          {Object.entries(chapterStatusLabels).map(([status, label]) => (
                            <option key={status} value={status}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operatingId === chapter.id || draftStatus === chapter.status} onClick={() => void handleStatusSave(chapter)}>
                          保存状态
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ) : null}

      <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
        <button className={previous ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          上一页
        </button>
        <span className="text-zinc-500">共 {count} 章</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>
    </div>
  );
}
