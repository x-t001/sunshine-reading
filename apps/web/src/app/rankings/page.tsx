import { rankings } from "@/mocks/rankings";
import { novels } from "@/mocks/novels";

export default function RankingsPage() {
  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <h1 className="mb-3 text-lg font-semibold">排行榜</h1>
      <ul className="space-y-2">
        {rankings.map((item) => {
          const novel = novels.find((n) => n.id === item.novelId);
          const trend = item.trend === "up" ? "↑" : item.trend === "down" ? "↓" : "→";
          return (
            <li key={item.novelId} className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm">
              <span>
                {item.rank}. {novel?.title}
              </span>
              <span className="text-zinc-500">
                {item.score} {trend}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
