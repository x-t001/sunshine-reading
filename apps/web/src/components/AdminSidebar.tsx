"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const adminNavItems = [
  { href: "/admin", label: "管理首页" },
  { href: "/admin/users", label: "用户管理" },
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
    <aside className="rounded-xl border border-zinc-200 bg-white p-3 shadow-sm md:w-48 md:shrink-0">
      <nav className="flex gap-2 overflow-x-auto text-sm md:flex-col">
        {adminNavItems.map((item) => {
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
