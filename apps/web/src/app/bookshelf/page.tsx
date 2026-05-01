import { NovelCard } from "@/components/NovelCard";
import { novels } from "@/mocks/novels";

export default function BookshelfPage() {
  return (
    <section>
      <h1 className="mb-3 text-lg font-semibold">我的书架</h1>
      <div className="grid gap-3">
        {novels.slice(0, 3).map((item) => (
          <NovelCard key={item.id} novel={item} />
        ))}
      </div>
    </section>
  );
}
