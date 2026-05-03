import { NovelCard } from "@/components/NovelCard";
import { getNovels } from "@/lib/api/novels";
import { getApiErrorMessage } from "@/lib/api/request";

export const dynamic = "force-dynamic";

type SearchPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function readKeyword(searchParams: Record<string, string | string[] | undefined>): string {
  const value = searchParams.keyword;
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const keyword = readKeyword(await searchParams).trim();
  let result: Awaited<ReturnType<typeof getNovels>> | null = null;
  let loadError: unknown = null;

  try {
    result = keyword ? await getNovels({ keyword, page_size: 10 }) : null;
  } catch (error) {
    loadError = error;
  }

  if (loadError) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        搜索失败：{getApiErrorMessage(loadError)}
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="mb-2 text-lg font-semibold">搜索</h1>
        <form action="/search">
          <input
            name="keyword"
            defaultValue={keyword}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            placeholder="输入小说名、作者或关键词"
          />
        </form>
      </div>

      {!keyword ? (
        <p className="rounded-xl border border-dashed border-zinc-300 bg-white px-3 py-6 text-center text-sm text-zinc-500">请输入关键词开始搜索。</p>
      ) : result && result.results.length > 0 ? (
        <div className="grid gap-3">
          {result.results.map((item) => (
            <NovelCard key={item.id} novel={item} />
          ))}
        </div>
      ) : (
        <p className="rounded-xl border border-dashed border-zinc-300 bg-white px-3 py-6 text-center text-sm text-zinc-500">没有找到相关小说。</p>
      )}
    </section>
  );
}
