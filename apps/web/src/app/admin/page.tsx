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
    href: "/admin/categories",
    title: "分类管理",
    description: "维护小说分类、排序、父级关系和启用状态。",
  },
  {
    href: "/admin/rankings",
    title: "榜单管理",
    description: "维护榜单类型和榜单条目，控制前台排行榜展示。",
  },
  {
    href: "/admin/novels",
    title: "小说管理",
    description: "查看小说内容，调整连载状态，并设置推荐。",
  },
  {
    href: "/admin/chapters",
    title: "章节管理",
    description: "查看章节内容，隐藏或恢复章节发布状态。",
  },
  {
    href: "/admin/comments",
    title: "评论管理",
    description: "查看评论内容，隐藏、恢复或标记删除。",
  },
  {
    href: "/",
    title: "返回首页",
    description: "回到阳光阅读主站继续浏览公开内容。",
  },
];

export default function AdminHomePage() {
  return (
    <AdminLayout title="后台首页" description="管理平台用户、分类、榜单、小说、章节和评论。">
      <div className="grid gap-3 md:grid-cols-2">
        {actionCards.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm hover:border-zinc-400">
            <h2 className="text-base font-semibold text-zinc-900">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{item.description}</p>
          </Link>
        ))}
      </div>
    </AdminLayout>
  );
}
