"use client";

type ReadingToolbarProps = {
  fontSize: number;
  nightMode: boolean;
  wideMode: boolean;
  progress: number;
  onDecreaseFont: () => void;
  onIncreaseFont: () => void;
  onToggleNightMode: () => void;
  onToggleWidth: () => void;
};

function clampProgress(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function ReadingToolbar({
  fontSize,
  nightMode,
  wideMode,
  progress,
  onDecreaseFont,
  onIncreaseFont,
  onToggleNightMode,
  onToggleWidth,
}: ReadingToolbarProps) {
  const containerClassName = nightMode
    ? "sticky bottom-16 z-10 mt-6 rounded-xl border border-zinc-700 bg-zinc-900 p-3 shadow-sm md:bottom-4"
    : "sticky bottom-16 z-10 mt-6 rounded-xl border border-zinc-200 bg-white p-3 shadow-sm md:bottom-4";
  const buttonClassName = nightMode
    ? "rounded-md border border-zinc-700 px-3 py-1 text-zinc-100"
    : "rounded-md border border-zinc-200 px-3 py-1 text-zinc-700";
  const mutedTextClassName = nightMode ? "text-zinc-300" : "text-zinc-600";
  const progressClassName = nightMode
    ? "ml-auto rounded-md bg-zinc-800 px-2 py-1 text-xs text-zinc-200"
    : "ml-auto rounded-md bg-zinc-100 px-2 py-1 text-xs text-zinc-600";

  return (
    <div className={containerClassName}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button className={buttonClassName} onClick={onDecreaseFont} type="button" aria-label="减小字体">
          字体-
        </button>
        <span className={mutedTextClassName}>{fontSize}px</span>
        <button className={buttonClassName} onClick={onIncreaseFont} type="button" aria-label="增大字体">
          字体+
        </button>
        <button className={buttonClassName} onClick={onToggleNightMode} type="button">
          {nightMode ? "日间模式" : "夜间模式"}
        </button>
        <button className={buttonClassName} onClick={onToggleWidth} type="button">
          {wideMode ? "窄版阅读" : "宽版阅读"}
        </button>
        <span className={progressClassName}>已读 {clampProgress(progress)}%</span>
      </div>
    </div>
  );
}
