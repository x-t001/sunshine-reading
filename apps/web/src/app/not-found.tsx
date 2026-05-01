import Link from "next/link";

export default function NotFoundPage() {
  return (
    <section className="mx-auto max-w-xl rounded-xl bg-white p-6 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-zinc-900">页面不存在</h1>
      <p className="mt-2 text-sm text-zinc-600">你访问的内容可能已下线或链接有误。</p>
      <div className="mt-5 flex justify-center gap-2">
        <Link href="/" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          返回首页
        </Link>
        <Link href="/novels" className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700">
          浏览小说
        </Link>
      </div>
    </section>
  );
}
