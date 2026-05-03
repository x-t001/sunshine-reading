"use client";

import Link from "next/link";
import { AuthorLayout } from "@/components/AuthorLayout";

const actionCards = [
  {
    href: "/author/novels",
    title: "我的作品",
    description: "查看、筛选和提交已有作品。",
  },
  {
    href: "/author/novels/create",
    title: "创建作品",
    description: "建立新小说草稿，准备章节内容。",
  },
  {
    href: "/",
    title: "返回首页",
    description: "回到读者端检查公开展示效果。",
  },
];

export default function AuthorHomePage() {
  return (
    <AuthorLayout title="作者中心" description="管理你的作品、章节草稿和审核提交。">
      <div className="grid gap-3 md:grid-cols-3">
        {actionCards.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm hover:border-emerald-200">
            <h2 className="text-base font-semibold text-zinc-900">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{item.description}</p>
          </Link>
        ))}
      </div>
    </AuthorLayout>
  );
}
