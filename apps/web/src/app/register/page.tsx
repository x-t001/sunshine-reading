"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { register } from "@/lib/api/auth";

function getMessage(error: unknown): string {
  return error instanceof Error ? error.message : "注册失败，请稍后重试。";
}

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await register({
        username,
        nickname,
        email,
        password,
        password_confirm: passwordConfirm,
      });
      router.push("/login");
    } catch (registerError) {
      setError(getMessage(registerError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-xl bg-white p-4 shadow-sm">
      <h1 className="text-lg font-semibold">注册</h1>
      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
        <label className="block text-sm text-zinc-700">
          用户名
          <input className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required />
        </label>
        <label className="block text-sm text-zinc-700">
          昵称
          <input className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" value={nickname} onChange={(event) => setNickname(event.target.value)} />
        </label>
        <label className="block text-sm text-zinc-700">
          邮箱
          <input className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
        </label>
        <label className="block text-sm text-zinc-700">
          密码
          <input className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" required />
        </label>
        <label className="block text-sm text-zinc-700">
          确认密码
          <input className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500" type="password" value={passwordConfirm} onChange={(event) => setPasswordConfirm(event.target.value)} autoComplete="new-password" required />
        </label>
        {error ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
        <button className="w-full rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300" type="submit" disabled={loading}>
          {loading ? "注册中..." : "注册"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-zinc-500">
        已有账号？{" "}
        <Link href="/login" className="text-emerald-600">
          去登录
        </Link>
      </p>
    </section>
  );
}
