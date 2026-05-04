"use client";

import Link from "next/link";
import { AdminLayout } from "@/components/AdminLayout";

const actionCards = [
  {
    href: "/admin/users",
    title: "用户管理",
    description: "查看用户列表，调整角色，并处理封禁或解封。",
  },
  {
    href: "/",
    title: "返回首页",
    description: "回到阳光阅读主站继续浏览公开内容。",
  },
];

export default function AdminHomePage() {
  return (
    <AdminLayout title="管理首页" description="管理平台用户角色和账号状态。">
      <div className="grid gap-3 md:grid-cols-2">
        {actionCards.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm hover:border-emerald-200">
            <h2 className="text-base font-semibold text-zinc-900">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{item.description}</p>
          </Link>
        ))}
      </div>
    </AdminLayout>
  );
}
