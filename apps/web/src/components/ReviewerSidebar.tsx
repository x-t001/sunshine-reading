"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const reviewerNavItems = [
  { href: "/reviewer", label: "审核首页" },
  { href: "/reviewer/novels", label: "待审核作品" },
  { href: "/reviewer/novels/reviewing", label: "我的作品审核" },
  { href: "/reviewer/chapters", label: "待审核章节" },
  { href: "/reviewer/chapters/reviewing", label: "我的章节审核" },
  { href: "/reviewer/audit-logs", label: "审核记录" },
  { href: "/", label: "返回首页" },
];

function isActiveNavItem(pathname: string, href: string): boolean {
  if (href === "/reviewer") {
    return pathname === href;
  }
  if (href === "/reviewer/novels") {
    return pathname === href || /^\/reviewer\/novels\/\d+/.test(pathname);
  }
  if (href === "/reviewer/chapters") {
    return pathname === href || /^\/reviewer\/chapters\/\d+/.test(pathname);
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function ReviewerSidebar() {
  const pathname = usePathname();

  return (
    <aside className="rounded-xl border border-zinc-200 bg-white p-3 shadow-sm md:w-48 md:shrink-0">
      <nav className="flex gap-2 overflow-x-auto text-sm md:flex-col">
        {reviewerNavItems.map((item) => {
          const active = isActiveNavItem(pathname, item.href);
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
