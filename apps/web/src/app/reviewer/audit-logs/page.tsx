"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ReviewerLayout } from "@/components/ReviewerLayout";
import { getAuditLogs } from "@/lib/api/reviewer";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel } from "@/lib/utils/format";
import type { AuditAction, AuditContentType, AuditLog, GetAuditLogsParams } from "@/types/reviewer";

const PAGE_SIZE = 10;

const contentTypeLabels: Record<AuditContentType, string> = {
  novel: "作品",
  chapter: "章节",
};

const actionLabels: Record<AuditAction, string> = {
  submit: "提交审核",
  claim: "领取审核",
  approve: "审核通过",
  reject: "审核驳回",
};

type FilterState = {
  content_type: "" | AuditContentType;
  action: "" | AuditAction;
};

export default function ReviewerAuditLogsPage() {
  return (
    <ReviewerLayout title="审核记录" description="查看审核流程中的状态流转历史。">
      <ReviewerAuditLogsContent />
    </ReviewerLayout>
  );
}

function ReviewerAuditLogsContent() {
  const [filters, setFilters] = useState<FilterState>({ content_type: "", action: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AuditLog[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: GetAuditLogsParams = {
        page,
        page_size: PAGE_SIZE,
        content_type: query.content_type,
        action: query.action,
      };
      const result = await getAuditLogs(params);
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
        await loadLogs();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadLogs]);

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(filters);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="grid gap-3 md:grid-cols-3" onSubmit={handleFilterSubmit}>
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={filters.content_type}
            onChange={(event) => setFilters((current) => ({ ...current, content_type: event.target.value as FilterState["content_type"] }))}
          >
            <option value="">全部对象</option>
            <option value="novel">作品</option>
            <option value="chapter">章节</option>
          </select>
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={filters.action}
            onChange={(event) => setFilters((current) => ({ ...current, action: event.target.value as FilterState["action"] }))}
          >
            <option value="">全部操作</option>
            <option value="submit">提交审核</option>
            <option value="claim">领取审核</option>
            <option value="approve">审核通过</option>
            <option value="reject">审核驳回</option>
          </select>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>
      </section>

      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载审核记录...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无审核记录。</section>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
        <div className="hidden grid-cols-[0.8fr_0.8fr_1fr_1fr_1fr_1fr_2fr_1fr] gap-3 border-b border-zinc-100 px-4 py-3 text-xs font-medium text-zinc-500 md:grid">
          <span>对象类型</span>
          <span>对象 ID</span>
          <span>审核员</span>
          <span>操作</span>
          <span>原状态</span>
          <span>新状态</span>
          <span>原因</span>
          <span>时间</span>
        </div>
        {items.map((log) => (
          <article key={log.id} className="grid gap-2 border-b border-zinc-100 px-4 py-3 text-sm last:border-b-0 md:grid-cols-[0.8fr_0.8fr_1fr_1fr_1fr_1fr_2fr_1fr] md:gap-3">
            <span>{contentTypeLabels[log.content_type]}</span>
            <span className="text-zinc-500">#{log.object_id}</span>
            <span>{log.reviewer?.nickname || log.reviewer?.username || "系统"}</span>
            <span>{actionLabels[log.action]}</span>
            <span className="text-zinc-500">{log.from_status || "-"}</span>
            <span className="text-zinc-500">{log.to_status || "-"}</span>
            <span className="line-clamp-2 text-zinc-600">{log.reason || "-"}</span>
            <span className="text-zinc-400">{formatDateLabel(log.created_at)}</span>
          </article>
        ))}
      </div>

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
