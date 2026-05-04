"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { banUser, getAdminUsers, unbanUser, updateUserRole } from "@/lib/api/admin";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AdminUser, AdminUserRole, GetAdminUsersParams } from "@/types/admin";

const PAGE_SIZE = 10;

const roleLabels: Record<AdminUserRole, string> = {
  reader: "读者",
  author: "作者",
  reviewer: "审核员",
  admin: "管理员",
};

type FilterState = {
  keyword: string;
  role: AdminUserRole | "";
  is_banned: "" | "true" | "false";
};

type BanTarget = {
  id: number;
  username: string;
} | null;

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

function buildParams(page: number, filters: FilterState): GetAdminUsersParams {
  return {
    page,
    page_size: PAGE_SIZE,
    keyword: filters.keyword,
    role: filters.role,
    is_banned: filters.is_banned === "" ? "" : filters.is_banned === "true",
  };
}

export default function AdminUsersPage() {
  return (
    <AdminLayout title="用户管理" description="查看用户、调整角色，并处理账号封禁状态。">
      <AdminUsersContent />
    </AdminLayout>
  );
}

function AdminUsersContent() {
  const [filters, setFilters] = useState<FilterState>({ keyword: "", role: "", is_banned: "" });
  const [query, setQuery] = useState<FilterState>(filters);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AdminUser[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [previous, setPrevious] = useState<string | null>(null);
  const [roleDrafts, setRoleDrafts] = useState<Record<number, AdminUserRole>>({});
  const [loading, setLoading] = useState(false);
  const [operatingId, setOperatingId] = useState<number | null>(null);
  const [banTarget, setBanTarget] = useState<BanTarget>(null);
  const [banReason, setBanReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminUsers(buildParams(page, query));
      setItems(result.results);
      setCount(result.count);
      setNext(result.next);
      setPrevious(result.previous);
      setRoleDrafts(
        result.results.reduce<Record<number, AdminUserRole>>((drafts, user) => {
          drafts[user.id] = user.role;
          return drafts;
        }, {}),
      );
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [page, query]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadUsers();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadUsers]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setQuery(filters);
  }

  async function handleRoleSave(user: AdminUser) {
    const nextRole = roleDrafts[user.id] || user.role;
    setOperatingId(user.id);
    setError(null);
    setNotice(null);
    try {
      await updateUserRole(user.id, nextRole);
      setNotice(`用户 ${user.username} 的角色已更新为 ${roleLabels[nextRole]}。`);
      await loadUsers();
    } catch (roleError) {
      setError(getApiErrorMessage(roleError));
    } finally {
      setOperatingId(null);
    }
  }

  async function handleBan() {
    if (!banTarget) {
      return;
    }
    setOperatingId(banTarget.id);
    setError(null);
    setNotice(null);
    try {
      await banUser(banTarget.id, { reason: banReason.trim() });
      setNotice(`用户 ${banTarget.username} 已封禁。`);
      setBanTarget(null);
      setBanReason("");
      await loadUsers();
    } catch (banError) {
      setError(getApiErrorMessage(banError));
    } finally {
      setOperatingId(null);
    }
  }

  async function handleUnban(user: AdminUser) {
    if (!window.confirm(`确认解封用户 ${user.username}？`)) {
      return;
    }
    setOperatingId(user.id);
    setError(null);
    setNotice(null);
    try {
      await unbanUser(user.id);
      setNotice(`用户 ${user.username} 已解封。`);
      await loadUsers();
    } catch (unbanError) {
      setError(getApiErrorMessage(unbanError));
    } finally {
      setOperatingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <form className="grid gap-3 md:grid-cols-5" onSubmit={handleSearch}>
          <input
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 md:col-span-2"
            value={filters.keyword}
            onChange={(event) => setFilters((current) => ({ ...current, keyword: event.target.value }))}
            placeholder="搜索用户名、昵称、邮箱或手机号"
          />
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.role}
            onChange={(event) => setFilters((current) => ({ ...current, role: event.target.value as AdminUserRole | "" }))}
          >
            <option value="">全部角色</option>
            {Object.entries(roleLabels).map(([role, label]) => (
              <option key={role} value={role}>
                {label}
              </option>
            ))}
          </select>
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={filters.is_banned}
            onChange={(event) => setFilters((current) => ({ ...current, is_banned: event.target.value as FilterState["is_banned"] }))}
          >
            <option value="">全部状态</option>
            <option value="false">未封禁</option>
            <option value="true">已封禁</option>
          </select>
          <button className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white" type="submit">
            筛选
          </button>
        </form>
      </section>

      {notice ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {loading ? <p className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载用户列表...</p> : null}

      {!loading && items.length === 0 ? (
        <section className="rounded-xl border border-dashed border-zinc-300 bg-white p-6 text-center text-sm text-zinc-500">暂无匹配用户。</section>
      ) : null}

      <div className="grid gap-3">
        {items.map((user) => {
          const draftRole = roleDrafts[user.id] || user.role;
          return (
            <article key={user.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold">{user.username}</h2>
                    <span className={user.is_banned ? "rounded-full bg-red-50 px-2 py-1 text-xs text-red-600" : "rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700"}>
                      {user.is_banned ? "已封禁" : "正常"}
                    </span>
                    {user.is_superuser ? <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-600">超级管理员</span> : null}
                    {user.is_staff ? <span className="rounded-full bg-zinc-100 px-2 py-1 text-xs text-zinc-600">Staff</span> : null}
                  </div>
                  <p className="mt-1 text-sm text-zinc-500">昵称：{user.nickname || "暂无"} · 角色：{roleLabels[user.role]}</p>
                  <p className="mt-1 text-sm text-zinc-500">邮箱：{user.email || "暂无"} · 手机：{user.phone || "暂无"}</p>
                  <p className="mt-1 text-xs text-zinc-400">
                    注册：{formatDateTime(user.date_joined)} · 最后登录：{formatDateTime(user.last_login)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 text-sm">
                  <Link href={`/admin/users/${user.id}`} className="rounded-lg border border-zinc-300 px-3 py-2 text-zinc-700">
                    查看详情
                  </Link>
                  <select
                    className="rounded-lg border border-zinc-200 px-3 py-2 outline-none focus:border-emerald-500"
                    value={draftRole}
                    disabled={operatingId === user.id}
                    onChange={(event) => setRoleDrafts((current) => ({ ...current, [user.id]: event.target.value as AdminUserRole }))}
                  >
                    {Object.entries(roleLabels).map(([role, label]) => (
                      <option key={role} value={role}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <button
                    className="rounded-lg bg-emerald-600 px-3 py-2 text-white disabled:bg-zinc-300"
                    type="button"
                    disabled={operatingId === user.id || draftRole === user.role}
                    onClick={() => void handleRoleSave(user)}
                  >
                    保存角色
                  </button>
                  {user.is_banned ? (
                    <button className="rounded-lg border border-emerald-300 px-3 py-2 text-emerald-700 disabled:border-zinc-200 disabled:text-zinc-400" type="button" disabled={operatingId === user.id} onClick={() => void handleUnban(user)}>
                      解封
                    </button>
                  ) : (
                    <button className="rounded-lg bg-red-600 px-3 py-2 text-white disabled:bg-zinc-300" type="button" disabled={operatingId === user.id} onClick={() => setBanTarget({ id: user.id, username: user.username })}>
                      封禁
                    </button>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <div className="flex items-center justify-between rounded-xl bg-white p-3 text-sm shadow-sm">
        <button className={previous ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>
          上一页
        </button>
        <span className="text-zinc-500">共 {count} 个用户</span>
        <button className={next ? "text-emerald-600" : "pointer-events-none text-zinc-400"} type="button" disabled={!next} onClick={() => setPage((current) => current + 1)}>
          下一页
        </button>
      </div>

      {banTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
          <section className="w-full max-w-lg rounded-xl bg-white p-4 shadow-xl">
            <h2 className="text-base font-semibold text-zinc-900">封禁用户：{banTarget.username}</h2>
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
                disabled={operatingId === banTarget.id}
                onClick={() => {
                  setBanTarget(null);
                  setBanReason("");
                }}
              >
                取消
              </button>
              <button className="rounded-lg bg-red-600 px-4 py-2 font-medium text-white disabled:bg-zinc-300" type="button" disabled={operatingId === banTarget.id} onClick={() => void handleBan()}>
                确认封禁
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
