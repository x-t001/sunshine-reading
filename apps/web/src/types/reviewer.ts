import type { PaginatedResponse } from "@/types/api";
import type { NovelAuthor, NovelCategory, NovelStatus } from "@/types/novel";

export type ReviewAuditStatus = "draft" | "pending" | "reviewing" | "approved" | "rejected";
export type ReviewerChapterStatus = "draft" | "published" | "hidden";
export type AuditContentType = "novel" | "chapter";
export type AuditAction = "submit" | "claim" | "approve" | "reject";

export type PendingNovel = {
  id: number;
  title: string;
  cover: string;
  author: NovelAuthor;
  category: NovelCategory | null;
  reviewer: NovelAuthor | null;
  status: NovelStatus;
  audit_status: ReviewAuditStatus;
  reviewed_at: string | null;
  word_count: number;
  view_count: number;
  collect_count: number;
  comment_count: number;
  rating_score: string;
  rating_count: number;
  latest_chapter_title: string;
  latest_chapter_updated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ReviewerNovelDetail = PendingNovel & {
  description: string;
  is_featured: boolean;
  chapter_count: number;
};

export type ReviewerChapterNovel = {
  id: number;
  title: string;
  author: NovelAuthor;
};

export type PendingChapter = {
  id: number;
  title: string;
  chapter_number: number;
  word_count: number;
  is_free: boolean;
  price: string;
  status: ReviewerChapterStatus;
  audit_status: ReviewAuditStatus;
  reviewer: NovelAuthor | null;
  reviewed_at: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  novel: ReviewerChapterNovel;
};

export type ReviewerChapterDetail = PendingChapter & {
  content: string;
};

export type AuditLog = {
  id: number;
  content_type: AuditContentType;
  object_id: number;
  reviewer: NovelAuthor | null;
  action: AuditAction;
  from_status: string;
  to_status: string;
  reason: string;
  created_at: string;
};

export type RejectPayload = {
  reason: string;
};

export type AuditActionResult = {
  id: number;
  title: string;
  status?: NovelStatus | ReviewerChapterStatus;
  audit_status: ReviewAuditStatus;
  reviewer?: NovelAuthor | null;
  reviewed_at?: string | null;
  published_at?: string | null;
  updated_at: string;
};

export type GetPendingNovelsParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
};

export type GetPendingChaptersParams = GetPendingNovelsParams & {
  novel_id?: number | string;
};

export type GetAuditLogsParams = {
  page?: number | string;
  page_size?: number | string;
  content_type?: AuditContentType | "";
  action?: AuditAction | "";
};

export type PendingNovelPage = PaginatedResponse<PendingNovel>;
export type PendingChapterPage = PaginatedResponse<PendingChapter>;
export type AuditLogPage = PaginatedResponse<AuditLog>;
