"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { sendAiChatMessage } from "@/lib/api/ai";
import { getApiErrorMessage } from "@/lib/api/request";
import type { AiChatContext, AiChatMessage } from "@/types/ai";

type NovelAiChatProps = {
  novelTitle: string;
  novelDescription?: string;
  authorName?: string;
  categoryName?: string;
  chapterTitle?: string;
  chapterContent?: string;
};

const DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions";
const DEFAULT_MODEL = "gpt-4o-mini";
const CONFIG_STORAGE_KEY = "sunshine-reading:ai-chat-config";
const MAX_CONTEXT_MESSAGES = 10;

const QUICK_PROMPTS = [
  "请总结当前内容。",
  "有哪些重要人物或设定？",
  "我应该重点关注哪些线索？",
];

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function trimText(value: string | undefined, limit: number): string {
  if (!value) {
    return "";
  }
  const text = value.trim();
  if (text.length <= limit) {
    return text;
  }
  return `${text.slice(0, limit)}...`;
}

function readStoredConfig() {
  if (!canUseStorage()) {
    return { apiUrl: DEFAULT_API_URL, model: DEFAULT_MODEL };
  }

  try {
    const raw = window.localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) {
      return { apiUrl: DEFAULT_API_URL, model: DEFAULT_MODEL };
    }
    const parsed = JSON.parse(raw) as Partial<{ apiUrl: string; model: string }>;
    return {
      apiUrl: parsed.apiUrl || DEFAULT_API_URL,
      model: parsed.model || DEFAULT_MODEL,
    };
  } catch {
    return { apiUrl: DEFAULT_API_URL, model: DEFAULT_MODEL };
  }
}

export function NovelAiChat({
  novelTitle,
  novelDescription,
  authorName,
  categoryName,
  chapterTitle,
  chapterContent,
}: NovelAiChatProps) {
  const [open, setOpen] = useState(false);
  const [configReady, setConfigReady] = useState(false);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [apiKey, setApiKey] = useState("");
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<AiChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const context = useMemo<AiChatContext>(
    () => ({
      novel_title: novelTitle,
      novel_description: trimText(novelDescription, 1600),
      author_name: authorName,
      category_name: categoryName,
      chapter_title: chapterTitle,
      chapter_excerpt: trimText(chapterContent, 3500),
    }),
    [authorName, categoryName, chapterContent, chapterTitle, novelDescription, novelTitle],
  );

  useEffect(() => {
    let active = true;
    window.setTimeout(() => {
      if (!active) {
        return;
      }
      const storedConfig = readStoredConfig();
      setApiUrl(storedConfig.apiUrl);
      setModel(storedConfig.model);
      setConfigReady(true);
    }, 0);

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!configReady || !canUseStorage()) {
      return;
    }
    window.localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify({ apiUrl, model }));
  }, [apiUrl, configReady, model]);

  async function submitMessage(content: string) {
    const normalizedContent = content.trim();
    if (!normalizedContent || loading) {
      return;
    }
    if (!apiKey.trim()) {
      setError("请输入 API Key。");
      return;
    }
    if (!model.trim()) {
      setError("请输入模型名称。");
      return;
    }

    const nextMessages: AiChatMessage[] = [...messages, { role: "user", content: normalizedContent }];
    setMessages(nextMessages);
    setDraft("");
    setLoading(true);
    setError(null);

    try {
      const result = await sendAiChatMessage({
        api_key: apiKey.trim(),
        api_url: apiUrl.trim(),
        model: model.trim(),
        messages: nextMessages.slice(-MAX_CONTEXT_MESSAGES),
        context,
      });
      setMessages([...nextMessages, { role: "assistant", content: result.answer }]);
    } catch (sendError) {
      setError(getApiErrorMessage(sendError));
      setMessages(messages);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(draft);
  }

  return (
    <section className="rounded-xl bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">智能问答</h2>
          <p className="mt-1 text-xs text-zinc-500">围绕当前小说内容提问。</p>
        </div>
        <button
          type="button"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
          onClick={() => setOpen((current) => !current)}
        >
          {open ? "收起窗口" : "打开聊天"}
        </button>
      </div>

      {open ? (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_180px]">
            <label className="block text-sm">
              <span className="mb-1 block text-zinc-700">API 地址</span>
              <input
                value={apiUrl}
                onChange={(event) => setApiUrl(event.target.value)}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                placeholder={DEFAULT_API_URL}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-zinc-700">模型</span>
              <input
                value={model}
                onChange={(event) => setModel(event.target.value)}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                placeholder={DEFAULT_MODEL}
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="mb-1 block text-zinc-700">API Key</span>
            <input
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              placeholder="sk-..."
              type="password"
              autoComplete="off"
            />
          </label>

          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-700 disabled:text-zinc-400"
                disabled={loading}
                onClick={() => void submitMessage(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="max-h-80 space-y-3 overflow-y-auto rounded-lg border border-zinc-200 bg-zinc-50 p-3">
            {messages.length === 0 ? (
              <p className="text-sm text-zinc-500">暂无对话。</p>
            ) : (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}-${message.content.slice(0, 16)}`}
                  className={
                    message.role === "user"
                      ? "ml-auto max-w-[88%] rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white"
                      : "max-w-[88%] whitespace-pre-wrap rounded-lg bg-white px-3 py-2 text-sm leading-6 text-zinc-700 shadow-sm"
                  }
                >
                  {message.content}
                </div>
              ))
            )}
            {loading ? <p className="text-sm text-zinc-500">正在生成回答...</p> : null}
          </div>

          {error ? <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}

          <form className="flex flex-col gap-2 sm:flex-row" onSubmit={handleSubmit}>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              className="min-h-20 flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              maxLength={1000}
              placeholder="输入你的问题..."
            />
            <button
              type="submit"
              disabled={loading || !draft.trim()}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:bg-zinc-300 sm:self-end"
            >
              发送
            </button>
          </form>
        </div>
      ) : null}
    </section>
  );
}
