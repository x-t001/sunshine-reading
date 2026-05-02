import Link from "next/link";
import { NovelCard } from "@/components/NovelCard";
import { SectionTitle } from "@/components/SectionTitle";
import { getCategories } from "@/lib/api/categories";
import { getNovels } from "@/lib/api/novels";
import { buildQueryString, getApiErrorMessage } from "@/lib/api/request";

export const dynamic = "force-dynamic";

type NovelsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function readParam(searchParams: Record<string, string | string[] | undefined>, key: string): string | undefined {
  const value = searchParams[key];
  return Array.isArray(value) ? value[0] : value;
}

function pageHref(page: number, params: Record<string, string | undefined>): string {
  return `/novels${buildQueryString({ ...params, page })}`;
}

export default async function NovelsPage({ searchParams }: NovelsPageProps) {
  const resolvedSearchParams = await searchParams;
  const page = Number(readParam(resolvedSearchParams, "page") || "1") || 1;
  const pageSize = Math.min(Number(readParam(resolvedSearchParams, "page_size") || "10") || 10, 50);
  const category = readParam(resolvedSearchParams, "category");
  const status = readParam(resolvedSearchParams, "status");
  const ordering = readParam(resolvedSearchParams, "ordering") || "latest";
  const keyword = readParam(resolvedSearchParams, "keyword");
  const queryState = { category, status, ordering, keyword, page_size: String(pageSize) };

  try {
    const [categories, novelPage] = await Promise.all([
      getCategories(),
      getNovels({ page, page_size: pageSize, category, status, ordering, keyword }),
    ]);

    return (
      <section className="space-y-4">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <SectionTitle title="小说列表" />
          <form action="/novels" className="grid gap-3 md:grid-cols-5">
            <input
              name="keyword"
              defaultValue={keyword ?? ""}
              className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
              placeholder="标题、作者、简介"
            />
            <select name="category" defaultValue={category ?? ""} className="rounded-lg border border-zinc-200 px-3 py-2 text-sm">
              <option value="">全部分类</option>
              {categories.map((item) => (
                <option key={item.id} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
            <select name="ordering" defaultValue={ordering} className="rounded-lg border border-zinc-200 px-3 py-2 text-sm">
              <option value="latest">最近更新</option>
              <option value="views">阅读量</option>
              <option value="collects">收藏数</option>
              <option value="rating">评分</option>
            </select>
            <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
              筛选
            </button>
          </form>
        </div>

        {novelPage.results.length === 0 ? (
          <p className="rounded-xl border border-dashed border-zinc-300 bg-white px-3 py-6 text-center text-sm text-zinc-500">暂无符合条件的小说。</p>
        ) : (
          <div className="grid gap-3">
            {novelPage.results.map((item) => (
              <NovelCard key={item.id} novel={item} />
            ))}
          </div>
        )}

        <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
          <Link
            href={page > 1 ? pageHref(page - 1, queryState) : "#"}
            className={page > 1 ? "text-emerald-600" : "pointer-events-none text-zinc-400"}
          >
            上一页
          </Link>
          <span className="text-zinc-500">共 {novelPage.count} 本</span>
          <Link
            href={novelPage.next ? pageHref(page + 1, queryState) : "#"}
            className={novelPage.next ? "text-emerald-600" : "pointer-events-none text-zinc-400"}
          >
            下一页
          </Link>
        </div>
      </section>
    );
  } catch (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        小说列表加载失败：{getApiErrorMessage(error)}
      </section>
    );
  }
}
