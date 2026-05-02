"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { updateCurrentUser } from "@/lib/api/users";
import { useAuth } from "@/hooks/useAuth";

function getMessage(error: unknown): string {
  return error instanceof Error ? error.message : "操作失败，请稍后重试。";
}

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading, error, logout, reload } = useAuth();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaved(false);

    try {
      const formData = new FormData(event.currentTarget);
      await updateCurrentUser({
        nickname: String(formData.get("nickname") || ""),
        email: String(formData.get("email") || ""),
        bio: String(formData.get("bio") || ""),
        phone: String(formData.get("phone") || ""),
      });
      setSaved(true);
      await reload();
    } catch (updateError) {
      setSaveError(getMessage(updateError));
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    logout();
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载个人资料...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-xl bg-white p-4 shadow-sm">
        <h1 className="text-lg font-semibold">个人中心</h1>
        <p className="mt-3 text-sm text-zinc-600">{error || "当前未登录，请先登录。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-2xl rounded-xl bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">个人中心</h1>
          <p className="mt-1 text-sm text-zinc-500">用户名：{user.username}</p>
          <p className="text-sm text-zinc-500">角色：{user.role}</p>
        </div>
        <button className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-700" type="button" onClick={handleLogout}>
          退出登录
        </button>
      </div>

      <form key={user.id} className="mt-5 space-y-3" onSubmit={handleSubmit}>
        <ProfileInput label="昵称" name="nickname" defaultValue={user.nickname || ""} />
        <ProfileInput label="邮箱" name="email" type="email" defaultValue={user.email || ""} />
        <ProfileInput label="手机" name="phone" defaultValue={user.phone || ""} />
        <label className="block text-sm text-zinc-700">
          简介
          <textarea
            name="bio"
            className="mt-1 min-h-24 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            defaultValue={user.bio || ""}
          />
        </label>
        {saveError ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{saveError}</p> : null}
        {saved ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">资料已保存。</p> : null}
        <button className="w-full rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300" type="submit" disabled={saving}>
          {saving ? "保存中..." : "保存资料"}
        </button>
      </form>
    </section>
  );
}

function ProfileInput({
  label,
  name,
  type = "text",
  defaultValue,
}: {
  label: string;
  name: string;
  type?: string;
  defaultValue: string;
}) {
  return (
    <label className="block text-sm text-zinc-700">
      {label}
      <input
        name={name}
        className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        type={type}
        defaultValue={defaultValue}
      />
    </label>
  );
}
