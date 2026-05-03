"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { AuthorSidebar } from "@/components/AuthorSidebar";
import { useAuth } from "@/hooks/useAuth";

type AuthorLayoutProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

function canUseAuthorCenter(role: string | undefined): boolean {
  return role === "author" || role === "admin";
}

export function AuthorLayout({ title, description, children }: AuthorLayoutProps) {
  const { user, loading, error } = useAuth();

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在检查登录状态...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">作者中心</h1>
        <p className="mt-3 text-sm text-zinc-600">{error || "当前未登录，请先登录后访问作者中心。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  if (!canUseAuthorCenter(user.role)) {
    return (
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">作者中心</h1>
        <p className="mt-3 text-sm text-zinc-600">当前账号不是作者账号，无法访问作者工作台。</p>
        <p className="mt-1 text-xs text-zinc-400">当前角色：{user.role}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/" className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700">
            返回首页
          </Link>
          <Link href="/profile" className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
            查看个人中心
          </Link>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <p className="text-xs text-zinc-500">作者工作台</p>
        <h1 className="mt-1 text-lg font-semibold">{title}</h1>
        {description ? <p className="mt-1 text-sm text-zinc-500">{description}</p> : null}
      </section>
      <div className="flex flex-col gap-4 md:flex-row md:items-start">
        <AuthorSidebar />
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
