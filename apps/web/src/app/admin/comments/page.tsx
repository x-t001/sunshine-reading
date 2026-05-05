"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { getAdminComments, updateAdminCommentStatus } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminComment, AdminCommentListParams, AdminCommentStatus } from "@/types/admin";

const PAGE_SIZE = 10;

const commentStatusLabels: Record<AdminCommentStatus, string> = {
  normal: "正常",
  hidden: "已隐藏",
  deleted: "已删除",
};

type FilterState = {
  keyword: string;
  user_id: string;
  novel_id: string;
  chapter_id: string;
  status: AdminCommentStatus | "";
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

function buildParams(page: number, filters: FilterState): AdminCommentListParams {
  return {
    page,
    page_size: PAGE_SIZE,
    keyword: filters.keyword,
    user_id: filters.user_id,
    novel_id: filters.novel_id,
    chapter_id: filters.chapter_id,
    status: filters.status,
  };
}

export default function AdminCommentsPage() {
  return (
    <AdminLayout title="评论管理" description="查看评论内容，隐藏、恢复或标记删除评论。">
      <AdminCommentsContent />
    </AdminLayout>
  );
}

function AdminCommentsContent() {
  const [filters, setFilters] = useState<FilterState>({ keyword: "", user_id: "", novel_id: "", chapter_id: "", status: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AdminComment[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadComments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminComments(buildParams(page, query));
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
        await loadComments();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadComments]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(filters);
  }

  async function handleStatusChange(comment: AdminComment, status: AdminCommentStatus) {
    if (status === "hidden" && !window.confirm("确认隐藏这条评论？")) {
      return;
    }
    if (status === "deleted" && !window.confirm("确认将这条评论标记为删除？")) {
      return;
    }
    setOperatingId(comment.id);
    setError(null);
    setNotice(null);
    try {
      await updateAdminCommentStatus(comment.id, { status });
      setNotice(`评论状态已更新为 ${commentStatusLabels[status]}。`);
      await loadComments();
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
            placeholder="搜索评论、用户、小说或章节"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.user_id}
            onChange={(event) => setFilters((current) => ({ ...current, user_id: event.target.value }))}
            placeholder="用户 ID"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.novel_id}
            onChange={(event) => setFilters((current) => ({ ...current, novel_id: event.target.value }))}
            placeholder="小说 ID"
          />
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.chapter_id}
            onChange={(event) => setFilters((current) => ({ ...current, chapter_id: event.target.value }))}
            placeholder="章节 ID"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value as AdminCommentStatus | "" }))}
          >
            <option value="">全部状态</option>
            {Object.entries(commentStatusLabels).map(([status, label]) => (
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
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载评论列表...</p> : null}

      {!loading && items.length === 0 ? <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无数据</section> : null}

      {items.length > 0 ? (
        <section className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="min-w-[1100px] text-left text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-xs text-zinc-500">
              <tr>
                <th className="px-4 py-3">评论内容</th>
                <th className="px-4 py-3">用户</th>
                <th className="px-4 py-3">小说/章节</th>
                <th className="px-4 py-3">状态</th>
                <th className="px-4 py-3">时间</th>
                <th className="px-4 py-3">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {items.map((comment) => (
                <tr key={comment.id} className="align-top">
                  <td className="px-4 py-3">
                    <p className="line-clamp-3 max-w-sm text-zinc-900">{comment.content || "空评论"}</p>
                    <p className="mt-1 text-xs text-zinc-500">点赞 {comment.like_count}</p>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">
                    <p>{comment.nickname || comment.username || comment.user?.nickname || comment.user?.username || "未知用户"}</p>
                    <p className="mt-1 text-xs text-zinc-400">ID {comment.user_id}</p>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">
                    <p>{comment.novel_title || comment.novel?.title || "未知小说"}</p>
                    <p className="mt-1 text-xs text-zinc-400">{comment.chapter_title || comment.chapter?.title || "小说评论"}</p>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">{commentStatusLabels[comment.status]}</td>
                  <td className="px-4 py-3 text-xs leading-6 text-zinc-500">
                    <p>创建 {formatDateTime(comment.created_at)}</p>
                    <p>更新 {formatDateTime(comment.updated_at)}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/admin/comments/${comment.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                        查看详情
                      </Link>
                      {comment.status !== "hidden" ? (
                        <button className="rounded-lg border border-amber-300 px-3 py-2 text-amber-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operatingId === comment.id} onClick={() => void handleStatusChange(comment, "hidden")}>
                          隐藏
                        </button>
                      ) : null}
                      {comment.status !== "normal" ? (
                        <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operatingId === comment.id} onClick={() => void handleStatusChange(comment, "normal")}>
                          恢复
                        </button>
                      ) : null}
                      {comment.status !== "deleted" ? (
                        <button className="rounded-lg border border-red-300 px-3 py-2 text-red-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operatingId === comment.id} onClick={() => void handleStatusChange(comment, "deleted")}>
                          标记删除
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
        <button className={previous ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          上一页
        </button>
        <span className="text-zinc-500">共 {count} 条</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>
    </div>
  );
}
