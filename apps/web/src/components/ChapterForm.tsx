"use client";

import { FormEvent, useMemo, useState } from "react";
import type {
  AuthorChapterDetail,
  CreateAuthorChapterPayload,
} from "@/types/author";

type ChapterFormValues = {
  title: string;
  chapter_number: string;
  content: string;
  is_free: boolean;
  price: string;
};

type ChapterFormProps = {
  initialChapter?: AuthorChapterDetail;
  submitLabel: string;
  submitting?: boolean;
  onSubmit: (payload: CreateAuthorChapterPayload) => Promise<void>;
};

function countWords(content: string): number {
  return content.replace(/\s+/g, "").length;
}

function buildInitialValues(initialChapter?: AuthorChapterDetail): ChapterFormValues {
  return {
    title: initialChapter?.title ?? "",
    chapter_number: initialChapter ? String(initialChapter.chapter_number) : "",
    content: initialChapter?.content ?? "",
    is_free: initialChapter?.is_free ?? true,
    price: initialChapter?.price ?? "0.00",
  };
}

export function ChapterForm({ initialChapter, submitLabel, submitting = false, onSubmit }: ChapterFormProps) {
  const initialValues = useMemo(() => buildInitialValues(initialChapter), [initialChapter]);
  const [values, setValues] = useState<ChapterFormValues>(initialValues);
  const [error, setError] = useState<string | null>(null);
  const wordCount = countWords(values.content);

  function updateField<K extends keyof ChapterFormValues>(key: K, value: ChapterFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!values.title.trim()) {
      setError("章节标题不能为空。");
      return;
    }
    if (!values.chapter_number || Number(values.chapter_number) < 1) {
      setError("章节序号必须大于 0。");
      return;
    }
    if (!values.content.trim()) {
      setError("章节正文不能为空。");
      return;
    }

    await onSubmit({
      title: values.title.trim(),
      chapter_number: Number(values.chapter_number),
      content: values.content,
      is_free: values.is_free,
      price: values.is_free ? "0.00" : values.price || "0.00",
    });
  }

  return (
    <form className="space-y-4 rounded-xl bg-white p-4 shadow-sm" onSubmit={handleSubmit}>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block text-sm text-zinc-700">
          章节标题
          <input
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={values.title}
            onChange={(event) => updateField("title", event.target.value)}
            placeholder="第一章 初遇"
          />
        </label>

        <label className="block text-sm text-zinc-700">
          章节序号
          <input
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            min={1}
            type="number"
            value={values.chapter_number}
            onChange={(event) => updateField("chapter_number", event.target.value)}
          />
        </label>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="flex items-center gap-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-700">
          <input
            type="checkbox"
            checked={values.is_free}
            onChange={(event) => updateField("is_free", event.target.checked)}
          />
          免费章节
        </label>

        <label className="block text-sm text-zinc-700">
          价格
          <input
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500 disabled:bg-zinc-100"
            disabled={values.is_free}
            min={0}
            step="0.01"
            type="number"
            value={values.price}
            onChange={(event) => updateField("price", event.target.value)}
          />
        </label>
      </div>

      <label className="block text-sm text-zinc-700">
        正文
        <textarea
          className="mt-1 min-h-[420px] w-full rounded-lg border border-zinc-200 px-3 py-3 text-base leading-8 outline-none focus:border-emerald-500"
          value={values.content}
          onChange={(event) => updateField("content", event.target.value)}
          placeholder="在这里输入章节正文"
        />
      </label>

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-500">
        <span>当前字数：{wordCount} 字</span>
        {initialChapter ? <span>当前状态：{initialChapter.status} / {initialChapter.audit_status}</span> : null}
      </div>

      {error ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      <button
        className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
        type="submit"
        disabled={submitting}
      >
        {submitting ? "保存中..." : submitLabel}
      </button>
    </form>
  );
}
