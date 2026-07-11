"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { NovelAiChat } from "@/components/NovelAiChat";
import { ReadingToolbar } from "@/components/ReadingToolbar";
import { getChapterDetail } from "@/lib/api/chapters";
import { getReadingHistory, reportReadingHistory } from "@/lib/api/reading-history";
import { ApiRequestError, getApiErrorMessage } from "@/lib/api/request";
import { clearTokens, getAccessToken } from "@/lib/auth/token";
import type { ChapterDetail } from "@/types/chapter";

type ReaderSettings = {
  fontSize: number;
  nightMode: boolean;
  wideMode: boolean;
};

const DEFAULT_READER_SETTINGS: ReaderSettings = {
  fontSize: 18,
  nightMode: false,
  wideMode: false,
};
const READER_SETTINGS_KEY = "sunshine-reading:reader-settings";
const POSITION_KEY_PREFIX = "sunshine-reading:reading-position:";
const LOCAL_SAVE_DELAY = 500;
const REMOTE_SYNC_DELAY = 10000;

function readRouteParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] : value || "";
}

function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 401;
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(value)));
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function getPositionKey(novelId: string, chapterId: string): string {
  return `${POSITION_KEY_PREFIX}${novelId}:${chapterId}`;
}

function readStoredSettings(): ReaderSettings {
  if (!canUseStorage()) {
    return DEFAULT_READER_SETTINGS;
  }

  try {
    const raw = window.localStorage.getItem(READER_SETTINGS_KEY);
    if (!raw) {
      return DEFAULT_READER_SETTINGS;
    }
    const parsed = JSON.parse(raw) as Partial<ReaderSettings>;
    return {
      fontSize: Math.max(14, Math.min(28, Number(parsed.fontSize) || DEFAULT_READER_SETTINGS.fontSize)),
      nightMode: Boolean(parsed.nightMode),
      wideMode: Boolean(parsed.wideMode),
    };
  } catch {
    return DEFAULT_READER_SETTINGS;
  }
}

function readLocalPosition(novelId: string, chapterId: string): number {
  if (!canUseStorage()) {
    return 0;
  }

  const value = Number(window.localStorage.getItem(getPositionKey(novelId, chapterId)));
  return clampPercent(value);
}

function writeLocalPosition(novelId: string, chapterId: string, position: number): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(getPositionKey(novelId, chapterId), String(clampPercent(position)));
}

function getScrollPercent(): number {
  if (typeof window === "undefined") {
    return 0;
  }
  const scrollableHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (scrollableHeight <= 0) {
    return 100;
  }
  return clampPercent((window.scrollY / scrollableHeight) * 100);
}

function scrollToPercent(position: number): void {
  if (typeof window === "undefined") {
    return;
  }
  const scrollableHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (scrollableHeight <= 0) {
    return;
  }
  window.scrollTo({
    top: (scrollableHeight * clampPercent(position)) / 100,
    behavior: "auto",
  });
}

