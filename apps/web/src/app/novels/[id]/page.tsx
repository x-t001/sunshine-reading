import Image from "next/image";
import Link from "next/link";
import { getNovelChapters } from "@/lib/api/chapters";
import { getNovelDetail } from "@/lib/api/novels";
import { getApiErrorMessage } from "@/lib/api/request";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";

export const dynamic = "force-dynamic";

function getCoverUrl(id: number, cover: string): string {
  if (cover.startsWith("https://picsum.photos/")) {
    return cover;
  }
  return `https://picsum.photos/seed/sunshine-${id}/240/320`;
}

export default async function NovelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  try {
    const [novel, chapters] = await Promise.all([getNovelDetail(id), getNovelChapters(id, { page_size: 50 })]);
    const firstChapter = chapters.results[0];
    const cover = getCoverUrl(novel.id, novel.cover);

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
              className="h-36 w-24 rounded-lg object-cover"
            />
            <div className="min-w-0 flex-1">
              <h1 className="text-lg font-semibold">{novel.title}</h1>
              <p className="mt-1 text-sm text-zinc-600">作者：{novel.author.nickname || novel.author.username}</p>
              <p className="text-sm text-zinc-600">分类：{novel.category?.name ?? "未分类"}</p>
              <p className="text-sm text-zinc-600">字数：{formatWordCount(novel.word_count)}</p>
              <p className="text-sm text-zinc-600">状态：{novel.status}</p>
              <p className="text-sm text-zinc-600">更新：{formatDateLabel(novel.latest_chapter_updated_at || novel.updated_at)}</p>
            </div>
          </div>
          <p className="mt-3 text-sm leading-6 text-zinc-700">{novel.description}</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-zinc-600">
            <span className="rounded-lg bg-zinc-100 px-2 py-1">阅读 {novel.view_count}</span>
            <span className="rounded-lg bg-zinc-100 px-2 py-1">收藏 {novel.collect_count}</span>
            <span className="rounded-lg bg-zinc-100 px-2 py-1">评分 {novel.rating_score}</span>
          </div>
          <div className="mt-4 flex gap-2">
            <Link
              href={firstChapter ? `/novels/${novel.id}/chapters/${firstChapter.id}` : "#"}
              className={firstChapter ? "rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white" : "pointer-events-none rounded-lg bg-zinc-300 px-4 py-2 text-sm font-medium text-white"}
            >
              开始阅读
            </Link>
            <button className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-400" type="button" disabled>
              加入书架
            </button>
          </div>
        </section>

        <section className="rounded-xl bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-base font-semibold">章节列表</h2>
          {chapters.results.length === 0 ? (
            <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500">暂无可阅读章节，稍后再来看看。</p>
          ) : (
            <ul className="space-y-2">
              {chapters.results.map((chapter) => (
                <li key={chapter.id}>
                  <Link href={`/novels/${novel.id}/chapters/${chapter.id}`} className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm">
                    <span>{chapter.title}</span>
                    <span className="text-xs text-zinc-500">{formatWordCount(chapter.word_count)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  } catch (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        小说详情加载失败：{getApiErrorMessage(error)}
      </section>
    );
  }
}
