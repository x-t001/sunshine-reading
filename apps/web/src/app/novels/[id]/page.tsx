import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { categories } from "@/mocks/categories";
import { chapterPreviews } from "@/mocks/chapters";
import { novels } from "@/mocks/novels";
import { formatWordCount } from "@/lib/utils/format";

export default async function NovelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const novel = novels.find((item) => item.id === id);

  if (!novel) {
    notFound();
  }

  const category = categories.find((item) => item.id === novel.categoryId);
  const chapters = chapterPreviews.filter((item) => item.novelId === novel.id);
  const firstChapter = chapters[0];

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex gap-3">
          <Image src={novel.cover} alt={novel.title} width={96} height={144} className="h-36 w-24 rounded-lg object-cover" />
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-semibold">{novel.title}</h1>
            <p className="mt-1 text-sm text-zinc-600">作者：{novel.author}</p>
            <p className="text-sm text-zinc-600">分类：{category?.name}</p>
            <p className="text-sm text-zinc-600">字数：{formatWordCount(novel.wordCount)}</p>
          </div>
        </div>
        <p className="mt-3 text-sm leading-6 text-zinc-700">{novel.summary}</p>
        <div className="mt-4 flex gap-2">
          <Link
            href={firstChapter ? `/novels/${novel.id}/chapters/${firstChapter.id}` : "#"}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white"
          >
            开始阅读
          </Link>
          <button className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700" type="button">
            加入书架
          </button>
        </div>
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-base font-semibold">章节列表</h2>
        <ul className="space-y-2">
          {chapters.map((chapter) => (
            <li key={chapter.id}>
              <Link href={`/novels/${novel.id}/chapters/${chapter.id}`} className="block rounded-lg border border-zinc-200 px-3 py-2 text-sm">
                {chapter.title}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
