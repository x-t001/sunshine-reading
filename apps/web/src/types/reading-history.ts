import type { PaginatedResponse } from "@/types/api";
import type { ChapterCatalogItem } from "@/types/chapter";
import type { NovelListItem } from "@/types/novel";

export type ReadingHistoryItem = {
  id: number;
  novel: NovelListItem;
  chapter: ChapterCatalogItem;
  reading_position: number;
  read_at: string;
};

export type GetReadingHistoryParams = {
  page?: number | string;
  page_size?: number | string;
};

export type ReadingHistoryPage = PaginatedResponse<ReadingHistoryItem>;

export type ReportReadingHistoryPayload = {
  novel_id: number;
  chapter_id: number;
  reading_position: number;
};
