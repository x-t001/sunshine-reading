import { NovelCard } from "@/components/NovelCard";
import { SectionTitle } from "@/components/SectionTitle";
import { novels } from "@/mocks/novels";

export default function NovelsPage() {
  return (
    <section>
      <SectionTitle title="小说列表" />
      <div className="grid gap-3">
        {novels.map((item) => (
          <NovelCard key={item.id} novel={item} />
        ))}
      </div>
    </section>
  );
}
