import { NovelCard } from "@/components/NovelCard";
import { novels } from "@/mocks/novels";

export default function SearchPage() {
  return (
    <section className="space-y-4">
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="mb-2 text-lg font-semibold">搜索</h1>
        <input
          className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          placeholder="输入小说名或作者（mock 页面）"
          readOnly
        />
      </div>

      <div className="grid gap-3">
        {novels.slice(0, 3).map((item) => (
          <NovelCard key={item.id} novel={item} />
        ))}
      </div>
    </section>
  );
}
