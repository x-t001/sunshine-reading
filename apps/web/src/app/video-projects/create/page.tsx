"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useMemo, useState } from "react";
import {
  createVideoProject,
  createVideoProjectFromChapter,
  createVideoProjectFromNovel,
  generateVideoStoryDraft,
  getVideoSourceChapters,
  getVideoSourceNovels,
} from "@/lib/api/video-projects";
import { getApiErrorMessage } from "@/lib/api/request";
import { useAuth } from "@/hooks/useAuth";
import type { VideoSourceChapter, VideoSourceNovel, VideoStoryGenre, VideoStoryTone } from "@/types/video-project";

const MIN_TEXT_LENGTH = 500;
const MAX_TEXT_LENGTH = 3000;
type SourceMode = "text" | "chapter" | "novel";

export default function CreateVideoProjectPage() {
  const router = useRouter();
  const { user, loading: authLoading, error: authError } = useAuth();
  const [sourceMode, setSourceMode] = useState<SourceMode>("text");
  const [title, setTitle] = useState("");
  const [inputText, setInputText] = useState("");
  const [durationTarget, setDurationTarget] = useState(60);
  const [storyPrompt, setStoryPrompt] = useState("");
  const [storyGenre, setStoryGenre] = useState<VideoStoryGenre>("fantasy");
  const [storyTone, setStoryTone] = useState<VideoStoryTone>("cinematic");
  const [generatingStory, setGeneratingStory] = useState(false);
  const [sourceChapters, setSourceChapters] = useState<VideoSourceChapter[]>([]);
  const [selectedChapterId, setSelectedChapterId] = useState<number | "">("");
  const [chapterKeyword, setChapterKeyword] = useState("");
  const [loadingChapters, setLoadingChapters] = useState(false);
  const [sourceNovels, setSourceNovels] = useState<VideoSourceNovel[]>([]);
  const [selectedNovelId, setSelectedNovelId] = useState<number | "">("");
  const [startChapterNumber, setStartChapterNumber] = useState<number | "">("");
  const [endChapterNumber, setEndChapterNumber] = useState<number | "">("");
  const [novelKeyword, setNovelKeyword] = useState("");
  const [loadingNovels, setLoadingNovels] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const textLength = inputText.trim().length;
  const textState = useMemo(() => {
    if (textLength < MIN_TEXT_LENGTH) {
      return `还需要 ${MIN_TEXT_LENGTH - textLength} 个字`;
    }
    if (textLength > MAX_TEXT_LENGTH) {
      return `已超出 ${textLength - MAX_TEXT_LENGTH} 个字`;
    }
    return "长度符合要求";
  }, [textLength]);
  const canSubmit = textLength >= MIN_TEXT_LENGTH && textLength <= MAX_TEXT_LENGTH && !submitting;
  const canSubmitChapter = selectedChapterId !== "" && !submitting;
  const selectedNovel = useMemo(
    () => sourceNovels.find((novel) => novel.id === selectedNovelId),
    [selectedNovelId, sourceNovels],
  );
  const selectedRangeLength =
    startChapterNumber !== "" && endChapterNumber !== "" ? endChapterNumber - startChapterNumber + 1 : 0;
  const canSubmitNovel = Boolean(
    selectedNovel &&
      startChapterNumber !== "" &&
      endChapterNumber !== "" &&
      startChapterNumber >= selectedNovel.first_chapter_number &&
      endChapterNumber <= selectedNovel.last_chapter_number &&
      selectedRangeLength >= 1 &&
      selectedRangeLength <= 10 &&
      !submitting,
  );
  const canGenerateStory = storyPrompt.trim().length >= 10 && !generatingStory;

  const loadSourceChapters = useCallback(async (keyword = "") => {
    setLoadingChapters(true);
    setError(null);
    try {
      const result = await getVideoSourceChapters({ keyword: keyword.trim() || undefined, page_size: 50 });
      setSourceChapters(result.results);
      setSelectedChapterId((current) =>
        result.results.some((chapter) => chapter.id === current) ? current : (result.results[0]?.id ?? ""),
      );
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoadingChapters(false);
    }
  }, []);

  const loadSourceNovels = useCallback(async (keyword = "") => {
    setLoadingNovels(true);
    setError(null);
    try {
      const result = await getVideoSourceNovels({ keyword: keyword.trim() || undefined, page_size: 50 });
      const nextNovel = result.results.find((novel) => novel.id === selectedNovelId) ?? result.results[0];
      setSourceNovels(result.results);
      setSelectedNovelId(nextNovel?.id ?? "");
      setStartChapterNumber(nextNovel?.first_chapter_number ?? "");
      setEndChapterNumber(
        nextNovel ? Math.min(nextNovel.last_chapter_number, nextNovel.first_chapter_number + 2) : "",
      );
    } catch (loadError) {
      setError(getApiErrorMessage(loadError));
    } finally {
      setLoadingNovels(false);
    }
  }, [selectedNovelId]);

  function handleSourceModeChange(mode: SourceMode) {
    setSourceMode(mode);
    if (mode === "chapter" && sourceChapters.length === 0) {
      void loadSourceChapters();
    }
    if (mode === "novel" && sourceNovels.length === 0) {
      void loadSourceNovels();
    }
  }

  function handleNovelSelection(value: string) {
    const novelId = Number(value);
    const novel = sourceNovels.find((item) => item.id === novelId);
    setSelectedNovelId(novel?.id ?? "");
    setStartChapterNumber(novel?.first_chapter_number ?? "");
    setEndChapterNumber(novel ? Math.min(novel.last_chapter_number, novel.first_chapter_number + 2) : "");
  }

  function handleStartChapterChange(value: string) {
    if (!selectedNovel || value === "") {
      setStartChapterNumber("");
      return;
    }
    const nextStart = Number(value);
    setStartChapterNumber(nextStart);
    setEndChapterNumber((current) => {
      const currentEnd = current === "" ? nextStart : current;
      return Math.min(Math.max(currentEnd, nextStart), selectedNovel.last_chapter_number, nextStart + 9);
    });
  }

  async function handleGenerateStory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canGenerateStory) {
      return;
    }

    setGeneratingStory(true);
    setError(null);
    try {
      const draft = await generateVideoStoryDraft({
        prompt: storyPrompt.trim(),
        genre: storyGenre,
        tone: storyTone,
        duration_target: durationTarget,
      });
      setTitle(draft.title);
      setInputText(draft.input_text);
      setDurationTarget(draft.duration_target);
    } catch (generateError) {
      setError(getApiErrorMessage(generateError));
    } finally {
      setGeneratingStory(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const project = await createVideoProject({
        source_type: "text",
        title: title.trim() || undefined,
        input_text: inputText.trim(),
        duration_target: durationTarget,
        aspect_ratio: "9:16",
        style_preset: "cinematic_story",
      });
      router.push(`/video-projects/${project.id}`);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleChapterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmitChapter) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const project = await createVideoProjectFromChapter({
        chapter_id: selectedChapterId,
        title: title.trim() || undefined,
        duration_target: durationTarget,
        aspect_ratio: "9:16",
        style_preset: "cinematic_story",
      });
      router.push(`/video-projects/${project.id}`);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleNovelSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmitNovel || selectedNovelId === "" || startChapterNumber === "" || endChapterNumber === "") {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const project = await createVideoProjectFromNovel({
        novel_id: selectedNovelId,
        start_chapter_number: startChapterNumber,
        end_chapter_number: endChapterNumber,
        title: title.trim() || undefined,
        duration_target: durationTarget,
        aspect_ratio: "9:16",
        style_preset: "cinematic_story",
      });
      router.push(`/video-projects/${project.id}`);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading) {
    return <section className="rounded-lg bg-white p-4 text-sm text-zinc-500 shadow-sm">正在检查登录状态...</section>;
  }

  if (!user) {
    return (
      <section className="rounded-lg bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold">新建短视频项目</h1>
        <p className="mt-3 text-sm text-zinc-600">{authError || "当前未登录，请先登录后创建短视频项目。"}</p>
        <Link href="/login" className="mt-4 inline-flex rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white">
          去登录
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="rounded-lg bg-white p-4 shadow-sm">
        <Link href="/video-projects" className="text-sm font-medium text-emerald-700">
          返回项目列表
        </Link>
        <h1 className="mt-3 text-lg font-semibold text-zinc-900">新建短视频项目</h1>
        <p className="mt-1 text-sm text-zinc-500">选择文本、单章或小说章节范围作为内容来源，再进入分镜制作。</p>
      </div>

      {error ? <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p> : null}

      <section className="rounded-lg bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-zinc-900">内容来源</h2>
        <div className="mt-3 grid grid-cols-3 gap-1 rounded-md bg-zinc-100 p-1">
          <button
            className={sourceMode === "text" ? "rounded-md bg-white px-3 py-2 text-sm font-medium text-zinc-900 shadow-sm" : "rounded-md px-3 py-2 text-sm text-zinc-600"}
            type="button"
            onClick={() => handleSourceModeChange("text")}
          >
            粘贴文本
          </button>
          <button
            className={sourceMode === "chapter" ? "rounded-md bg-white px-3 py-2 text-sm font-medium text-zinc-900 shadow-sm" : "rounded-md px-3 py-2 text-sm text-zinc-600"}
            type="button"
            onClick={() => handleSourceModeChange("chapter")}
          >
            选择章节
          </button>
          <button
            className={sourceMode === "novel" ? "rounded-md bg-white px-3 py-2 text-sm font-medium text-zinc-900 shadow-sm" : "rounded-md px-3 py-2 text-sm text-zinc-600"}
            type="button"
            onClick={() => handleSourceModeChange("novel")}
          >
            选择小说
          </button>
        </div>
      </section>

      {sourceMode === "text" ? (
        <>
      <form className="space-y-4 rounded-lg bg-white p-4 shadow-sm" onSubmit={handleGenerateStory}>
        <div>
          <h2 className="text-base font-semibold text-zinc-900">生成剧情草稿</h2>
          <p className="mt-1 text-sm text-zinc-500">没有现成故事时，先用一句创意生成可创建项目的文本草稿。</p>
        </div>

        <label className="block">
          <span className="text-sm font-medium text-zinc-700">剧情创意</span>
          <textarea
            className="mt-2 min-h-24 w-full resize-y rounded-md border border-zinc-300 px-3 py-2 text-sm leading-6 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            value={storyPrompt}
            maxLength={300}
            placeholder="例如：边城少年捡到会发光的旧书，被迫在家人和真相之间做选择。"
            onChange={(event) => setStoryPrompt(event.target.value)}
          />
          <span className={storyPrompt.trim().length < 10 ? "mt-2 block text-xs text-amber-700" : "mt-2 block text-xs text-zinc-500"}>
            至少输入 10 个字。
          </span>
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-zinc-700">题材</span>
            <select
              className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              value={storyGenre}
              onChange={(event) => setStoryGenre(event.target.value as VideoStoryGenre)}
            >
              <option value="fantasy">东方幻想</option>
              <option value="urban">都市现实</option>
              <option value="romance">情感成长</option>
              <option value="sci_fi">科幻想象</option>
              <option value="mystery">悬疑推理</option>
              <option value="history">历史传奇</option>
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-700">风格</span>
            <select
              className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              value={storyTone}
              onChange={(event) => setStoryTone(event.target.value as VideoStoryTone)}
            >
              <option value="cinematic">电影感</option>
              <option value="warm">温暖治愈</option>
              <option value="suspense">悬念紧张</option>
              <option value="high_energy">高燃爽感</option>
              <option value="sad">克制伤感</option>
            </select>
          </label>
        </div>

        <button
          className="w-full rounded-md border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 disabled:border-zinc-200 disabled:bg-zinc-100 disabled:text-zinc-400"
          type="submit"
          disabled={!canGenerateStory}
        >
          {generatingStory ? "生成中..." : "生成并填入下方正文"}
        </button>
      </form>

      <form className="space-y-4 rounded-lg bg-white p-4 shadow-sm" onSubmit={handleSubmit}>
        <label className="block">
          <span className="text-sm font-medium text-zinc-700">项目标题</span>
          <input
            className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            value={title}
            maxLength={255}
            placeholder="例如：星火神途宣传短片"
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium text-zinc-700">故事或文章文本</span>
          <textarea
            className="mt-2 min-h-72 w-full resize-y rounded-md border border-zinc-300 px-3 py-2 text-sm leading-6 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            value={inputText}
            maxLength={MAX_TEXT_LENGTH + 200}
            placeholder="粘贴 500 到 3000 字的故事、小说片段或文章内容。"
            onChange={(event) => setInputText(event.target.value)}
          />
          <span className={textLength > MAX_TEXT_LENGTH || textLength < MIN_TEXT_LENGTH ? "mt-2 block text-xs text-amber-700" : "mt-2 block text-xs text-emerald-700"}>
            {textLength}/{MAX_TEXT_LENGTH} · {textState}
          </span>
        </label>

        <label className="block">
          <span className="text-sm font-medium text-zinc-700">目标时长</span>
          <select
            className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            value={durationTarget}
            onChange={(event) => setDurationTarget(Number(event.target.value))}
          >
            <option value={30}>30 秒</option>
            <option value={45}>45 秒</option>
            <option value={60}>60 秒</option>
            <option value={90}>90 秒</option>
          </select>
        </label>

        <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-600">
          当前版本会保存项目草稿，不会生成真实视频文件。后续迭代会继续加入 AI 分镜、图片、旁白和渲染。
        </div>

        <button
          className="w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
          type="submit"
          disabled={!canSubmit}
        >
          {submitting ? "创建中..." : "创建草稿"}
        </button>
      </form>
        </>
      ) : sourceMode === "chapter" ? (
        <form className="space-y-4 rounded-lg bg-white p-4 shadow-sm" onSubmit={handleChapterSubmit}>
          <div>
            <h2 className="text-base font-semibold text-zinc-900">选择可用章节</h2>
            <p className="mt-1 text-sm text-zinc-500">公开已发布章节和你自己创作的章节会显示在这里。</p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="flex-1">
              <span className="sr-only">搜索章节</span>
              <input
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                value={chapterKeyword}
                maxLength={100}
                placeholder="搜索小说或章节标题"
                onChange={(event) => setChapterKeyword(event.target.value)}
              />
            </label>
            <button
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 disabled:text-zinc-400"
              type="button"
              disabled={loadingChapters}
              onClick={() => void loadSourceChapters(chapterKeyword)}
            >
              {loadingChapters ? "搜索中..." : "搜索"}
            </button>
          </div>

          {sourceChapters.length > 0 ? (
            <label className="block">
              <span className="text-sm font-medium text-zinc-700">章节</span>
              <select
                className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                value={selectedChapterId}
                onChange={(event) => setSelectedChapterId(Number(event.target.value))}
              >
                {sourceChapters.map((chapter) => (
                  <option key={chapter.id} value={chapter.id}>
                    {chapter.novel_title} · 第 {chapter.chapter_number} 章 {chapter.title} · {chapter.source_access === "owned" ? "我的章节" : chapter.source_access === "admin" ? "管理可见" : "公开章节"}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-4 text-sm text-zinc-500">
              {loadingChapters ? "正在加载章节..." : "没有找到可用章节。"}
            </p>
          )}

          <label className="block">
            <span className="text-sm font-medium text-zinc-700">项目标题（可选）</span>
            <input
              className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              value={title}
              maxLength={255}
              placeholder="默认使用小说名和章节名"
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-700">目标时长</span>
            <select
              className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              value={durationTarget}
              onChange={(event) => setDurationTarget(Number(event.target.value))}
            >
              <option value={30}>30 秒</option>
              <option value={45}>45 秒</option>
              <option value={60}>60 秒</option>
              <option value={90}>90 秒</option>
            </select>
          </label>

          <button
            className="w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
            type="submit"
            disabled={!canSubmitChapter}
          >
            {submitting ? "创建中..." : "从章节创建项目"}
          </button>
        </form>
      ) : (
        <form className="space-y-4 rounded-lg bg-white p-4 shadow-sm" onSubmit={handleNovelSubmit}>
          <div>
            <h2 className="text-base font-semibold text-zinc-900">选择小说章节范围</h2>
            <p className="mt-1 text-sm text-zinc-500">公开已审核小说和你自己的小说会显示在这里。</p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="flex-1">
              <span className="sr-only">搜索小说</span>
              <input
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                value={novelKeyword}
                maxLength={100}
                placeholder="搜索小说或作者"
                onChange={(event) => setNovelKeyword(event.target.value)}
              />
            </label>
            <button
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 disabled:text-zinc-400"
              type="button"
              disabled={loadingNovels}
              onClick={() => void loadSourceNovels(novelKeyword)}
            >
              {loadingNovels ? "搜索中..." : "搜索"}
            </button>
          </div>

          {sourceNovels.length > 0 ? (
            <label className="block">
              <span className="text-sm font-medium text-zinc-700">小说</span>
              <select
                className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                value={selectedNovelId}
                onChange={(event) => handleNovelSelection(event.target.value)}
              >
                {sourceNovels.map((novel) => (
                  <option key={novel.id} value={novel.id}>
                    {novel.title} · {novel.author_name} · {novel.chapter_count} 章 · {novel.source_access === "owned" ? "我的小说" : novel.source_access === "admin" ? "管理可见" : "公开小说"}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="rounded-md border border-dashed border-zinc-300 bg-zinc-50 p-4 text-sm text-zinc-500">
              {loadingNovels ? "正在加载小说..." : "没有找到可用小说。"}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-zinc-700">起始章节</span>
              <input
                className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 disabled:bg-zinc-100"
                type="number"
                value={startChapterNumber}
                min={selectedNovel?.first_chapter_number}
                max={selectedNovel?.last_chapter_number}
                disabled={!selectedNovel}
                onChange={(event) => handleStartChapterChange(event.target.value)}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-zinc-700">结束章节</span>
              <input
                className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 disabled:bg-zinc-100"
                type="number"
                value={endChapterNumber}
                min={startChapterNumber === "" ? selectedNovel?.first_chapter_number : startChapterNumber}
                max={
                  selectedNovel && startChapterNumber !== ""
                    ? Math.min(selectedNovel.last_chapter_number, startChapterNumber + 9)
                    : selectedNovel?.last_chapter_number
                }
                disabled={!selectedNovel}
                onChange={(event) => setEndChapterNumber(event.target.value === "" ? "" : Number(event.target.value))}
              />
            </label>
          </div>

          {selectedNovel ? (
            <p className={canSubmitNovel ? "text-xs text-emerald-700" : "text-xs text-amber-700"}>
              可用范围：第 {selectedNovel.first_chapter_number}-{selectedNovel.last_chapter_number} 章 · 当前选择 {Math.max(0, selectedRangeLength)} 章 · 最多 10 章
            </p>
          ) : null}

          <label className="block">
            <span className="text-sm font-medium text-zinc-700">项目标题（可选）</span>
            <input
              className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              value={title}
              maxLength={255}
              placeholder="默认使用小说名和章节范围"
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-700">目标时长</span>
            <select
              className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              value={durationTarget}
              onChange={(event) => setDurationTarget(Number(event.target.value))}
            >
              <option value={30}>30 秒</option>
              <option value={45}>45 秒</option>
              <option value={60}>60 秒</option>
              <option value={90}>90 秒</option>
            </select>
          </label>

          <button
            className="w-full rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300"
            type="submit"
            disabled={!canSubmitNovel}
          >
            {submitting ? "创建中..." : "从小说创建项目"}
          </button>
        </form>
      )}
    </section>
  );
}
