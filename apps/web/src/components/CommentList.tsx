"use client";

import { useCallback, useEffect, useState } from "react";
import { CommentForm } from "@/components/CommentForm";
import { CommentItem } from "@/components/CommentItem";
import { deleteComment, getNovelComments } from "@/lib/api/comments";
import { getApiErrorMessage } from "@/lib/api/request";
import { useAuth } from "@/hooks/useAuth";
import type { NovelComment } from "@/types/comment";

type CommentListProps = {
  novelId: number | string;
};

export function CommentList({ novelId }: CommentListProps) {
  const { user } = useAuth();
  const [comments, setComments] = useState<NovelComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadComments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await getNovelComments(novelId, { page: 1, page_size: 10 });
      setComments(page.results);
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
        await loadComments();
      }
    })();

    return () => {
      active = false;
    };
  }, [loadComments]);

  async function handleDelete(commentId: number) {
    if (!window.confirm("确认删除这条评论？")) {
      return;
    }

    setDeletingId(commentId);
    setDeleteError(null);
    try {
      await deleteComment(commentId);
      await loadComments();
    } catch (deleteCommentError) {
      setDeleteError(getApiErrorMessage(deleteCommentError));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">读者评论</h2>
          <p className="mt-1 text-xs text-zinc-500">交流阅读感受，评论区公开可见。</p>
        </div>
      </div>

      <CommentForm novelId={novelId} onSubmitted={loadComments} />

      {deleteError ? <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{deleteError}</p> : null}
      {error ? <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">评论加载失败：{error}</p> : null}
      {loading ? <p className="mt-4 rounded-lg bg-zinc-50 px-3 py-4 text-sm text-zinc-500">正在加载评论...</p> : null}
      {!loading && !error && comments.length === 0 ? (
        <p className="mt-4 rounded-lg border border-dashed border-zinc-300 px-3 py-5 text-center text-sm text-zinc-500">
          暂无评论，来写第一条。
        </p>
      ) : null}

      {!loading && comments.length > 0 ? (
        <div className="mt-4 space-y-3">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              currentUserId={user?.id}
              deletingId={deletingId}
              onDelete={(commentId) => void handleDelete(commentId)}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
