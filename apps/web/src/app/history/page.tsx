"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getReadingHistory } from "@/lib/api/reading-history";
import { getApiErrorMessage } from "@/lib/api/request";
import { getNovelCoverUrl } from "@/lib/utils/cover";
import { formatDateLabel } from "@/lib/utils/format";
import { useAuth } from "@/hooks/useAuth";
import type { ReadingHistoryItem } from "@/types/reading-history";

function formatProgress(value: number): string {
  if (!Number.isFinite(value)) {
    return "暂无";
  }
  return `${Math.max(0, Math.min(100, Math.round(value)))}%`;
}

export default function HistoryPage() {
  const { user, loading: authLoading, error: authError } = useAuth();
  const [items, setItems] = useState<ReadingHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
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
      try {
        const page = await getReadingHistory({ page: 1, page_size: 20 });
        if (active) {
          setItems(page.results);
        }
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
  }, [user]);

  if (authLoading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在检查登录状态...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">阅读历史</h1>
        <p className="mt-3 text-sm text-zinc-600">{authError || "当前未登录，请先登录后查看阅读历史。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">阅读历史</h1>
        <p className="mt-1 text-sm text-zinc-500">按最近阅读时间排序。</p>
      </div>

      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载阅读历史...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">
          暂无阅读历史。打开任意公开章节后会自动记录。
        </section>
      ) : null}

      <div className="grid gap-3">
        {items.map((item) => (
          <article key={item.id} className="flex gap-3 rounded-xl border border-zinc-200 bg-white p-3 shadow-sm">
            <Image
              src={getNovelCoverUrl(item.novel.cover)}
              alt={item.novel.title}
              width={64}
              height={88}
              className="h-24 w-16 shrink-0 rounded-md object-cover"
            />
            <div className="min-w-0 flex-1">
              <Link href={`/novels/${item.novel.id}`} className="line-clamp-1 text-sm font-semibold text-zinc-900">
                {item.novel.title}
              </Link>
              <p className="mt-1 text-xs text-zinc-600">
                {item.chapter.title} · 第 {item.chapter.chapter_number} 章
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                进度 {formatProgress(item.reading_position)} · {formatDateLabel(item.read_at)}
              </p>
              <Link
                href={`/novels/${item.novel.id}/chapters/${item.chapter.id}`}
                className="mt-3 inline-flex rounded-lg bg-emerald-600 px-3 py-2 text-xs font-medium text-white"
              >
                继续阅读
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
