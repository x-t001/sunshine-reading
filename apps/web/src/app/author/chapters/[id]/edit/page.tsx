"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthorAuditHistory } from "@/components/AuthorAuditHistory";
import { AuthorLayout } from "@/components/AuthorLayout";
import { ChapterForm } from "@/components/ChapterForm";
import { getAuthorChapterDetail, submitAuthorChapter, updateAuthorChapter } from "@/lib/api/author";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AuthorChapterAuditStatus, AuthorChapterDetail, AuthorChapterStatus, UpdateAuthorChapterPayload } from "@/types/author";

const statusLabels: Record<AuthorChapterStatus, string> = {
  draft: "草稿",
  published: "已发布",
  hidden: "已隐藏",
};

const auditStatusLabels: Record<AuthorChapterAuditStatus, string> = {
  pending: "待审核",
  reviewing: "审核中",
  approved: "已通过",
  rejected: "已拒绝",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function EditAuthorChapterPage() {
  return (
    <AuthorLayout title="编辑章节" description="编辑章节草稿并提交审核。">
      <EditAuthorChapterContent />
    </AuthorLayout>
  );
}

function EditAuthorChapterContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [chapter, setChapter] = useState<AuthorChapterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadChapter = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setChapter(await getAuthorChapterDetail(id));
    } catch (loadError) {
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

  async function handleSave(payload: UpdateAuthorChapterPayload) {
    if (!id) {
      return false;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const nextChapter = await updateAuthorChapter(id, payload);
      setChapter(nextChapter);
      setNotice("章节已保存。");
      return true;
    } catch (updateError) {
      setError(getApiErrorMessage(updateError));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitReview() {
    if (!id) {
      return;
    }
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const result = await submitAuthorChapter(id);
      setNotice(`章节已提交审核，当前状态：${statusLabels[result.status]} / ${auditStatusLabels[result.audit_status]}`);
      await loadChapter();
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节...</section>;
  }

  if (!chapter) {
    return <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error || "章节不存在或无权访问。"}</section>;
  }

  return (
    <div className="space-y-4">
      <section className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold">{chapter.novel_title}</h2>
          <p className="mt-1 text-sm text-zinc-500">
            第 {chapter.chapter_number} 章 · {statusLabels[chapter.status]} / {auditStatusLabels[chapter.audit_status]}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/author/novels/${chapter.novel_id}/chapters`} className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-700">
            返回章节列表
          </Link>
          <button
            className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
            type="button"
            disabled={
              submitting ||
              chapter.audit_status === "pending" ||
              chapter.audit_status === "reviewing" ||
              chapter.audit_status === "approved"
            }
            onClick={() => void handleSubmitReview()}
          >
            {submitting ? "提交中..." : "提交审核"}
          </button>
        </div>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <AuthorAuditHistory logs={chapter.audit_logs} currentStatus={chapter.audit_status} />

      <ChapterForm
        key={chapter.id}
        draftStorageKey={`sunshine-reading:author-chapter:edit:${chapter.id}`}
        initialChapter={chapter}
        submitLabel="保存章节"
        submitting={saving}
        onSubmit={handleSave}
      />
    </div>
  );
}
