"use client";

import { FormEvent, useState } from "react";

type RejectDialogProps = {
  open: boolean;
  title: string;
  submitting?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: (reason: string) => Promise<void> | void;
};

export function RejectDialog({ open, title, submitting = false, error, onCancel, onConfirm }: RejectDialogProps) {
  const [reason, setReason] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextReason = reason.trim();
    if (!nextReason) {
      setLocalError("请填写驳回原因。");
      return;
    }
    setLocalError(null);
    await onConfirm(nextReason);
    setReason("");
  }

  function handleCancel() {
    setReason("");
    setLocalError(null);
    onCancel();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <form className="w-full max-w-lg rounded-xl bg-white p-4 shadow-xl" onSubmit={(event) => void handleSubmit(event)}>
        <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
        <textarea
          className="mt-3 min-h-32 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          value={reason}
          maxLength={1000}
          onChange={(event) => setReason(event.target.value)}
          placeholder="请输入驳回原因，最多 1000 字"
        />
        <div className="mt-1 flex justify-between text-xs text-zinc-400">
          <span>{localError || error || ""}</span>
          <span>{reason.length}/1000</span>
        </div>
        <div className="mt-4 flex justify-end gap-2 text-sm">
          <button
            className="rounded-lg border border-zinc-300 px-4 py-2 text-zinc-700"
            type="button"
            disabled={submitting}
            onClick={handleCancel}
          >
            取消
          </button>
          <button className="rounded-lg bg-red-600 px-4 py-2 font-medium text-white disabled:bg-zinc-300" type="submit" disabled={submitting}>
            {submitting ? "提交中..." : "确认驳回"}
          </button>
        </div>
      </form>
    </div>
  );
}
