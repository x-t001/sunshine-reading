export type Category = {
  id: string;
  name: string;
  slug: string;
};

export type NovelAuthor = {
  id: number;
  username: string;
  nickname: string;
};

export type NovelCategory = {
  id: number;
  name: string;
  slug: string;
};

export type NovelStatus = "serializing" | "completed" | "paused" | "removed";
export type NovelAuditStatus = "draft" | "pending" | "approved" | "rejected";

export type NovelListItem = {
  id: number;
  title: string;
  author: NovelAuthor;
  category: NovelCategory | null;
  cover: string;
  description: string;
  status: NovelStatus;
  word_count: number;
  view_count: number;
  collect_count: number;
  comment_count: number;
  rating_score: string;
  latest_chapter_title: string;
  latest_chapter_updated_at: string | null;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
};

export type NovelDetail = NovelListItem & {
  audit_status: NovelAuditStatus;
};

export type ChapterPreview = {
  id: string;
  novelId: string;
  chapterNo: number;
  title: string;
  updatedAt: string;
};

export type Novel = {
  id: string;
  title: string;
  author: string;
  categoryId: string;
  cover: string;
  summary: string;
  status: "ongoing" | "completed";
  wordCount: number;
  updatedAt: string;
  recommend: boolean;
};

export type RankingItem = {
  rank: number;
  novelId: string;
  score: number;
  trend: "up" | "down" | "same";
};

export type ChapterContent = {
  chapterId: string;
  novelId: string;
  title: string;
  content: string;
};
