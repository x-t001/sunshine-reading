"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { deleteNovelRating, getNovelRatingSummary, submitNovelRating } from "@/lib/api/ratings";
import { getApiErrorMessage } from "@/lib/api/request";
import { useAuth } from "@/hooks/useAuth";
import type { RatingSummary } from "@/types/rating";

type RatingPanelProps = {
  novelId: number | string;
};

const SCORE_OPTIONS = [1, 2, 3, 4, 5];

function formatScore(value: number): string {
  return value > 0 ? value.toFixed(1) : "暂无";
}

export function RatingPanel({ novelId }: RatingPanelProps) {
  const { user, loading: authLoading } = useAuth();
  const [summary, setSummary] = useState<RatingSummary | null>(null);
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextSummary = await getNovelRatingSummary(novelId);
      setSummary(nextSummary);
      setScore(nextSummary.my_rating?.score ?? null);
      setComment(nextSummary.my_rating?.comment ?? "");
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadSummary();
      }
    })();

    return () => {
      active = false;
    };
  }, [loadSummary]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!score) {
      setFormError("请选择 1 到 5 分。");
      return;
    }
    if (comment.length > 500) {
      setFormError("短评不能超过 500 字。");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const nextSummary = await submitNovelRating(novelId, {
        score,
        comment: comment.trim(),
      });
      setSummary(nextSummary);
      setScore(nextSummary.my_rating?.score ?? null);
      setComment(nextSummary.my_rating?.comment ?? "");
    } catch (submitError) {
      setFormError(getApiErrorMessage(submitError));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("确认删除你的评分？")) {
      return;
    }

    setDeleting(true);
    setFormError(null);
    try {
      const nextSummary = await deleteNovelRating(novelId);
      setSummary(nextSummary);
      setScore(null);
      setComment("");
    } catch (deleteError) {
      setFormError(getApiErrorMessage(deleteError));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold">小说评分</h2>
          <p className="mt-1 text-sm text-zinc-600">
            平均评分 {summary ? formatScore(summary.rating_score) : "--"} · {summary?.rating_count ?? 0} 人评分
          </p>
          {summary?.my_rating ? (
            <p className="mt-1 text-xs text-emerald-700">
              我的评分：{summary.my_rating.score} 分{summary.my_rating.comment ? ` · ${summary.my_rating.comment}` : ""}
            </p>
          ) : null}
        </div>
        {loading ? <span className="text-xs text-zinc-400">正在加载评分...</span> : null}
      </div>

      {error ? <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">评分加载失败：{error}</p> : null}

      {authLoading ? (
        <p className="mt-4 rounded-lg bg-zinc-50 px-3 py-3 text-sm text-zinc-500">正在检查登录状态...</p>
      ) : !user ? (
        <div className="mt-4 rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-3 py-4 text-sm text-zinc-600">
          登录后评分。
          <Link href="/login" className="ml-2 text-emerald-600">
            去登录
          </Link>
        </div>
      ) : (
        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <div>
            <p className="mb-2 text-sm text-zinc-700">选择评分</p>
            <div className="grid grid-cols-5 gap-2 sm:flex">
              {SCORE_OPTIONS.map((value) => (
                <button
                  key={value}
                  className={
                    score === value
                      ? "rounded-lg border border-emerald-500 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700"
                      : "rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-700"
                  }
                  type="button"
                  onClick={() => setScore(value)}
                >
                  {value} 分
                </button>
              ))}
            </div>
          </div>

          <label className="block text-sm text-zinc-700">
            短评
            <textarea
              className="mt-2 min-h-20 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              maxLength={500}
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="可选，最多 500 字"
            />
          </label>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className={comment.length > 500 ? "text-xs text-red-600" : "text-xs text-zinc-400"}>
              {comment.length}/500
            </span>
            <div className="flex gap-2">
              {summary?.my_rating ? (
                <button
                  className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700 disabled:text-zinc-400"
                  type="button"
                  disabled={deleting || saving}
                  onClick={() => void handleDelete()}
                >
                  {deleting ? "删除中..." : "删除评分"}
                </button>
              ) : null}
              <button
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
                type="submit"
                disabled={saving || deleting || !score}
              >
                {saving ? "提交中..." : summary?.my_rating ? "更新评分" : "提交评分"}
              </button>
            </div>
          </div>
          {formError ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{formError}</p> : null}
        </form>
      )}
    </section>
  );
}
