"use client";

import type { NovelComment, NovelCommentReply } from "@/types/comment";

type CommentItemProps = {
  comment: NovelComment;
  currentUserId?: number;
  deletingId: number | null;
  onDelete: (commentId: number) => void;
};

function formatCommentTime(value: string): string {
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function userName(comment: NovelComment | NovelCommentReply): string {
  return comment.user.nickname || comment.user.username;
}

function canDelete(comment: NovelComment | NovelCommentReply, currentUserId?: number): boolean {
  return Boolean(currentUserId && comment.user.id === currentUserId);
}

export function CommentItem({ comment, currentUserId, deletingId, onDelete }: CommentItemProps) {
  return (
    <article className="rounded-lg border border-zinc-200 px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="line-clamp-1 text-sm font-medium text-zinc-900">{userName(comment)}</p>
          <p className="mt-1 text-xs text-zinc-500">{formatCommentTime(comment.created_at)}</p>
        </div>
        {canDelete(comment, currentUserId) ? (
          <button
            className="shrink-0 text-xs text-zinc-500 disabled:text-zinc-300"
            type="button"
            disabled={deletingId === comment.id}
            onClick={() => onDelete(comment.id)}
          >
            {deletingId === comment.id ? "删除中..." : "删除"}
          </button>
        ) : null}
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-700">{comment.content}</p>

      {comment.replies.length > 0 ? (
        <div className="mt-3 space-y-2 rounded-lg bg-zinc-50 p-3">
          {comment.replies.slice(0, 3).map((reply) => (
            <div key={reply.id} className="border-b border-zinc-200 pb-2 last:border-0 last:pb-0">
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs font-medium text-zinc-700">{userName(reply)}</p>
                {canDelete(reply, currentUserId) ? (
                  <button
                    className="shrink-0 text-xs text-zinc-500 disabled:text-zinc-300"
                    type="button"
                    disabled={deletingId === reply.id}
                    onClick={() => onDelete(reply.id)}
                  >
                    {deletingId === reply.id ? "删除中..." : "删除"}
                  </button>
                ) : null}
              </div>
              <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-zinc-600">{reply.content}</p>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}
