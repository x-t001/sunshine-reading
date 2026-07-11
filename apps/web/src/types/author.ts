import type { PaginatedResponse } from "@/types/api";
import type { CategorySummary } from "@/types/category";
import type { NovelAuditStatus, NovelStatus } from "@/types/novel";

export type AuthorChapterStatus = "draft" | "published" | "hidden";
export type AuthorChapterAuditStatus = "pending" | "reviewing" | "approved" | "rejected";

export type AuthorAuditAction = "submit" | "claim" | "approve" | "reject";

export type AuthorAuditLog = {
  id: number;
  content_type: "novel" | "chapter";
  object_id: number;
  reviewer: {
    id: number;
    username: string;
    nickname: string;
  } | null;
  action: AuthorAuditAction;
  from_status: string;
  to_status: string;
  reason: string;
  created_at: string;
};

export type AuthorNovel = {
  id: number;
  title: string;
  cover: string;
  category: CategorySummary | null;
  status: NovelStatus;
  audit_status: NovelAuditStatus;
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

export type AuthorNovelDetail = AuthorNovel & {
  author: {
    id: number;
    username: string;
    nickname: string;
  };
  description: string;
  chapter_count: number;
  audit_logs: AuthorAuditLog[];
};

export type CreateAuthorNovelPayload = {
  title: string;
  category_id: number;
  cover?: string;
  description: string;
  status: NovelStatus;
};

export type UpdateAuthorNovelPayload = Partial<CreateAuthorNovelPayload>;

export type AuthorNovelSubmitResult = {
  id: number;
  audit_status: NovelAuditStatus;
};

export type AuthorChapter = {
  id: number;
  title: string;
  chapter_number: number;
  word_count: number;
  is_free: boolean;
  price: string;
  status: AuthorChapterStatus;
  audit_status: AuthorChapterAuditStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AuthorChapterDetail = AuthorChapter & {
  novel_id: number;
  novel_title: string;
  content: string;
  audit_logs: AuthorAuditLog[];
};

export type CreateAuthorChapterPayload = {
  title: string;
  chapter_number: number;
  content: string;
  is_free: boolean;
  price: string;
};

export type UpdateAuthorChapterPayload = Partial<CreateAuthorChapterPayload> & {
  status?: AuthorChapterStatus;
};

export type AuthorChapterSubmitResult = {
  id: number;
  status: AuthorChapterStatus;
  audit_status: AuthorChapterAuditStatus;
};

export type GetAuthorNovelsParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  status?: NovelStatus | string;
  audit_status?: NovelAuditStatus | string;
};

export type GetAuthorChaptersParams = {
  page?: number | string;
  page_size?: number | string;
};

export type AuthorNovelPage = PaginatedResponse<AuthorNovel>;
export type AuthorChapterPage = PaginatedResponse<AuthorChapter>;
