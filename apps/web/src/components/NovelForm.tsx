"use client";

import { FormEvent, useMemo, useState } from "react";
import type { Category } from "@/types/category";
import type { CreateAuthorNovelPayload, AuthorNovelDetail } from "@/types/author";
import type { NovelStatus } from "@/types/novel";

type NovelFormValues = {
  title: string;
  category_id: string;
  cover: string;
  description: string;
  status: NovelStatus;
};

type NovelFormProps = {
  categories: Category[];
  initialNovel?: AuthorNovelDetail;
  submitLabel: string;
  submitting?: boolean;
  onSubmit: (payload: CreateAuthorNovelPayload) => Promise<void>;
};

function buildInitialValues(initialNovel?: AuthorNovelDetail): NovelFormValues {
  return {
    title: initialNovel?.title ?? "",
    category_id: initialNovel?.category ? String(initialNovel.category.id) : "",
    cover: initialNovel?.cover ?? "",
    description: initialNovel?.description ?? "",
    status: initialNovel?.status ?? "serializing",
  };
}

export function NovelForm({ categories, initialNovel, submitLabel, submitting = false, onSubmit }: NovelFormProps) {
  const initialValues = useMemo(() => buildInitialValues(initialNovel), [initialNovel]);
  const [values, setValues] = useState<NovelFormValues>(initialValues);
  const [error, setError] = useState<string | null>(null);

  function updateField<K extends keyof NovelFormValues>(key: K, value: NovelFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!values.title.trim()) {
      setError("标题不能为空。");
      return;
    }
    if (!values.category_id) {
      setError("请选择分类。");
      return;
    }
    if (!values.description.trim()) {
      setError("简介不能为空。");
      return;
    }

    await onSubmit({
      title: values.title.trim(),
      category_id: Number(values.category_id),
      cover: values.cover.trim(),
      description: values.description.trim(),
      status: values.status,
    });
  }

  return (
    <form className="space-y-4 rounded-xl bg-white p-4 shadow-sm" onSubmit={handleSubmit}>
      <label className="block text-sm text-zinc-700">
        标题
        <input
          className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          value={values.title}
          onChange={(event) => updateField("title", event.target.value)}
          placeholder="我的第一本小说"
        />
      </label>

      <label className="block text-sm text-zinc-700">
        分类
        <select
          className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          value={values.category_id}
          onChange={(event) => updateField("category_id", event.target.value)}
        >
          <option value="">请选择分类</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </label>

      <label className="block text-sm text-zinc-700">
        封面地址
        <input
          className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          value={values.cover}
          onChange={(event) => updateField("cover", event.target.value)}
          placeholder="可选，先填写图片 URL"
        />
      </label>

      <label className="block text-sm text-zinc-700">
        连载状态
        <select
          className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm outline-none focus:border-emerald-500"
          value={values.status}
          onChange={(event) => updateField("status", event.target.value as NovelStatus)}
        >
          <option value="serializing">连载中</option>
          <option value="completed">已完结</option>
          <option value="paused">暂停更新</option>
        </select>
      </label>

      <label className="block text-sm text-zinc-700">
        简介
        <textarea
          className="mt-1 min-h-32 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm leading-6 outline-none focus:border-emerald-500"
          value={values.description}
          onChange={(event) => updateField("description", event.target.value)}
          placeholder="写一段让读者理解故事看点的简介"
        />
      </label>

      {error ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

      <button
        className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
        type="submit"
        disabled={submitting}
      >
        {submitting ? "提交中..." : submitLabel}
      </button>
    </form>
  );
}
