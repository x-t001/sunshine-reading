"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { login } from "@/lib/api/auth";

function getMessage(error: unknown): string {
  return error instanceof Error ? error.message : "登录失败，请稍后重试。";
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login({ username, password });
      router.push("/profile");
      router.refresh();
    } catch (loginError) {
      setError(getMessage(loginError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-xl bg-white p-4 shadow-sm">
      <h1 className="text-lg font-semibold">登录</h1>
      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
        <label className="block text-sm text-zinc-700">
          用户名
          <input
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="block text-sm text-zinc-700">
          密码
          <input
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <button className="w-full rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300" type="submit" disabled={loading}>
          {loading ? "登录中..." : "登录"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-zinc-500">
        还没有账号？{" "}
        <Link href="/register" className="text-emerald-600">
          去注册
        </Link>
      </p>
    </section>
  );
}
