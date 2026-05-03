"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const authorNavItems = [
  { href: "/author", label: "工作台" },
  { href: "/author/novels", label: "我的作品" },
  { href: "/author/novels/create", label: "创建作品" },
  { href: "/", label: "返回首页" },
];

export function AuthorSidebar() {
  const pathname = usePathname();

  return (
    <aside className="rounded-xl border border-zinc-200 bg-white p-3 shadow-sm md:w-48 md:shrink-0">
      <nav className="flex gap-2 overflow-x-auto text-sm md:flex-col">
        {authorNavItems.map((item) => {
          const active = item.href === "/author" ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                active
                  ? "shrink-0 rounded-lg bg-emerald-50 px-3 py-2 font-medium text-emerald-700"
                  : "shrink-0 rounded-lg px-3 py-2 text-zinc-600 hover:bg-zinc-50"
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
