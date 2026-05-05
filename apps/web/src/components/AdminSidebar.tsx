"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const adminNavItems = [
  { href: "/admin", label: "后台首页" },
  { href: "/admin/users", label: "用户管理" },
  { href: "/admin/novels", label: "小说管理" },
  { href: "/admin/chapters", label: "章节管理" },
  { href: "/admin/comments", label: "评论管理" },
  { href: "/", label: "返回首页" },
];

function isActiveNavItem(pathname: string, href: string): boolean {
  if (href === "/admin") {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 shadow-sm md:w-48 md:shrink-0">
      <p className="mb-3 hidden px-3 text-xs font-medium text-zinc-400 md:block">运营导航</p>
      <nav className="flex gap-2 overflow-x-auto text-sm md:flex-col">
        {adminNavItems.map((item) => {
          const active = isActiveNavItem(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                active
                  ? "shrink-0 rounded-lg bg-emerald-500 px-3 py-2 font-medium text-white"
                  : "shrink-0 rounded-lg px-3 py-2 text-zinc-300 hover:bg-zinc-900 hover:text-white"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
