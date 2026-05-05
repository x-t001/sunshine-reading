"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { getAdminCommentDetail, updateAdminCommentStatus } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminCommentDetail, AdminCommentStatus } from "@/types/admin";

const commentStatusLabels: Record<AdminCommentStatus, string> = {
  normal: "正常",
  hidden: "已隐藏",
  deleted: "已删除",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

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

export default function AdminCommentDetailPage() {
  return (
    <AdminLayout title="评论详情" description="查看评论上下文，并调整评论状态。">
      <AdminCommentDetailContent />
    </AdminLayout>
  );
}

function AdminCommentDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [comment, setComment] = useState<AdminCommentDetail | null>(null);
  const [statusDraft, setStatusDraft] = useState<AdminCommentStatus>("normal");
  const [loading, setLoading] = useState(true);
  const [operating, setOperating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadComment = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminCommentDetail(id);
      setComment(result);
      setStatusDraft(result.status);
    } catch (loadError) {
      setComment(null);
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
        await loadComment();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadComment]);

  async function handleStatusSave(nextStatus = statusDraft) {
    if (!comment) {
      return;
    }
    if (nextStatus === "hidden" && !window.confirm("确认隐藏这条评论？")) {
      return;
    }
    if (nextStatus === "deleted" && !window.confirm("确认将这条评论标记为删除？")) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await updateAdminCommentStatus(comment.id, { status: nextStatus });
      setNotice(`评论状态已更新为 ${commentStatusLabels[nextStatus]}。`);
      await loadComment();
    } catch (statusError) {
      setError(getApiErrorMessage(statusError));
    } finally {
      setOperating(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载评论详情...</section>;
  }

  if (!comment) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error || "评论不存在或无权访问。"}
      </section>
    );
  }

  const displayUser = comment.nickname || comment.username || comment.user?.nickname || comment.user?.username || "未知用户";

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">评论 #{comment.id}</h2>
            <p className="mt-2 text-sm text-zinc-500">
              用户：{displayUser} · 状态：{commentStatusLabels[comment.status]} · 点赞 {comment.like_count}
            </p>
            <p className="mt-1 text-sm text-zinc-500">
              小说：{comment.novel_title || comment.novel?.title || "未知小说"} · 章节：{comment.chapter_title || comment.chapter?.title || "小说评论"}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2 text-sm">
            <Link href="/admin/comments" className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
              返回列表
            </Link>
            <select
              className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
              value={statusDraft}
              disabled={operating}
              onChange={(event) => setStatusDraft(event.target.value as AdminCommentStatus)}
            >
              {Object.entries(commentStatusLabels).map(([status, label]) => (
                <option key={status} value={status}>
                  {label}
                </option>
              ))}
            </select>
            <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating || statusDraft === comment.status} onClick={() => void handleStatusSave()}>
              保存状态
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h3 className="text-base font-semibold">评论内容</h3>
        <p className="mt-4 max-w-4xl whitespace-pre-wrap break-words text-sm leading-7 text-zinc-700">{comment.content || "空评论"}</p>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <InfoCard label="用户 ID" value={`${comment.user_id}`} />
        <InfoCard label="小说 ID" value={`${comment.novel_id}`} />
        <InfoCard label="章节 ID" value={comment.chapter_id ? `${comment.chapter_id}` : "无"} />
        <InfoCard label="父评论" value={comment.parent ? `#${comment.parent}` : "无"} />
        <InfoCard label="创建时间" value={formatDateTime(comment.created_at)} />
        <InfoCard label="更新时间" value={formatDateTime(comment.updated_at)} />
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-wrap gap-2 text-sm">
          {comment.status !== "hidden" ? (
            <button className="rounded-lg border border-amber-300 px-3 py-2 text-amber-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operating} onClick={() => void handleStatusSave("hidden")}>
              隐藏
            </button>
          ) : null}
          {comment.status !== "normal" ? (
            <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operating} onClick={() => void handleStatusSave("normal")}>
              恢复
            </button>
          ) : null}
          {comment.status !== "deleted" ? (
            <button className="rounded-lg border border-red-300 px-3 py-2 text-red-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operating} onClick={() => void handleStatusSave("deleted")}>
              标记删除
            </button>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-zinc-900">{value}</p>
    </div>
  );
}
