"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
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

type StoredChapterDraft = {
  version: 1;
  saved_at: string;
  values: ChapterFormValues;
};

type ChapterFormProps = {
  draftStorageKey: string;
  initialChapter?: AuthorChapterDetail;
  submitLabel: string;
  submitting?: boolean;
  onSubmit: (payload: CreateAuthorChapterPayload) => Promise<boolean>;
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

function isChapterFormValues(value: unknown): value is ChapterFormValues {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ChapterFormValues>;
  return (
    typeof candidate.title === "string" &&
    typeof candidate.chapter_number === "string" &&
    typeof candidate.content === "string" &&
    typeof candidate.is_free === "boolean" &&
    typeof candidate.price === "string"
  );
}

function parseStoredDraft(rawDraft: string): StoredChapterDraft | null {
  try {
    const parsed = JSON.parse(rawDraft) as Partial<StoredChapterDraft>;
    if (parsed.version !== 1 || typeof parsed.saved_at !== "string" || !isChapterFormValues(parsed.values)) {
      return null;
    }
    return parsed as StoredChapterDraft;
  } catch {
    return null;
  }
}

function readStoredDraft(storageKey: string): StoredChapterDraft | null {
  try {
    const rawDraft = window.localStorage.getItem(storageKey);
    return rawDraft ? parseStoredDraft(rawDraft) : null;
  } catch {
    return null;
  }
}

function writeStoredDraft(storageKey: string, draft: StoredChapterDraft): boolean {
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(draft));
    return true;
  } catch {
    return false;
  }
}

function removeStoredDraft(storageKey: string) {
  try {
    window.localStorage.removeItem(storageKey);
  } catch {
    // Local draft persistence is optional and must not block chapter editing.
  }
}

function valuesMatch(first: ChapterFormValues, second: ChapterFormValues): boolean {
  return (
    first.title === second.title &&
    first.chapter_number === second.chapter_number &&
    first.content === second.content &&
    first.is_free === second.is_free &&
    first.price === second.price
  );
}

function formatSavedTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "刚刚";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function ChapterForm({
  draftStorageKey,
  initialChapter,
  submitLabel,
  submitting = false,
  onSubmit,
}: ChapterFormProps) {
  const initialValues = useMemo(() => buildInitialValues(initialChapter), [initialChapter]);
  const [values, setValues] = useState<ChapterFormValues>(initialValues);
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [error, setError] = useState<string | null>(null);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [restorableDraft, setRestorableDraft] = useState<StoredChapterDraft | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const wordCount = countWords(values.content);
  const previewParagraphs = values.content.trim().split(/\n\s*\n/).filter(Boolean);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const storedDraft = readStoredDraft(draftStorageKey);
      if (!storedDraft) {
        return;
      }

      if (valuesMatch(storedDraft.values, initialValues)) {
        removeStoredDraft(draftStorageKey);
        return;
      }

      setRestorableDraft(storedDraft);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [draftStorageKey, initialValues]);

  useEffect(() => {
    if (!hasInteracted) {
      return;
    }

    const timer = window.setTimeout(() => {
      if (valuesMatch(values, initialValues)) {
        removeStoredDraft(draftStorageKey);
        setSavedAt(null);
        return;
      }

      const nextSavedAt = new Date().toISOString();
      const draft: StoredChapterDraft = {
        version: 1,
        saved_at: nextSavedAt,
        values,
      };
      if (writeStoredDraft(draftStorageKey, draft)) {
        setSavedAt(nextSavedAt);
      }
    }, 900);

    return () => window.clearTimeout(timer);
  }, [draftStorageKey, hasInteracted, initialValues, values]);

  function updateField<K extends keyof ChapterFormValues>(key: K, value: ChapterFormValues[K]) {
    setHasInteracted(true);
    setRestorableDraft(null);
    setValues((current) => ({ ...current, [key]: value }));
  }

  function restoreDraft() {
    if (!restorableDraft) {
      return;
    }
    setValues(restorableDraft.values);
    setSavedAt(restorableDraft.saved_at);
    setRestorableDraft(null);
    setHasInteracted(true);
  }

  function discardDraft() {
    removeStoredDraft(draftStorageKey);
    setRestorableDraft(null);
    setSavedAt(null);
    setHasInteracted(false);
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

    const saved = await onSubmit({
      title: values.title.trim(),
      chapter_number: Number(values.chapter_number),
      content: values.content,
      is_free: values.is_free,
      price: values.is_free ? "0.00" : values.price || "0.00",
    });

    if (saved) {
      removeStoredDraft(draftStorageKey);
      setSavedAt(null);
      setHasInteracted(false);
    }
  }

  return (
    <form className="space-y-4 rounded-xl bg-white p-4 shadow-sm" onSubmit={handleSubmit}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-100 pb-4">
        <div className="flex rounded-lg bg-zinc-100 p-1" aria-label="章节编辑模式">
          <button
            className={`rounded-md px-3 py-1.5 text-sm ${mode === "edit" ? "bg-white font-medium text-zinc-900 shadow-sm" : "text-zinc-600"}`}
            type="button"
            aria-pressed={mode === "edit"}
            onClick={() => setMode("edit")}
          >
            编辑
          </button>
          <button
            className={`rounded-md px-3 py-1.5 text-sm ${mode === "preview" ? "bg-white font-medium text-zinc-900 shadow-sm" : "text-zinc-600"}`}
            type="button"
            aria-pressed={mode === "preview"}
            onClick={() => setMode("preview")}
          >
            预览
          </button>
        </div>
        <p className="text-xs text-zinc-500" aria-live="polite">
          {savedAt ? <>本地草稿已自动保存于 <time dateTime={savedAt}>{formatSavedTime(savedAt)}</time></> : "编辑后将自动保存本地草稿"}
        </p>
      </div>

      {restorableDraft ? (
        <div className="flex flex-col gap-3 border-l-4 border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between">
          <p>
            检测到 <time dateTime={restorableDraft.saved_at}>{formatSavedTime(restorableDraft.saved_at)}</time> 保存的本地草稿。
          </p>
          <div className="flex gap-2">
            <button className="rounded-lg bg-amber-600 px-3 py-1.5 font-medium text-white" type="button" onClick={restoreDraft}>
              恢复草稿
            </button>
            <button className="rounded-lg border border-amber-300 px-3 py-1.5" type="button" onClick={discardDraft}>
              丢弃草稿
            </button>
          </div>
        </div>
      ) : null}

      {mode === "edit" ? (
        <>
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
        </>
      ) : (
        <section className="mx-auto max-w-3xl py-4 sm:py-8" aria-label="章节阅读预览">
          <header className="border-b border-zinc-200 pb-5 text-center">
            <h2 className="text-xl font-semibold text-zinc-900 sm:text-2xl">{values.title.trim() || "未命名章节"}</h2>
            <p className="mt-2 text-sm text-zinc-500">
              第 {values.chapter_number || "-"} 章 · {wordCount} 字 · {values.is_free ? "免费" : `价格 ${values.price || "0.00"}`}
            </p>
          </header>
          <div className="mt-6 text-base leading-9 text-zinc-800 sm:text-lg sm:leading-10">
            {previewParagraphs.length > 0 ? (
              previewParagraphs.map((paragraph, index) => (
                <p className="mb-5 whitespace-pre-wrap" key={`${index}-${paragraph.slice(0, 16)}`}>
                  {paragraph}
                </p>
              ))
            ) : (
              <p className="py-12 text-center text-sm text-zinc-400">输入正文后可在这里查看阅读效果。</p>
            )}
          </div>
        </section>
      )}

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
