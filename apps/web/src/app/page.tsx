import Link from "next/link";
import { SectionTitle } from "@/components/SectionTitle";
import { NovelCard } from "@/components/NovelCard";
import { categories } from "@/mocks/categories";
import { novels } from "@/mocks/novels";

export default function HomePage() {
  const recommends = novels.filter((item) => item.recommend);
  const updates = [...novels].sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1)).slice(0, 3);

  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <p className="mb-2 text-sm text-zinc-500">搜索小说、作者、关键词</p>
        <Link href="/search" className="block rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-500">
          请输入关键词...
        </Link>
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <SectionTitle title="分类入口" actionText="查看全部" />
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
          {categories.map((item) => (
            <Link key={item.id} href="/categories" className="rounded-lg bg-zinc-100 px-3 py-2 text-center text-sm text-zinc-700">
              {item.name}
            </Link>
          ))}
        </div>
      </section>

      <section>
        <SectionTitle title="推荐小说" actionText="更多" />
        <div className="grid gap-3">{recommends.map((item) => <NovelCard key={item.id} novel={item} />)}</div>
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <SectionTitle title="排行榜入口" actionText="进入榜单" />
        <Link href="/rankings" className="text-sm text-emerald-600">
          查看热度榜、新书榜、评分榜
        </Link>
      </section>

      <section>
        <SectionTitle title="最近更新" />
        <div className="grid gap-3">{updates.map((item) => <NovelCard key={item.id} novel={item} />)}</div>
      </section>
    </div>
  );
}
