import Link from "next/link";
import { notFound } from "next/navigation";
import { ReadingToolbar } from "@/components/ReadingToolbar";
import { chapterContents, chapterPreviews } from "@/mocks/chapters";
import { novels } from "@/mocks/novels";

export default async function ReadingPage({
  params,
}: {
  params: Promise<{ id: string; chapterId: string }>;
}) {
  const { id, chapterId } = await params;
  const novel = novels.find((item) => item.id === id);
  const chapter = chapterContents.find((item) => item.chapterId === chapterId && item.novelId === id);

  if (!novel || !chapter) {
    notFound();
  }

  const chapterList = chapterPreviews.filter((item) => item.novelId === id);
  const currentIndex = chapterList.findIndex((item) => item.id === chapterId);
  const prev = currentIndex > 0 ? chapterList[currentIndex - 1] : null;
  const next = currentIndex < chapterList.length - 1 ? chapterList[currentIndex + 1] : null;

  return (
    <article className="mx-auto max-w-3xl rounded-xl bg-white p-4 shadow-sm">
      <p className="text-xs text-zinc-500">{novel.title}</p>
      <h1 className="mt-1 text-xl font-semibold">{chapter.title}</h1>
      <div className="mt-4 space-y-4 text-[18px] leading-8 text-zinc-800">
        {chapter.content.split("\n\n").map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>

      <div className="mt-8 grid grid-cols-3 gap-2 text-sm">
        <Link
          href={prev ? `/novels/${id}/chapters/${prev.id}` : "#"}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700"
        >
          上一章
        </Link>
        <Link href={`/novels/${id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700">
          目录
        </Link>
        <Link
          href={next ? `/novels/${id}/chapters/${next.id}` : "#"}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700"
        >
          下一章
        </Link>
      </div>

      <ReadingToolbar />
    </article>
  );
}
