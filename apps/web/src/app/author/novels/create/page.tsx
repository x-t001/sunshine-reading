"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthorLayout } from "@/components/AuthorLayout";
import { NovelForm } from "@/components/NovelForm";
import { createAuthorNovel } from "@/lib/api/author";
import { getCategories } from "@/lib/api/categories";
import { getApiErrorMessage } from "@/lib/api/request";
import type { CreateAuthorNovelPayload } from "@/types/author";
import type { Category } from "@/types/category";

export default function CreateAuthorNovelPage() {
  return (
    <AuthorLayout title="创建作品" description="先创建小说草稿，再进入章节管理。">
      <CreateAuthorNovelContent />
    </AuthorLayout>
  );
}

function CreateAuthorNovelContent() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCategories(await getCategories());
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadCategories();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadCategories]);

  async function handleSubmit(payload: CreateAuthorNovelPayload) {
    setSaving(true);
    setError(null);
    try {
      const novel = await createAuthorNovel(payload);
      router.push(`/author/novels/${novel.id}`);
    } catch (createError) {
      setError(getApiErrorMessage(createError));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载分类...</section>;
  }

  return (
    <div className="space-y-4">
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <NovelForm categories={categories} submitLabel="创建作品" submitting={saving} onSubmit={handleSubmit} />
    </div>
  );
}
