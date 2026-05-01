import Link from "next/link";
import { categories } from "@/mocks/categories";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link href="/" className="text-base font-semibold text-zinc-900">
          阳光阅读
        </Link>
        <nav className="hidden gap-4 text-sm text-zinc-600 md:flex">
          <Link href="/novels">小说</Link>
          <Link href="/categories">分类</Link>
          <Link href="/rankings">排行榜</Link>
          <Link href="/search">搜索</Link>
          <Link href="/bookshelf">书架</Link>
        </nav>
      </div>
      <div className="mx-auto hidden max-w-5xl gap-2 overflow-x-auto px-4 py-2 md:flex">
        {categories.map((item) => (
          <span key={item.id} className="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-600">
            {item.name}
          </span>
        ))}
      </div>
    </header>
  );
}
