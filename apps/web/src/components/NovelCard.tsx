import Image from "next/image";
import Link from "next/link";
import { categories } from "@/mocks/categories";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";
import { Novel, NovelListItem } from "@/types/novel";

type NovelCardData = Novel | NovelListItem;

function isApiNovel(novel: NovelCardData): novel is NovelListItem {
  return typeof novel.id === "number";
}

function getCoverUrl(novel: NovelCardData): string {
  const id = String(novel.id);
  if (novel.cover.startsWith("https://picsum.photos/")) {
    return novel.cover;
  }
  return `https://picsum.photos/seed/sunshine-${id}/240/320`;
}

export function NovelCard({ novel, priorityCover = false }: { novel: NovelCardData; priorityCover?: boolean }) {
  const id = String(novel.id);
  const apiNovel = isApiNovel(novel);
  const category = apiNovel ? novel.category : categories.find((item) => item.id === novel.categoryId);
  const author = apiNovel ? novel.author.nickname || novel.author.username : novel.author;
  const summary = apiNovel ? novel.description : novel.summary;
  const wordCount = apiNovel ? novel.word_count : novel.wordCount;
  const updatedAt = apiNovel ? novel.latest_chapter_updated_at || novel.updated_at || novel.created_at : novel.updatedAt;

  return (
    <Link href={`/novels/${id}`} className="flex gap-3 rounded-xl border border-zinc-200 bg-white p-3">
      <Image
        src={getCoverUrl(novel)}
        alt={novel.title}
        width={72}
        height={96}
        priority={priorityCover}
        className="h-24 w-18 rounded-md object-cover"
      />
      <div className="min-w-0 flex-1">
        <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900">{novel.title}</h3>
        <p className="mt-1 text-xs text-zinc-500">
          {author} · {category?.name ?? "未分类"}
        </p>
        <p className="mt-2 line-clamp-2 text-xs text-zinc-600">{summary}</p>
        <p className="mt-2 text-[11px] text-zinc-500">
          {formatWordCount(wordCount)} · 更新 {formatDateLabel(updatedAt)}
        </p>
      </div>
    </Link>
  );
}
