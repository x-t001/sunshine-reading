"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { AuthorLayout } from "@/components/AuthorLayout";
import { ChapterForm } from "@/components/ChapterForm";
import { createAuthorChapter } from "@/lib/api/author";
import { getApiErrorMessage } from "@/lib/api/request";
import type { CreateAuthorChapterPayload } from "@/types/author";

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

export default function CreateAuthorChapterPage() {
  return (
    <AuthorLayout title="创建章节" description="使用纯文本编辑章节草稿。">
      <CreateAuthorChapterContent />
    </AuthorLayout>
  );
}

function CreateAuthorChapterContent() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const novelId = readRouteParam(params.id);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(payload: CreateAuthorChapterPayload) {
    if (!novelId) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createAuthorChapter(novelId, payload);
      router.push(`/author/novels/${novelId}/chapters`);
    } catch (createError) {
      setError(getApiErrorMessage(createError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <ChapterForm submitLabel="创建章节" submitting={saving} onSubmit={handleSubmit} />
    </div>
  );
}
