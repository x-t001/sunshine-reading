"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { categories as fallbackCategories } from "@/mocks/categories";
import { useAuth } from "@/hooks/useAuth";
import { getAdminUsers } from "@/lib/api/admin";
import { getCategories } from "@/lib/api/categories";

type NavigationCategory = {
  id: number | string;
  name: string;
  slug: string;
};

type CategoryLinksProps = {
  activeSlug?: string | null;
  categories: NavigationCategory[];
  isNovelList?: boolean;
};

function categoryLinkClass(active: boolean): string {
  return active
    ? "shrink-0 rounded-full bg-emerald-600 px-3 py-1 text-xs font-medium text-white"
    : "shrink-0 rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-600 transition-colors hover:bg-zinc-200 hover:text-zinc-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600";
}

function CategoryLinks({ activeSlug, categories, isNovelList = false }: CategoryLinksProps) {
  return (
    <>
      <Link href="/novels" className={categoryLinkClass(isNovelList && !activeSlug)} aria-current={isNovelList && !activeSlug ? "page" : undefined}>
        全部
      </Link>
      {categories.map((item) => {
        const active = isNovelList && activeSlug === item.slug;
        return (
          <Link
            key={`${item.id}-${item.slug}`}
            href={`/novels?category=${encodeURIComponent(item.slug)}`}
            className={categoryLinkClass(active)}
            aria-current={active ? "page" : undefined}
          >
            {item.name}
          </Link>
        );
      })}
      <Link
        href="/categories"
        className="shrink-0 px-2 py-1 text-xs font-medium text-emerald-700 hover:text-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
      >
        查看全部
      </Link>
    </>
  );
}

function ActiveCategoryLinks({ categories }: { categories: NavigationCategory[] }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  return <CategoryLinks categories={categories} isNovelList={pathname === "/novels"} activeSlug={searchParams.get("category")} />;
}

export function SiteHeader() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [canAccessAdminPanel, setCanAccessAdminPanel] = useState(false);
  const [navigationCategories, setNavigationCategories] = useState<NavigationCategory[]>(fallbackCategories);
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

  useEffect(() => {
    let active = true;

    void getCategories()
      .then((items) => {
        if (active && items.length > 0) {
          setNavigationCategories(items);
        }
      })
      .catch(() => {
        // Header navigation remains usable with the local fallback categories.
      });

    return () => {
      active = false;
    };
  }, []);

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
          <Link href="/video-projects">短视频</Link>
          <Link href="/bookshelf">书架</Link>
          <Link href="/history">历史</Link>
          {canAccessAuthorCenter ? <Link href="/author">作者中心</Link> : null}
          {canAccessReviewerCenter ? <Link href="/reviewer">审核中心</Link> : null}
          {canAccessAdminPanel ? <Link href="/admin">运营后台</Link> : null}
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
      <nav className="mx-auto flex max-w-5xl gap-2 overflow-x-auto px-4 py-2" aria-label="小说分类快捷导航">
        <Suspense fallback={<CategoryLinks categories={navigationCategories} />}>
          <ActiveCategoryLinks categories={navigationCategories} />
        </Suspense>
      </nav>
    </header>
  );
}
