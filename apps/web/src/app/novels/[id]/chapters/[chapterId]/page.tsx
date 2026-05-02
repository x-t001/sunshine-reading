"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ReadingToolbar } from "@/components/ReadingToolbar";
import { getChapterDetail } from "@/lib/api/chapters";
import { reportReadingHistory } from "@/lib/api/reading-history";
import { getApiErrorMessage } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type { ChapterDetail } from "@/types/chapter";

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function ReadingPage() {
  const params = useParams<{ id: string; chapterId: string }>();
  const id = readRouteParam(params.id);
  const chapterId = readRouteParam(params.chapterId);
  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const reportedRef = useRef(false);

  useEffect(() => {
    if (!chapterId) {
      return;
    }

    let active = true;
    reportedRef.current = false;

    void (async () => {
      await Promise.resolve();
      if (!active) {
        return;
      }
      setLoading(true);
      setError(null);
      setSyncError(null);
      try {
        const chapterDetail = await getChapterDetail(chapterId);
        if (!active) {
          return;
        }
        if (String(chapterDetail.novel.id) !== id) {
          setChapter(null);
          setError("章节与小说不匹配。");
          return;
        }
        setChapter(chapterDetail);
      } catch (loadError) {
        if (active) {
          setError(getApiErrorMessage(loadError));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [chapterId, id]);

  useEffect(() => {
    if (!chapter || reportedRef.current || !getAccessToken()) {
      return;
    }

    reportedRef.current = true;
    void reportReadingHistory({
      novel_id: Number(id),
      chapter_id: Number(chapterId),
      reading_position: 0,
    }).catch((reportError) => {
      setSyncError(getApiErrorMessage(reportError));
    });
  }, [chapter, chapterId, id]);

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节...</section>;
  }

  if (error || !chapter) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        章节加载失败：{error || "章节不存在或暂不可访问。"}
      </section>
    );
  }

  return (
    <article className="mx-auto max-w-3xl rounded-xl bg-white p-4 shadow-sm">
      <p className="text-xs text-zinc-500">{chapter.novel.title}</p>
      <h1 className="mt-1 text-xl font-semibold">{chapter.title}</h1>
      <p className="mt-2 text-xs text-zinc-500">
        {chapter.is_free ? "免费章节" : `付费章节 ${chapter.price}`} · {chapter.word_count} 字
      </p>
      {syncError ? <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">阅读历史同步失败：{syncError}</p> : null}

      <div className="mt-4 space-y-4 text-[18px] leading-8 text-zinc-800">
        {chapter.content.split(/\n{2,}/).map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>

      <div className="mt-8 grid grid-cols-3 gap-2 text-sm">
        <Link
          href={chapter.previous_chapter_id ? `/novels/${id}/chapters/${chapter.previous_chapter_id}` : "#"}
          className={
            chapter.previous_chapter_id
              ? "rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700"
              : "pointer-events-none rounded-lg border border-zinc-200 px-3 py-2 text-center text-zinc-400"
          }
        >
          上一章
        </Link>
        <Link href={`/novels/${id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700">
          目录
        </Link>
        <Link
          href={chapter.next_chapter_id ? `/novels/${id}/chapters/${chapter.next_chapter_id}` : "#"}
          className={
            chapter.next_chapter_id
              ? "rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700"
              : "pointer-events-none rounded-lg border border-zinc-200 px-3 py-2 text-center text-zinc-400"
          }
        >
          下一章
        </Link>
      </div>

      <ReadingToolbar />
    </article>
  );
}
