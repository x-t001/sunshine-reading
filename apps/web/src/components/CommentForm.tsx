"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { createNovelComment } from "@/lib/api/comments";
import { getApiErrorMessage } from "@/lib/api/request";
import { useAuth } from "@/hooks/useAuth";

type CommentFormProps = {
  novelId: number | string;
  onSubmitted: () => Promise<void> | void;
};

export function CommentForm({ novelId, onSubmitted }: CommentFormProps) {
  const { user, loading: authLoading } = useAuth();
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedContent = content.trim();
    if (!trimmedContent) {
      setError("评论内容不能为空。");
      return;
    }
    if (trimmedContent.length > 1000) {
      setError("评论内容不能超过 1000 字。");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await createNovelComment(novelId, {
        content: trimmedContent,
        parent_id: null,
        chapter_id: null,
      });
      setContent("");
      await onSubmitted();
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading) {
    return <p className="rounded-lg bg-zinc-50 px-3 py-3 text-sm text-zinc-500">正在检查登录状态...</p>;
  }

  if (!user) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-3 py-4 text-sm text-zinc-600">
        登录后发表评论。
        <Link href="/login" className="ml-2 text-emerald-600">
          去登录
        </Link>
      </div>
    );
  }

  return (
    <form className="space-y-2" onSubmit={handleSubmit}>
      <label className="block text-sm text-zinc-700">
        发表评论
        <textarea
          className="mt-2 min-h-24 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          maxLength={1000}
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="写下你的阅读感受..."
        />
      </label>
      <div className="flex items-center justify-between gap-3">
        <span className={content.length > 1000 ? "text-xs text-red-600" : "text-xs text-zinc-400"}>
          {content.length}/1000
        </span>
        <button
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
          type="submit"
          disabled={submitting || !content.trim()}
        >
          {submitting ? "提交中..." : "发布评论"}
        </button>
      </div>
      {error ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
    </form>
  );
}
