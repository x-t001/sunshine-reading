const DEFAULT_NOVEL_COVER = "/covers/default-novel.svg";

export function getNovelCoverUrl(cover?: string | null): string {
  const value = cover?.trim();
  if (!value) {
    return DEFAULT_NOVEL_COVER;
  }

  if (value.startsWith("/") && !value.startsWith("//")) {
    return value;
  }

  return DEFAULT_NOVEL_COVER;
}
