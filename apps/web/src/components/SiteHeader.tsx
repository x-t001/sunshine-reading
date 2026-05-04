"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { categories } from "@/mocks/categories";
import { useAuth } from "@/hooks/useAuth";
import { getAdminUsers } from "@/lib/api/admin";

export function SiteHeader() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [canAccessAdminPanel, setCanAccessAdminPanel] = useState(false);
  const canAccessAuthorCenter = user?.role === "author" || user?.role === "admin";
  const canAccessReviewerCenter = user?.role === "reviewer" || user?.role === "admin" || user?.is_staff || user?.is_superuser;

  useEffect(() => {
    let active = true;

    async function checkAdminAccess() {
      if (!user) {
        setCanAccessAdminPanel(false);
        return;
      }
      if (user.role === "admin" || user.is_staff || user.is_superuser) {
        setCanAccessAdminPanel(true);
        return;
      }

      try {
        await getAdminUsers({ page_size: 1 });
        if (active) {
          setCanAccessAdminPanel(true);
        }
      } catch {
        if (active) {
          setCanAccessAdminPanel(false);
        }
      }
    }

    void checkAdminAccess();
    return () => {
      active = false;
    };
  }, [user]);

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
          <Link href="/rankings">榜单</Link>
          <Link href="/search">搜索</Link>
          <Link href="/bookshelf">书架</Link>
          <Link href="/history">历史</Link>
          {canAccessAuthorCenter ? <Link href="/author">作者中心</Link> : null}
          {canAccessReviewerCenter ? <Link href="/reviewer">审核中心</Link> : null}
          {canAccessAdminPanel ? <Link href="/admin">管理后台</Link> : null}
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
          ) : loading ? (
            <span className="hidden text-xs text-zinc-400 sm:inline">检查登录...</span>
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
