"use client";

import { useState } from "react";

export function ReadingToolbar() {
  const [fontSize, setFontSize] = useState(18);
  const [night, setNight] = useState(false);

  return (
    <div className="sticky bottom-16 z-10 mt-6 rounded-xl border border-zinc-200 bg-white p-3 shadow-sm md:bottom-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button
          className="rounded-md border px-3 py-1 text-zinc-700"
          onClick={() => setFontSize((prev) => Math.max(14, prev - 1))}
          type="button"
        >
          字体-
        </button>
        <span className="text-zinc-600">{fontSize}px</span>
        <button
          className="rounded-md border px-3 py-1 text-zinc-700"
          onClick={() => setFontSize((prev) => Math.min(28, prev + 1))}
          type="button"
        >
          字体+
        </button>
        <button
          className="rounded-md border px-3 py-1 text-zinc-700"
          onClick={() => setNight((prev) => !prev)}
          type="button"
        >
          {night ? "日间模式" : "夜间模式"}
        </button>
        <span className="ml-auto rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-600">示例控件（仅 mock）</span>
      </div>
    </div>
  );
}
