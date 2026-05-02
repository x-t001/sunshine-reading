import Link from "next/link";
import { getRankings } from "@/lib/api/rankings";
import { getApiErrorMessage } from "@/lib/api/request";

export const dynamic = "force-dynamic";

export default async function RankingsPage() {
  try {
    const rankings = await getRankings();

    return (
      <section className="space-y-4">
        <div className="rounded-xl bg-white p-4 shadow-sm">
          <h1 className="text-lg font-semibold">排行榜</h1>
        </div>
        {rankings.length === 0 ? (
          <p className="rounded-xl border border-dashed border-zinc-300 bg-white px-3 py-6 text-center text-sm text-zinc-500">暂无排行榜。</p>
        ) : (
          rankings.map((ranking) => (
            <div key={ranking.id} className="rounded-xl bg-white p-4 shadow-sm">
              <div className="mb-3">
                <h2 className="text-base font-semibold">{ranking.name}</h2>
                {ranking.description ? <p className="mt-1 text-xs text-zinc-500">{ranking.description}</p> : null}
              </div>
              {ranking.items.length === 0 ? (
                <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-4 text-sm text-zinc-500">暂无榜单数据。</p>
              ) : (
                <ul className="space-y-2">
                  {ranking.items.map((item) => (
                    <li key={`${ranking.id}-${item.rank}-${item.novel.id}`}>
                      <Link href={`/novels/${item.novel.id}`} className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm">
                        <span>
                          {item.rank}. {item.novel.title}
                        </span>
                        <span className="text-zinc-500">{item.score}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))
        )}
      </section>
    );
  } catch (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        排行榜加载失败：{getApiErrorMessage(error)}
      </section>
    );
  }
}
