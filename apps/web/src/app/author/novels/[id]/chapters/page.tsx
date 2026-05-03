"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthorLayout } from "@/components/AuthorLayout";
import { getAuthorNovelChapters, getAuthorNovelDetail, submitAuthorChapter } from "@/lib/api/author";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { AuthorChapter, AuthorChapterAuditStatus, AuthorChapterStatus, AuthorNovelDetail } from "@/types/author";

const PAGE_SIZE = 10;

const statusLabels: Record<AuthorChapterStatus, string> = {
  draft: "草稿",
  published: "已发布",
  hidden: "已隐藏",
};

const auditStatusLabels: Record<AuthorChapterAuditStatus, string> = {
  pending: "审核中",
  approved: "已通过",
  rejected: "已拒绝",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function AuthorNovelChaptersPage() {
  return (
    <AuthorLayout title="章节管理" description="维护章节草稿，提交章节审核。">
      <AuthorNovelChaptersContent />
    </AuthorLayout>
  );
}

function AuthorNovelChaptersContent() {
  const params = useParams<{ id: string }>();
  const novelId = readRouteParam(params.id);
  const [novel, setNovel] = useState<AuthorNovelDetail | null>(null);
  const [chapters, setChapters] = useState<AuthorChapter[]>([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submittingId, setSubmittingId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    if (!novelId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [novelDetail, chapterPage] = await Promise.all([
        getAuthorNovelDetail(novelId),
        getAuthorNovelChapters(novelId, { page, page_size: PAGE_SIZE }),
      ]);
      setNovel(novelDetail);
      setChapters(chapterPage.results);
      setCount(chapterPage.count);
      setNext(chapterPage.next);
      setPrevious(chapterPage.previous);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [novelId, page]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadData();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadData]);

  async function handleSubmitReview(chapterId: number) {
    setSubmittingId(chapterId);
    setError(null);
    setNotice(null);
    try {
      const result = await submitAuthorChapter(chapterId);
      setNotice(`章节已提交审核，当前状态：${statusLabels[result.status]} / ${auditStatusLabels[result.audit_status]}`);
      await loadData();
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmittingId(null);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节...</section>;
  }

  if (error && !novel) {
    return <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</section>;
  }

  return (
    <div className="space-y-4">
      <section className="flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold">{novel?.title || "章节列表"}</h2>
          <p className="mt-1 text-sm text-zinc-500">共 {count} 章</p>
        </div>
        <Link href={`/author/novels/${novelId}/chapters/create`} className="rounded-lg bg-emerald-600 px-4 py-2 text-center text-sm font-medium text-white">
          创建章节
        </Link>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      {chapters.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">
          暂无章节。可以先创建第一章草稿。
        </section>
      ) : null}

      <div className="grid gap-3">
        {chapters.map((chapter) => (
          <article key={chapter.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <h3 className="line-clamp-1 text-base font-semibold">
                  第 {chapter.chapter_number} 章 {chapter.title}
                </h3>
                <p className="mt-1 text-sm text-zinc-500">
                  {formatWordCount(chapter.word_count)} · {statusLabels[chapter.status]} · {auditStatusLabels[chapter.audit_status]}
                </p>
                <p className="mt-1 text-xs text-zinc-400">
                  发布时间：{chapter.published_at ? formatDateLabel(chapter.published_at) : "未发布"} · 更新：{formatDateLabel(chapter.updated_at)}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Link href={`/author/chapters/${chapter.id}/edit`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  查看章节
                </Link>
                <Link href={`/author/chapters/${chapter.id}/edit`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                  编辑章节
                </Link>
                <button
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
                  type="button"
                  disabled={submittingId === chapter.id || chapter.audit_status === "approved"}
                  onClick={() => void handleSubmitReview(chapter.id)}
                >
                  {submittingId === chapter.id ? "提交中..." : "提交审核"}
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
        <span className="text-zinc-500">共 {count} 章</span>
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
