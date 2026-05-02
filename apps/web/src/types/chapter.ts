import type { NovelListItem } from "@/types/novel";

export type ChapterCatalogItem = {
  id: number;
  title: string;
  chapter_number: number;
  word_count: number;
  is_free: boolean;
  published_at: string | null;
};

export type ChapterDetail = ChapterCatalogItem & {
  content: string;
  price: string;
  novel: NovelListItem;
  previous_chapter_id: number | null;
  next_chapter_id: number | null;
};
