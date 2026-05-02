import type { PaginatedResponse } from "@/types/api";

export type CommentUser = {
  id: number;
  username: string;
  nickname: string;
  avatar: string;
};

export type CommentStatus = "normal" | "hidden" | "deleted";

export type NovelCommentBase = {
  id: number;
  user: CommentUser;
  novel_id: number;
  chapter_id: number | null;
  parent_id: number | null;
  parent?: number | null;
  chapter?: number | null;
  content: string;
  status?: CommentStatus;
  like_count: number;
  created_at: string;
  updated_at: string;
};

export type NovelCommentReply = NovelCommentBase;

export type NovelComment = NovelCommentBase & {
  replies: NovelCommentReply[];
};

export type GetNovelCommentsParams = {
  page?: number | string;
  page_size?: number | string;
};

export type NovelCommentPage = PaginatedResponse<NovelComment>;

export type CreateNovelCommentPayload = {
  content: string;
  parent_id?: number | null;
  chapter_id?: number | null;
};
