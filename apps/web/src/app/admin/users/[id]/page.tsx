"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { banUser, getAdminUserDetail, unbanUser, updateUserRole } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminUserDetail, AdminUserRole } from "@/types/admin";

const roleLabels: Record<AdminUserRole, string> = {
  reader: "读者",
  author: "作者",
  reviewer: "审核员",
  admin: "管理员",
};

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "暂无";
  }
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AdminUserDetailPage() {
  return (
    <AdminLayout title="用户详情" description="查看用户资料、角色和账号状态。">
      <AdminUserDetailContent />
    </AdminLayout>
  );
}

function AdminUserDetailContent() {
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [roleDraft, setRoleDraft] = useState<AdminUserRole>("reader");
  const [banReason, setBanReason] = useState("");
  const [banOpen, setBanOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [operating, setOperating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadUser = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminUserDetail(id);
      setUser(result);
      setRoleDraft(result.role);
    } catch (loadError) {
      setUser(null);
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadUser();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadUser]);

  async function handleRoleSave() {
    if (!user) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await updateUserRole(user.id, roleDraft);
      setNotice(`用户 ${user.username} 的角色已更新为 ${roleLabels[roleDraft]}。`);
      await loadUser();
    } catch (roleError) {
      setError(getApiErrorMessage(roleError));
    } finally {
      setOperating(false);
    }
  }

  async function handleBan() {
    if (!user) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await banUser(user.id, { reason: banReason.trim() });
      setNotice(`用户 ${user.username} 已封禁。`);
      setBanOpen(false);
      setBanReason("");
      await loadUser();
    } catch (banError) {
      setError(getApiErrorMessage(banError));
    } finally {
      setOperating(false);
    }
  }

  async function handleUnban() {
    if (!user || !window.confirm(`确认解封用户 ${user.username}？`)) {
      return;
    }
    setOperating(true);
    setError(null);
    setNotice(null);
    try {
      await unbanUser(user.id);
      setNotice(`用户 ${user.username} 已解封。`);
      await loadUser();
    } catch (unbanError) {
      setError(getApiErrorMessage(unbanError));
    } finally {
      setOperating(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载用户详情...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {error || "用户不存在或无权访问。"}
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-xl bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-semibold">{user.username}</h2>
              <span className={user.is_banned ? "rounded-full bg-red-50 px-2 py-1 text-xs text-red-600" : "rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700"}>
                {user.is_banned ? "已封禁" : "正常"}
              </span>
              {user.is_superuser ? <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-600">超级管理员</span> : null}
              {user.is_staff ? <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-600">Staff</span> : null}
            </div>
            <p className="mt-2 text-sm text-zinc-500">昵称：{user.nickname || "暂无"}</p>
            <p className="mt-1 text-sm text-zinc-500">角色：{roleLabels[user.role]}</p>
            <p className="mt-1 text-sm text-zinc-500">邮箱：{user.email || "暂无"}</p>
            <p className="mt-1 text-sm text-zinc-500">手机：{user.phone || "暂无"}</p>
            <p className="mt-3 text-sm leading-6 text-zinc-700">简介：{user.bio || "暂无"}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2 text-sm">
            <Link href="/admin/users" className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
              返回列表
            </Link>
            <select
              className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
              value={roleDraft}
              disabled={operating}
              onChange={(event) => setRoleDraft(event.target.value as AdminUserRole)}
            >
              {Object.entries(roleLabels).map(([role, label]) => (
                <option key={role} value={role}>
                  {label}
                </option>
              ))}
            </select>
            <button className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating || roleDraft === user.role} onClick={() => void handleRoleSave()}>
              保存角色
            </button>
            {user.is_banned ? (
              <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operating} onClick={() => void handleUnban()}>
                解封
              </button>
            ) : (
              <button className="rounded-lg bg-red-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operating} onClick={() => setBanOpen(true)}>
                封禁
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <StatCard label="作品数" value={`${user.novel_count}`} />
        <StatCard label="评论数" value={`${user.comment_count}`} />
        <StatCard label="书架数" value={`${user.bookshelf_count}`} />
        <StatCard label="评分数" value={`${user.rating_count}`} />
      </section>

      <section className="rounded-xl bg-white p-4 text-sm text-zinc-600 shadow-sm">
        <p>用户 ID：{user.id}</p>
        <p className="mt-1">账号启用：{user.is_active ? "是" : "否"}</p>
        <p className="mt-1">注册时间：{formatDateTime(user.date_joined)}</p>
        <p className="mt-1">最后登录：{formatDateTime(user.last_login)}</p>
      </section>

      {banOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
          <section className="w-full max-w-lg rounded-xl bg-white p-4 shadow-xl">
            <h2 className="text-base font-semibold text-zinc-900">封禁用户：{user.username}</h2>
            <textarea
              className="mt-3 min-h-28 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              value={banReason}
              maxLength={500}
              onChange={(event) => setBanReason(event.target.value)}
              placeholder="封禁原因，可选"
            />
            <div className="mt-1 text-right text-xs text-zinc-400">{banReason.length}/500</div>
            <div className="mt-4 flex justify-end gap-2 text-sm">
              <button
                className="rounded-lg border border-zinc-300 px-4 py-2 text-zinc-700"
                type="button"
                disabled={operating}
                onClick={() => {
                  setBanOpen(false);
                  setBanReason("");
                }}
              >
                取消
              </button>
              <button className="rounded-lg bg-red-600 px-4 py-2 font-medium text-white disabled:bg-zinc-300" type="button" disabled={operating} onClick={() => void handleBan()}>
                确认封禁
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
    </div>
  );
}
