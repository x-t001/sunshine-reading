import Link from "next/link";
import { ReadingToolbar } from "@/components/ReadingToolbar";
import { getChapterDetail } from "@/lib/api/chapters";
import { getApiErrorMessage } from "@/lib/api/request";

export const dynamic = "force-dynamic";

export default async function ReadingPage({
  params,
}: {
  params: Promise<{ id: string; chapterId: string }>;
}) {
  const { id, chapterId } = await params;

  try {
    const chapter = await getChapterDetail(chapterId);
    if (String(chapter.novel.id) !== id) {
      return (
        <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          章节与小说不匹配。
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
        <div className="mt-4 space-y-4 text-[18px] leading-8 text-zinc-800">
          {chapter.content.split("\n\n").map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>

        <div className="mt-8 grid grid-cols-3 gap-2 text-sm">
          <Link
            href={chapter.previous_chapter_id ? `/novels/${id}/chapters/${chapter.previous_chapter_id}` : "#"}
            className={chapter.previous_chapter_id ? "rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700" : "pointer-events-none rounded-lg border border-zinc-200 px-3 py-2 text-center text-zinc-400"}
          >
            上一章
          </Link>
          <Link href={`/novels/${id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700">
            目录
          </Link>
          <Link
            href={chapter.next_chapter_id ? `/novels/${id}/chapters/${chapter.next_chapter_id}` : "#"}
            className={chapter.next_chapter_id ? "rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700" : "pointer-events-none rounded-lg border border-zinc-200 px-3 py-2 text-center text-zinc-400"}
          >
            下一章
          </Link>
        </div>

        <ReadingToolbar />
      </article>
    );
  } catch (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        章节加载失败：{getApiErrorMessage(error)}
      </section>
    );
  }
}
