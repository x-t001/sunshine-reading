"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getNovelChapters } from "@/lib/api/chapters";
import { addToBookshelf, checkInBookshelf } from "@/lib/api/bookshelf";
import { getNovelDetail } from "@/lib/api/novels";
import { getApiErrorMessage } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import type { ChapterCatalogItem } from "@/types/chapter";
import type { NovelDetail } from "@/types/novel";

function getCoverUrl(id: number, cover: string): string {
  if (cover.startsWith("https://picsum.photos/")) {
    return cover;
  }
  return `https://picsum.photos/seed/sunshine-${id}/240/320`;
}

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function NovelDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [novel, setNovel] = useState<NovelDetail | null>(null);
  const [chapters, setChapters] = useState<ChapterCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inBookshelf, setInBookshelf] = useState<boolean | null>(null);
  const [bookshelfError, setBookshelfError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!id) {
      return;
    }

    let active = true;
    void (async () => {
      await Promise.resolve();
      if (!active) {
        return;
      }
      setLoading(true);
      setError(null);
      setInBookshelf(null);
      setBookshelfError(null);
      try {
        const [novelDetail, chapterPage] = await Promise.all([getNovelDetail(id), getNovelChapters(id, { page_size: 50 })]);
        if (!active) {
          return;
        }
        setNovel(novelDetail);
        setChapters(chapterPage.results);
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
  }, [id]);

  useEffect(() => {
    if (!novel || !getAccessToken()) {
      return;
    }

    let active = true;
    void (async () => {
      await Promise.resolve();
      if (!active) {
        return;
      }
      setBookshelfError(null);
      try {
        const result = await checkInBookshelf(novel.id);
        if (active) {
          setInBookshelf(result.in_bookshelf);
        }
      } catch (checkError) {
        if (active) {
          setBookshelfError(getApiErrorMessage(checkError));
          setInBookshelf(null);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [novel]);

  const firstChapter = chapters[0];
  const cover = useMemo(() => (novel ? getCoverUrl(novel.id, novel.cover) : ""), [novel]);

  async function handleAddToBookshelf() {
    if (!novel) {
      return;
    }
    if (!getAccessToken()) {
      router.push("/login");
      return;
    }
    if (inBookshelf) {
      return;
    }

    setAdding(true);
    setBookshelfError(null);
    try {
      await addToBookshelf(novel.id);
      setInBookshelf(true);
    } catch (addError) {
      setBookshelfError(getApiErrorMessage(addError));
    } finally {
      setAdding(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载小说详情...</section>;
  }

  if (error || !novel) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        小说详情加载失败：{error || "小说不存在或暂不可访问。"}
      </section>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex gap-3">
          <Image
            src={cover}
            alt={novel.title}
            width={96}
            height={144}
            priority
            className="h-36 w-24 shrink-0 rounded-lg object-cover"
          />
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-semibold">{novel.title}</h1>
            <p className="mt-1 text-sm text-zinc-600">作者：{novel.author.nickname || novel.author.username}</p>
            <p className="text-sm text-zinc-600">分类：{novel.category?.name ?? "未分类"}</p>
            <p className="text-sm text-zinc-600">字数：{formatWordCount(novel.word_count)}</p>
            <p className="text-sm text-zinc-600">状态：{novel.status}</p>
            <p className="text-sm text-zinc-600">
              更新：{formatDateLabel(novel.latest_chapter_updated_at || novel.updated_at)}
            </p>
          </div>
        </div>

        <p className="mt-3 text-sm leading-6 text-zinc-700">{novel.description}</p>
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-zinc-600">
          <span className="rounded-lg bg-zinc-100 px-2 py-1">阅读 {novel.view_count}</span>
          <span className="rounded-lg bg-zinc-100 px-2 py-1">收藏 {novel.collect_count}</span>
          <span className="rounded-lg bg-zinc-100 px-2 py-1">评分 {novel.rating_score}</span>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href={firstChapter ? `/novels/${novel.id}/chapters/${firstChapter.id}` : "#"}
            className={
              firstChapter
                ? "rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white"
                : "pointer-events-none rounded-lg bg-zinc-300 px-4 py-2 text-sm font-medium text-white"
            }
          >
            开始阅读
          </Link>
          <button
            className={
              inBookshelf
                ? "rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-700"
                : "rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700 disabled:text-zinc-400"
            }
            type="button"
            disabled={adding || Boolean(inBookshelf)}
            onClick={() => void handleAddToBookshelf()}
          >
            {inBookshelf ? "已加入书架" : adding ? "加入中..." : "加入书架"}
          </button>
        </div>
        {bookshelfError ? <p className="mt-3 text-sm text-red-600">{bookshelfError}</p> : null}
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-base font-semibold">章节列表</h2>
        {chapters.length === 0 ? (
          <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500">
            暂无可阅读章节，稍后再来看看。
          </p>
        ) : (
          <ul className="space-y-2">
            {chapters.map((chapter) => (
              <li key={chapter.id}>
                <Link
                  href={`/novels/${novel.id}/chapters/${chapter.id}`}
                  className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                >
                  <span className="line-clamp-1">{chapter.title}</span>
                  <span className="shrink-0 text-xs text-zinc-500">{formatWordCount(chapter.word_count)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
