export function formatWordCount(value: number): string {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}万字`;
  }

  return `${value}字`;
}

export function formatDateLabel(value: string): string {
  return new Date(value).toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  });
}
