"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "首页" },
  { href: "/novels", label: "小说" },
  { href: "/categories", label: "分类" },
  { href: "/rankings", label: "榜单" },
  { href: "/video-projects", label: "短视频" },
  { href: "/bookshelf", label: "书架" },
  { href: "/history", label: "历史" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-zinc-200 bg-white md:hidden">
      <ul className="mx-auto grid max-w-3xl grid-cols-7 px-2 py-2 text-xs">
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <li key={item.href} className="text-center">
              <Link className={active ? "font-medium text-emerald-600" : "text-zinc-500"} href={item.href}>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
