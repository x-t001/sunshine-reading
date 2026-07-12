"use client";

import { useState } from "react";
import type { UpdateVideoScenePayload, VideoScene } from "@/types/video-project";

type VideoSceneEditorProps = {
  scene: VideoScene;
  saving: boolean;
  onSave: (sceneId: number, payload: UpdateVideoScenePayload) => Promise<void>;
};

export default function VideoSceneEditor({ scene, saving, onSave }: VideoSceneEditorProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<UpdateVideoScenePayload>({});

  function startEditing() {
    setDraft({
      title: scene.title,
      visual_prompt: scene.visual_prompt,
      narration_text: scene.narration_text,
      subtitle_text: scene.subtitle_text,
      duration_seconds: scene.duration_seconds,
      camera_direction: scene.camera_direction,
      mood: scene.mood,
    });
    setEditing(true);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await onSave(scene.id, draft);
      setEditing(false);
    } catch {
      // The parent keeps the API error visible while this editor stays open.
    }
  }

  if (!editing) {
    return (
      <article className="rounded-md border border-zinc-200 p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-zinc-900">
              {scene.scene_no}. {scene.title || "未命名分镜"}
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              {scene.duration_seconds} 秒 · {scene.mood || "默认氛围"}
            </p>
          </div>
          <button
            className="self-start rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
            type="button"
            onClick={startEditing}
          >
            编辑分镜
          </button>
        </div>
        <p className="mt-2 text-sm leading-6 text-zinc-600">{scene.visual_prompt}</p>
        {scene.camera_direction ? <p className="mt-2 text-xs leading-5 text-zinc-500">运镜：{scene.camera_direction}</p> : null}
        {scene.narration_text ? <p className="mt-1 text-xs leading-5 text-zinc-500">旁白：{scene.narration_text}</p> : null}
        {scene.subtitle_text ? <p className="mt-1 text-xs leading-5 text-zinc-500">字幕：{scene.subtitle_text}</p> : null}
      </article>
    );
  }

  return (
    <form className="rounded-md border border-emerald-300 bg-emerald-50/30 p-3" onSubmit={(event) => void handleSubmit(event)}>
      <div className="grid gap-3 sm:grid-cols-[1fr_120px_160px]">
        <label className="text-xs font-medium text-zinc-700">
          分镜标题
          <input
            className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
            maxLength={255}
            value={draft.title ?? ""}
            onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
          />
        </label>
        <label className="text-xs font-medium text-zinc-700">
          时长（秒）
          <input
            className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
            type="number"
            min={1}
            max={30}
            required
            value={draft.duration_seconds ?? scene.duration_seconds}
            onChange={(event) => setDraft((current) => ({ ...current, duration_seconds: Number(event.target.value) }))}
          />
        </label>
        <label className="text-xs font-medium text-zinc-700">
          氛围
          <input
            className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
            maxLength={100}
            value={draft.mood ?? ""}
            onChange={(event) => setDraft((current) => ({ ...current, mood: event.target.value }))}
          />
        </label>
      </div>

      <label className="mt-3 block text-xs font-medium text-zinc-700">
        画面提示词
        <textarea
          className="mt-1 min-h-24 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm leading-6 text-zinc-900"
          maxLength={2000}
          value={draft.visual_prompt ?? ""}
          onChange={(event) => setDraft((current) => ({ ...current, visual_prompt: event.target.value }))}
        />
      </label>

      <label className="mt-3 block text-xs font-medium text-zinc-700">
        运镜说明
        <input
          className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
          maxLength={200}
          value={draft.camera_direction ?? ""}
          onChange={(event) => setDraft((current) => ({ ...current, camera_direction: event.target.value }))}
        />
      </label>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-xs font-medium text-zinc-700">
          旁白
          <textarea
            className="mt-1 min-h-20 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm leading-6 text-zinc-900"
            maxLength={2000}
            value={draft.narration_text ?? ""}
            onChange={(event) => setDraft((current) => ({ ...current, narration_text: event.target.value }))}
          />
        </label>
        <label className="text-xs font-medium text-zinc-700">
          字幕
          <textarea
            className="mt-1 min-h-20 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm leading-6 text-zinc-900"
            maxLength={500}
            value={draft.subtitle_text ?? ""}
            onChange={(event) => setDraft((current) => ({ ...current, subtitle_text: event.target.value }))}
          />
        </label>
      </div>

      <div className="mt-3 flex justify-end gap-2">
        <button
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 disabled:text-zinc-400"
          type="button"
          disabled={saving}
          onClick={() => setEditing(false)}
        >
          取消
        </button>
        <button
          className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
          type="submit"
          disabled={saving}
        >
          {saving ? "保存中..." : "保存分镜"}
        </button>
      </div>
    </form>
  );
}