export default function ReadingPage() {
  const params = useParams<{ id: string; chapterId: string }>();
  const id = readRouteParam(params.id);
  const chapterId = readRouteParam(params.chapterId);
  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [settings, setSettings] = useState<ReaderSettings>(DEFAULT_READER_SETTINGS);
  const [settingsReady, setSettingsReady] = useState(false);
  const [readingProgress, setReadingProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const progressRef = useRef(0);
  const localSaveTimerRef = useRef<number | null>(null);
  const remoteSyncTimerRef = useRef<number | null>(null);
  const lastSyncedPositionRef = useRef<number | null>(null);

  const syncReadingProgress = useCallback(
    async (position: number) => {
      const normalizedPosition = clampPercent(position);
      if (!chapter || !getAccessToken() || lastSyncedPositionRef.current === normalizedPosition) {
        return;
      }

      try {
        await reportReadingHistory({
          novel_id: Number(id),
          chapter_id: Number(chapterId),
          reading_position: normalizedPosition,
        });
        lastSyncedPositionRef.current = normalizedPosition;
        setSyncError(null);
      } catch (reportError) {
        if (isUnauthorizedError(reportError)) {
          clearTokens();
          return;
        }
        setSyncError(getApiErrorMessage(reportError));
      }
    },
    [chapter, chapterId, id],
  );

  useEffect(() => {
    let active = true;
    window.setTimeout(() => {
      if (!active) {
        return;
      }
      setSettings(readStoredSettings());
      setSettingsReady(true);
    }, 0);

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!settingsReady || !canUseStorage()) {
      return;
    }
    window.localStorage.setItem(READER_SETTINGS_KEY, JSON.stringify(settings));
  }, [settings, settingsReady]);

  useEffect(() => {
    if (!chapterId) {
      return;
    }

    let active = true;
    lastSyncedPositionRef.current = null;
    progressRef.current = 0;

    void (async () => {
      await Promise.resolve();
      if (!active) {
        return;
      }
      setReadingProgress(0);
      setLoading(true);
      setError(null);
      setSyncError(null);
      try {
        const chapterDetail = await getChapterDetail(chapterId);
        if (!active) {
          return;
        }
        if (String(chapterDetail.novel.id) !== id) {
          setChapter(null);
          setError("章节与小说不匹配。");
          return;
        }
        setChapter(chapterDetail);
      } catch (loadError) {
        if (active) {
          setError(getApiErrorMessage(loadError));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [chapterId, id]);

  useEffect(() => {
    if (!chapter) {
      return;
    }

    let cancelled = false;

    async function restorePosition() {
      let position = readLocalPosition(id, chapterId);

      if (getAccessToken()) {
        try {
          const historyPage = await getReadingHistory({ page: 1, page_size: 50 });
          const historyItem = historyPage.results.find(
            (item) => String(item.novel.id) === id && String(item.chapter.id) === chapterId,
          );
          if (historyItem) {
            position = clampPercent(Number(historyItem.reading_position));
            writeLocalPosition(id, chapterId, position);
          }
        } catch (historyError) {
          if (isUnauthorizedError(historyError)) {
            clearTokens();
          }
        }
      }

      if (cancelled) {
        return;
      }

      progressRef.current = position;
      setReadingProgress(position);
      window.requestAnimationFrame(() => {
        window.setTimeout(() => {
          if (!cancelled) {
            scrollToPercent(position);
          }
        }, 50);
      });
    }

    void restorePosition();

    return () => {
      cancelled = true;
    };
  }, [chapter, chapterId, id]);

  useEffect(() => {
    if (!chapter) {
      return;
    }

    function saveCurrentPosition() {
      const position = getScrollPercent();
      progressRef.current = position;
      setReadingProgress(position);
      writeLocalPosition(id, chapterId, position);
      return position;
    }

    function scheduleRemoteSync() {
      if (!getAccessToken() || remoteSyncTimerRef.current) {
        return;
      }
      remoteSyncTimerRef.current = window.setTimeout(() => {
        remoteSyncTimerRef.current = null;
        void syncReadingProgress(progressRef.current);
      }, REMOTE_SYNC_DELAY);
    }

    function handleScroll() {
      if (localSaveTimerRef.current) {
        return;
      }
      localSaveTimerRef.current = window.setTimeout(() => {
        localSaveTimerRef.current = null;
        saveCurrentPosition();
        scheduleRemoteSync();
      }, LOCAL_SAVE_DELAY);
    }

    function handlePageHide() {
      saveCurrentPosition();
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("pagehide", handlePageHide);

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("pagehide", handlePageHide);
      if (localSaveTimerRef.current) {
        window.clearTimeout(localSaveTimerRef.current);
        localSaveTimerRef.current = null;
      }
      if (remoteSyncTimerRef.current) {
        window.clearTimeout(remoteSyncTimerRef.current);
        remoteSyncTimerRef.current = null;
      }
      saveCurrentPosition();
      void syncReadingProgress(progressRef.current);
    };
  }, [chapter, chapterId, id, syncReadingProgress]);

  function decreaseFontSize() {
    setSettings((current) => ({ ...current, fontSize: Math.max(14, current.fontSize - 1) }));
  }

  function increaseFontSize() {
    setSettings((current) => ({ ...current, fontSize: Math.min(28, current.fontSize + 1) }));
  }

  function toggleNightMode() {
    setSettings((current) => ({ ...current, nightMode: !current.nightMode }));
  }

  function toggleWidth() {
    setSettings((current) => ({ ...current, wideMode: !current.wideMode }));
  }

  if (loading) {
    return <section className="rounded-xl bg-white p-4 text-sm text-zinc-500 shadow-sm">正在加载章节...</section>;
  }

  if (error || !chapter) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        章节加载失败：{error || "章节不存在或暂不可访问。"}
      </section>
    );
  }

  const widthClassName = settings.wideMode
    ? "-mx-4 rounded-none p-3 sm:mx-auto sm:max-w-4xl sm:rounded-xl sm:p-4"
    : "mx-auto max-w-3xl rounded-xl p-5 sm:p-6";
  const articleClassName = settings.nightMode
    ? `${widthClassName} bg-zinc-950 text-zinc-100 shadow-sm`
    : `${widthClassName} bg-white text-zinc-900 shadow-sm`;
  const metaTextClassName = settings.nightMode ? "text-xs text-zinc-400" : "text-xs text-zinc-500";
  const contentTextClassName = settings.nightMode ? "mt-4 space-y-4 text-zinc-100" : "mt-4 space-y-4 text-zinc-800";
  const navLinkClassName = settings.nightMode
    ? "rounded-lg border border-zinc-700 px-3 py-2 text-center text-zinc-100"
    : "rounded-lg border border-zinc-300 px-3 py-2 text-center text-zinc-700";
  const disabledNavClassName = settings.nightMode
    ? "rounded-lg border border-zinc-800 px-3 py-2 text-center text-zinc-600"
    : "rounded-lg border border-zinc-200 px-3 py-2 text-center text-zinc-400";
  const chatWrapperClassName = settings.wideMode ? "mx-auto max-w-4xl" : "mx-auto max-w-3xl";

  return (
    <div className="space-y-4">
      <article className={articleClassName}>
        <p className={metaTextClassName}>{chapter.novel.title}</p>
        <h1 className="mt-1 text-xl font-semibold">{chapter.title}</h1>
        <p className={`mt-2 ${metaTextClassName}`}>
          {chapter.is_free ? "免费章节" : `付费章节 ${chapter.price}`} · {chapter.word_count} 字 · 已读 {readingProgress}%
        </p>
        {syncError ? <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">阅读历史同步失败：{syncError}</p> : null}

        <div className={contentTextClassName} style={{ fontSize: `${settings.fontSize}px`, lineHeight: 1.9 }}>
          {chapter.content.split(/\n{2,}/).map((paragraph, index) => (
            <p key={`${index}-${paragraph.slice(0, 24)}`}>{paragraph}</p>
          ))}
        </div>

        <div className="mt-8 grid grid-cols-3 gap-2 text-sm">
          {chapter.previous_chapter_id ? (
            <Link href={`/novels/${id}/chapters/${chapter.previous_chapter_id}`} className={navLinkClassName}>
              上一章
            </Link>
          ) : (
            <span className={disabledNavClassName} aria-disabled="true">
              上一章
            </span>
          )}
          <Link href={`/novels/${id}`} className={navLinkClassName}>
            目录
          </Link>
          {chapter.next_chapter_id ? (
            <Link href={`/novels/${id}/chapters/${chapter.next_chapter_id}`} className={navLinkClassName}>
              下一章
            </Link>
          ) : (
            <span className={disabledNavClassName} aria-disabled="true">
              下一章
            </span>
          )}
        </div>

        <ReadingToolbar
          fontSize={settings.fontSize}
          nightMode={settings.nightMode}
          wideMode={settings.wideMode}
          progress={readingProgress}
          onDecreaseFont={decreaseFontSize}
          onIncreaseFont={increaseFontSize}
          onToggleNightMode={toggleNightMode}
          onToggleWidth={toggleWidth}
        />
      </article>

      <div className={chatWrapperClassName}>
        <NovelAiChat
          novelTitle={chapter.novel.title}
          novelDescription={chapter.novel.description}
          authorName={chapter.novel.author.nickname || chapter.novel.author.username}
          categoryName={chapter.novel.category?.name}
          chapterTitle={chapter.title}
          chapterContent={chapter.content}
        />
      </div>
    </div>
  );
}
