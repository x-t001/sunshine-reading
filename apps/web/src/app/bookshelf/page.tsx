"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getBookshelf, removeFromBookshelf } from "@/lib/api/bookshelf";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel } from "@/lib/utils/format";
import { useAuth } from "@/hooks/useAuth";
import type { BookshelfItem } from "@/types/bookshelf";

function coverUrl(item: BookshelfItem): string {
  if (item.novel.cover.startsWith("https://picsum.photos/")) {
    return item.novel.cover;
  }
  return `https://picsum.photos/seed/sunshine-${item.novel.id}/240/320`;
}

function readHref(item: BookshelfItem): string {
  if (item.last_read_chapter) {
    return `/novels/${item.novel.id}/chapters/${item.last_read_chapter.id}`;
  }
  return `/novels/${item.novel.id}`;
}

export default function BookshelfPage() {
  const { user, loading: authLoading, error: authError } = useAuth();
  const [items, setItems] = useState<BookshelfItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);

  const loadBookshelf = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await getBookshelf({ page: 1, page_size: 20 });
      setItems(page.results);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadBookshelf();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadBookshelf, user]);

  async function handleRemove(novelId: number) {
    setRemovingId(novelId);
    setError(null);
    try {
      await removeFromBookshelf(novelId);
      await loadBookshelf();
    } catch (removeError) {
      setError(getApiErrorMessage(removeError));
    } finally {
      setRemovingId(null);
    }
  }

  if (authLoading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在检查登录状态...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">我的书架</h1>
        <p className="mt-3 text-sm text-zinc-600">{authError || "当前未登录，请先登录后查看书架。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">我的书架</h1>
        <p className="mt-1 text-sm text-zinc-500">继续阅读已收藏的小说。</p>
      </div>

      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}

      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载书架...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">
          书架还是空的，去小说详情页加入喜欢的作品。
        </section>
      ) : null}

      <div className="grid gap-3">
        {items.map((item) => (
          <article key={item.id} className="flex gap-3 rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
            <Image
              src={coverUrl(item)}
              alt={item.novel.title}
              width={72}
              height={96}
              className="h-24 w-[72px] shrink-0 rounded-md object-cover"
            />
            <div className="min-w-0 flex-1">
              <Link href={`/novels/${item.novel.id}`} className="line-clamp-1 text-sm font-semibold text-zinc-900">
                {item.novel.title}
              </Link>
              <p className="mt-1 text-xs text-zinc-500">
                {item.novel.author.nickname || item.novel.author.username}
              </p>
              <p className="mt-2 text-xs text-zinc-600">
                最近阅读：{item.last_read_chapter?.title || "尚未开始"}
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                进度 {item.reading_progress} · 最近阅读 {item.last_read_at ? formatDateLabel(item.last_read_at) : "暂无"}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link href={readHref(item)} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-medium text-white">
                  继续阅读
                </Link>
                <button
                  className="rounded-lg border border-zinc-300 px-3 py-2 text-xs text-zinc-700 disabled:text-zinc-400"
                  type="button"
                  disabled={removingId === item.novel.id}
                  onClick={() => void handleRemove(item.novel.id)}
                >
                  {removingId === item.novel.id ? "移出中..." : "移出书架"}
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
