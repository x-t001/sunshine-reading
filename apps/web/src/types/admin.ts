import type { PaginatedResponse } from "@/types/api";
import type { NovelAuthor, NovelCategory } from "@/types/novel";

export type AdminUserRole = "reader" | "author" | "reviewer" | "admin";
export type AdminNovelStatus = "serializing" | "completed" | "paused" | "removed";
export type AdminAuditStatus = "draft" | "pending" | "reviewing" | "approved" | "rejected";
export type AdminChapterStatus = "draft" | "published" | "hidden";
export type AdminCommentStatus = "normal" | "hidden" | "deleted";

export type AdminUser = {
  id: number;
  username: string;
  nickname: string;
  email: string;
  phone: string;
  role: AdminUserRole;
  is_banned: boolean;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
};

export type AdminUserDetail = AdminUser & {
  avatar: string;
  bio: string;
  novel_count: number;
  comment_count: number;
  bookshelf_count: number;
  rating_count: number;
};

export type GetAdminUsersParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  role?: AdminUserRole | "";
  is_banned?: boolean | "";
};

export type UpdateUserRolePayload = {
  role: AdminUserRole;
};

export type BanUserPayload = {
  reason?: string;
};

export type AdminUserPage = PaginatedResponse<AdminUser>;

export type AdminPaginatedResponse<T> = PaginatedResponse<T>;

export type AdminNovel = {
  id: number;
  title: string;
  author: NovelAuthor;
  author_id: number;
  author_username: string;
  author_nickname: string;
  category: NovelCategory | null;
  category_id: number | null;
  status: AdminNovelStatus;
  audit_status: AdminAuditStatus;
  word_count: number;
  view_count: number;
  collect_count: number;
  comment_count: number;
  rating_score: string;
  rating_count: number;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
  latest_chapter_title: string;
  latest_chapter_updated_at: string | null;
};

export type AdminNovelDetail = AdminNovel & {
  cover: string;
  description: string;
  reviewer: NovelAuthor | null;
  reviewed_at: string | null;
  chapter_count: number;
};

export type AdminNovelListParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  category?: string;
  status?: AdminNovelStatus | "";
  audit_status?: AdminAuditStatus | "";
  author_id?: number | string;
};

export type UpdateNovelStatusPayload = {
  status: AdminNovelStatus;
};

export type UpdateNovelFeaturedPayload = {
  is_featured: boolean;
};

export type AdminChapterNovel = {
  id: number;
  title: string;
  author: NovelAuthor;
};

export type AdminChapter = {
  id: number;
  novel: AdminChapterNovel;
  novel_id: number;
  novel_title: string;
  author_id: number;
  author_username: string;
  title: string;
  chapter_number: number;
  word_count: number;
  is_free: boolean;
  price: string;
  status: AdminChapterStatus;
  audit_status: AdminAuditStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminChapterDetail = AdminChapter & {
  content: string;
  reviewer: NovelAuthor | null;
  reviewed_at: string | null;
};

export type AdminChapterListParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  novel_id?: number | string;
  author_id?: number | string;
  status?: AdminChapterStatus | "";
  audit_status?: AdminAuditStatus | "";
};

export type UpdateChapterStatusPayload = {
  status: AdminChapterStatus;
};

export type AdminCommentUser = {
  id: number;
  username: string;
  nickname: string;
  avatar: string;
};

export type AdminCommentNovel = {
  id: number;
  title: string;
};

export type AdminCommentChapter = {
  id: number;
  title: string;
};

export type AdminComment = {
  id: number;
  user: AdminCommentUser;
  user_id: number;
  username: string;
  nickname: string;
  novel: AdminCommentNovel;
  novel_id: number;
  novel_title: string;
  chapter: AdminCommentChapter | null;
  chapter_id: number | null;
  chapter_title: string | null;
  parent: number | null;
  content: string;
  like_count: number;
  status: AdminCommentStatus;
  created_at: string;
  updated_at: string;
};

export type AdminCommentDetail = AdminComment;

export type AdminCommentListParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  user_id?: number | string;
  novel_id?: number | string;
  chapter_id?: number | string;
  status?: AdminCommentStatus | "";
};

export type UpdateCommentStatusPayload = {
  status: AdminCommentStatus;
};

export type AdminNovelPage = AdminPaginatedResponse<AdminNovel>;
export type AdminChapterPage = AdminPaginatedResponse<AdminChapter>;
export type AdminCommentPage = AdminPaginatedResponse<AdminComment>;
