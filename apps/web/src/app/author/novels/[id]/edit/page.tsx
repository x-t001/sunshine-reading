"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthorLayout } from "@/components/AuthorLayout";
import { NovelForm } from "@/components/NovelForm";
import { getAuthorNovelDetail, updateAuthorNovel } from "@/lib/api/author";
import { getCategories } from "@/lib/api/categories";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AuthorNovelDetail, UpdateAuthorNovelPayload } from "@/types/author";
import type { Category } from "@/types/category";

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function EditAuthorNovelPage() {
  return (
    <AuthorLayout title="编辑作品" description="修改作品基础信息。已通过作品修改后会重新进入审核流程。">
      <EditAuthorNovelContent />
    </AuthorLayout>
  );
}

function EditAuthorNovelContent() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = readRouteParam(params.id);
  const [novel, setNovel] = useState<AuthorNovelDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [novelDetail, categoryList] = await Promise.all([getAuthorNovelDetail(id), getCategories()]);
      setNovel(novelDetail);
      setCategories(categoryList);
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await Promise.resolve();
      if (active) {
        await loadData();
      }
    })();
    return () => {
      active = false;
    };
  }, [loadData]);

  async function handleSubmit(payload: UpdateAuthorNovelPayload) {
    if (!id) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const nextNovel = await updateAuthorNovel(id, payload);
      router.push(`/author/novels/${nextNovel.id}`);
    } catch (updateError) {
      setError(getApiErrorMessage(updateError));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载作品...</section>;
  }

  if (!novel) {
    return <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error || "作品不存在或无权访问。"}</section>;
  }

  return (
    <div className="space-y-4">
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <NovelForm key={novel.id} categories={categories} initialNovel={novel} submitLabel="保存作品" submitting={saving} onSubmit={handleSubmit} />
    </div>
  );
}
