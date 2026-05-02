import type { PaginatedResponse } from "@/types/api";
import type { ChapterCatalogItem } from "@/types/chapter";
import type { NovelListItem } from "@/types/novel";

export type BookshelfItem = {
  id: number;
  novel: NovelListItem;
  last_read_chapter: ChapterCatalogItem | null;
  reading_progress: string;
  joined_at: string;
  last_read_at: string | null;
};

export type GetBookshelfParams = {
  page?: number | string;
  page_size?: number | string;
};

export type BookshelfPage = PaginatedResponse<BookshelfItem>;

export type AddBookshelfPayload = {
  novel_id: number;
};

export type BookshelfCheckResult = {
  in_bookshelf: boolean;
};
