"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { categories } from "@/mocks/categories";
import { useAuth } from "@/hooks/useAuth";

export function SiteHeader() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  function handleLogout() {
    logout();
    router.push("/");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-3 px-4">
        <Link href="/" className="shrink-0 text-base font-semibold text-zinc-900">
          阳光阅读
        </Link>
        <nav className="hidden gap-4 text-sm text-zinc-600 md:flex">
          <Link href="/novels">小说</Link>
          <Link href="/categories">分类</Link>
          <Link href="/rankings">排行榜</Link>
          <Link href="/search">搜索</Link>
          <Link href="/bookshelf">书架</Link>
        </nav>
        <div className="ml-auto flex shrink-0 items-center gap-2 text-sm">
          {user ? (
            <>
              <Link href="/profile" className="max-w-28 truncate text-emerald-700">
                {user.nickname || user.username}
              </Link>
              <button className="text-zinc-500" type="button" onClick={handleLogout}>
                退出
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-emerald-600">
                登录
              </Link>
              <span className="text-zinc-300">/</span>
              <Link href="/register" className="text-zinc-600">
                注册
              </Link>
            </>
          )}
          {loading && !user ? <span className="hidden text-xs text-zinc-400 sm:inline">检查登录态</span> : null}
        </div>
      </div>
      <div className="mx-auto hidden max-w-5xl gap-2 overflow-x-auto px-4 py-2 md:flex">
        {categories.map((item) => (
          <span key={item.id} className="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-600">
            {item.name}
          </span>
        ))}
      </div>
    </header>
  );
}
