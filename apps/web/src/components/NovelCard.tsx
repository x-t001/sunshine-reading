import Image from "next/image";
import Link from "next/link";
import { categories } from "@/mocks/categories";
import { Novel } from "@/types/novel";
import { formatDateLabel, formatWordCount } from "@/lib/utils/format";

export function NovelCard({ novel, priorityCover = false }: { novel: Novel; priorityCover?: boolean }) {
  const category = categories.find((item) => item.id === novel.categoryId);

  return (
    <Link href={`/novels/${novel.id}`} className="flex gap-3 rounded-xl border border-zinc-200 bg-white p-3">
      <Image
        src={novel.cover}
        alt={novel.title}
        width={72}
        height={96}
        priority={priorityCover}
        className="h-24 w-18 rounded-md object-cover"
      />
      <div className="min-w-0 flex-1">
        <h3 className="line-clamp-1 text-sm font-semibold text-zinc-900">{novel.title}</h3>
        <p className="mt-1 text-xs text-zinc-500">
          {novel.author} · {category?.name}
        </p>
        <p className="mt-2 line-clamp-2 text-xs text-zinc-600">{novel.summary}</p>
        <p className="mt-2 text-[11px] text-zinc-500">
          {formatWordCount(novel.wordCount)} · 更新 {formatDateLabel(novel.updatedAt)}
        </p>
      </div>
    </Link>
  );
}
