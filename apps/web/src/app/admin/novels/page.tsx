"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { getAdminNovels, updateAdminNovelFeatured, updateAdminNovelStatus } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminAuditStatus, AdminNovel, AdminNovelListParams, AdminNovelStatus } from "@/types/admin";

const PAGE_SIZE = 10;

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

type FilterState = {
  keyword: string;
  status: AdminNovelStatus | "";
  audit_status: AdminAuditStatus | "";
  author_id: string;
  category: string;
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

function buildParams(page: number, filters: FilterState): AdminNovelListParams {
  return {
    page,
    page_size: PAGE_SIZE,
    keyword: filters.keyword,
    status: filters.status,
    audit_status: filters.audit_status,
    author_id: filters.author_id,
    category: filters.category,
  };
}

export default function AdminNovelsPage() {
  return (
    <AdminLayout title="小说管理" description="查看小说内容，调整状态，并设置推荐。">
      <AdminNovelsContent />
    </AdminLayout>
  );
}

function AdminNovelsContent() {
  const [filters, setFilters] = useState<FilterState>({ keyword: "", status: "", audit_status: "", author_id: "", category: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AdminNovel[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [statusDrafts, setStatusDrafts] = useState<Record<number, AdminNovelStatus>>({});
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadNovels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminNovels(buildParams(page, query));
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
      setStatusDrafts(
        result.results.reduce<Record<number, AdminNovelStatus>>((drafts, novel) => {
          drafts[novel.id] = novel.status;
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
    setQuery(filters);
  }

  async function handleStatusSave(novel: AdminNovel) {
    const nextStatus = statusDrafts[novel.id] || novel.status;
    if (nextStatus === "removed" && !window.confirm(`确认下架小说「${novel.title}」？`)) {
      return;
    }
    setOperatingId(novel.id);
    setError(null);
    setNotice(null);
    try {
      await updateAdminNovelStatus(novel.id, { status: nextStatus });
      setNotice(`小说「${novel.title}」状态已更新为 ${novelStatusLabels[nextStatus]}。`);
      await loadNovels();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperatingId(null);
    }
  }

  async function handleFeatured(novel: AdminNovel, isFeatured: boolean) {
    setOperatingId(novel.id);
    setError(null);
    setNotice(null);
    try {
      await updateAdminNovelFeatured(novel.id, { is_featured: isFeatured });
      setNotice(`小说「${novel.title}」已${isFeatured ? "设为推荐" : "取消推荐"}。`);
      await loadNovels();
    } catch (featuredError) {
      setError(getApiErrorMessage(featuredError));
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
            placeholder="搜索标题、简介或作者"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as AdminNovelStatus | "" }))}
          >
            <option value="">全部状态</option>
            {Object.entries(novelStatusLabels).map(([status, label]) => (
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
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.author_id}
            onChange={(event) => setFilters((current) => ({ ...current, author_id: event.target.value }))}
            placeholder="作者 ID"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.category}
            onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}
            placeholder="分类 ID/slug"
          />
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white md:col-span-6" type="submit">
            筛选
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载小说列表...</p> : null}

      {!loading && items.length === 0 ? <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无数据</section> : null}

      {items.length > 0 ? (
        <section className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="min-w-[1180px] text-left text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500">
              <tr>
                <th className="px-4 py-3">小说</th>
                <th className="px-4 py-3">作者/分类</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">统计</th>
                <th className="px-4 py-3">时间</th>
                <th className="px-4 py-3">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {items.map((novel) => {
                const draftStatus = statusDrafts[novel.id] || novel.status;
                return (
                  <tr key={novel.id} className="align-top">
                    <td className="px-4 py-3">
                      <p className="max-w-xs font-medium text-zinc-900">{novel.title}</p>
                      <p className="mt-1 text-xs text-zinc-500">最新：{novel.latest_chapter_title || "暂无"}</p>
                      <p className="mt-1 text-xs text-zinc-500">{novel.is_featured ? "已推荐" : "未推荐"}</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-600">
                      <p>{novel.author_nickname || novel.author_username || "未知作者"}</p>
                      <p className="mt-1 text-xs text-zinc-400">{novel.category?.name || "未分类"}</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-600">
                      <p>{novelStatusLabels[novel.status]}</p>
                      <p className="mt-1 text-xs text-zinc-400">{auditStatusLabels[novel.audit_status]}</p>
                    </td>
                    <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                      <p>字数 {novel.word_count}</p>
                      <p>阅读 {novel.view_count} / 收藏 {novel.collect_count}</p>
                      <p>评论 {novel.comment_count} / 评分 {novel.rating_score}</p>
                    </td>
                    <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                      <p>创建 {formatDateTime(novel.created_at)}</p>
                      <p>更新 {formatDateTime(novel.updated_at)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Link href={`/admin/novels/${novel.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                          查看详情
                        </Link>
                        <select
                          className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                          value={draftStatus}
                          disabled={operatingId === novel.id}
                          onChange={(event) => setStatusDrafts((current) => ({ ...current, [novel.id]: event.target.value as AdminNovelStatus }))}
                        >
                          {Object.entries(novelStatusLabels).map(([status, label]) => (
                            <option key={status} value={status}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operatingId === novel.id || draftStatus === novel.status} onClick={() => void handleStatusSave(novel)}>
                          保存状态
                        </button>
                        <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operatingId === novel.id} onClick={() => void handleFeatured(novel, !novel.is_featured)}>
                          {novel.is_featured ? "取消推荐" : "设置推荐"}
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
        <span className="text-zinc-500">共 {count} 本</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>
    </div>
  );
}
