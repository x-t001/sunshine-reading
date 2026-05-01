import { categories } from "@/mocks/categories";

export default function CategoriesPage() {
  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <h1 className="mb-3 text-lg font-semibold">分类</h1>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {categories.map((item) => (
          <div key={item.id} className="rounded-lg border border-zinc-200 p-3 text-center text-sm text-zinc-700">
            {item.name}
          </div>
        ))}
      </div>
    </section>
  );
}
