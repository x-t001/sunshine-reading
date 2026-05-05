"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { AdminSidebar } from "@/components/AdminSidebar";
import { useAuth } from "@/hooks/useAuth";
import { getAdminUsers } from "@/lib/api/admin";

type AdminLayoutProps = {
  title: string;
  description?: string;
  children: ReactNode;
};

type AccessState = "checking" | "allowed" | "forbidden";

function hasAdminShape(user: { role?: string; is_staff?: boolean; is_superuser?: boolean } | null): boolean {
  return Boolean(user && (user.role === "admin" || user.is_staff || user.is_superuser));
}

export function AdminLayout({ title, description, children }: AdminLayoutProps) {
  const { user, loading, error } = useAuth();
  const [accessState, setAccessState] = useState<AccessState>("checking");

  useEffect(() => {
    let active = true;

    async function checkAccess() {
      if (!user) {
        setAccessState("checking");
        return;
      }
      if (hasAdminShape(user)) {
        setAccessState("allowed");
        return;
      }

      setAccessState("checking");
      try {
        await getAdminUsers({ page_size: 1 });
        if (active) {
          setAccessState("allowed");
        }
      } catch {
        if (active) {
          setAccessState("forbidden");
        }
      }
    }

    void checkAccess();
    return () => {
      active = false;
    };
  }, [user]);

  if (loading || (user && accessState === "checking")) {
    return <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-300 shadow-sm">正在检查运营后台权限...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-white shadow-sm">
        <h1 className="text-lg font-semibold">运营后台</h1>
        <p className="mt-3 text-sm text-zinc-300">{error || "当前未登录，请先登录后访问运营后台。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  if (accessState !== "allowed") {
    return (
      <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-white shadow-sm">
        <h1 className="text-lg font-semibold">运营后台</h1>
        <p className="mt-3 text-sm text-zinc-300">当前账号没有管理员权限，无法访问运营后台。</p>
        <p className="mt-1 text-xs text-zinc-500">当前角色：{user.role}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/" className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-200">
            返回首页
          </Link>
          <Link href="/profile" className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white">
            查看个人中心
          </Link>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-4 rounded-2xl border border-zinc-200 bg-zinc-100 p-3 md:p-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-white shadow-sm">
        <p className="text-xs font-medium text-emerald-300">运营后台</p>
        <h1 className="mt-1 text-lg font-semibold">{title}</h1>
        {description ? <p className="mt-1 text-sm text-zinc-300">{description}</p> : null}
        <p className="mt-2 text-xs text-zinc-500">当前账号：{user.nickname || user.username} / {user.role}</p>
      </section>
      <div className="flex flex-col gap-4 md:flex-row md:items-start">
        <AdminSidebar />
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
