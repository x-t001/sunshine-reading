import Link from "next/link";
import { NovelCard } from "@/components/NovelCard";
import { SectionTitle } from "@/components/SectionTitle";
import { getCategories } from "@/lib/api/categories";
import { getNovels } from "@/lib/api/novels";
import { getRankings } from "@/lib/api/rankings";
import { getApiErrorMessage } from "@/lib/api/request";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let categories: Awaited<ReturnType<typeof getCategories>> | null = null;
  let recommends: Awaited<ReturnType<typeof getNovels>> | null = null;
  let rankings: Awaited<ReturnType<typeof getRankings>> | null = null;
  let updates: Awaited<ReturnType<typeof getNovels>> | null = null;
  let loadError: unknown = null;

  try {
    [categories, recommends, rankings, updates] = await Promise.all([
      getCategories(),
      getNovels({ ordering: "rating", page_size: 3 }),
      getRankings(),
      getNovels({ ordering: "latest", page_size: 3 }),
    ]);
  } catch (error) {
    loadError = error;
  }

  if (loadError || !categories || !recommends || !rankings || !updates) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        后端数据加载失败：{getApiErrorMessage(loadError)}
      </section>
    );
  }

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
        {categories.length === 0 ? (
          <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500">暂无分类。</p>
        ) : (
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {categories.map((item) => (
              <Link key={item.id} href={`/novels?category=${item.slug}`} className="rounded-lg bg-zinc-100 px-3 py-2 text-center text-sm text-zinc-700">
                {item.name}
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionTitle title="推荐小说" actionText="更多" />
        {recommends.results.length === 0 ? (
          <p className="rounded-lg border border-dashed border-zinc-300 bg-white px-3 py-4 text-sm text-zinc-500">暂无推荐小说。</p>
        ) : (
          <div className="grid gap-3">
            {recommends.results.map((item, index) => (
              <NovelCard key={item.id} novel={item} priorityCover={index === 0} />
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <SectionTitle title="排行榜入口" actionText="进入榜单" />
        <Link href="/rankings" className="text-sm text-emerald-600">
          {rankings.length > 0 ? rankings.map((item) => item.name).slice(0, 3).join("、") : "查看榜单"}
        </Link>
      </section>

      <section>
        <SectionTitle title="最近更新" />
        {updates.results.length === 0 ? (
          <p className="rounded-lg border border-dashed border-zinc-300 bg-white px-3 py-4 text-sm text-zinc-500">暂无最近更新。</p>
        ) : (
          <div className="grid gap-3">
            {updates.results.map((item) => (
              <NovelCard key={item.id} novel={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
