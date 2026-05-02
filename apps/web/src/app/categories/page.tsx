import Link from "next/link";
import { getCategories } from "@/lib/api/categories";
import { getApiErrorMessage } from "@/lib/api/request";

export const dynamic = "force-dynamic";

export default async function CategoriesPage() {
  try {
    const categories = await getCategories();

    return (
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="mb-3 text-lg font-semibold">分类</h1>
        {categories.length === 0 ? (
          <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-center text-sm text-zinc-500">暂无分类。</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {categories.map((item) => (
              <Link key={item.id} href={`/novels?category=${item.slug}`} className="rounded-lg border border-zinc-200 p-3 text-center text-sm text-zinc-700">
                {item.name}
              </Link>
            ))}
          </div>
        )}
      </section>
    );
  } catch (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        分类加载失败：{getApiErrorMessage(error)}
      </section>
    );
  }
}
