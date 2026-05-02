import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  CreateNovelCommentPayload,
  GetNovelCommentsParams,
  NovelComment,
  NovelCommentPage,
} from "@/types/comment";

function requireLogin(message = "请先登录后再发表评论。"): void {
  if (!getAccessToken()) {
    throw new ApiRequestError(message, 401);
  }
}

export function getNovelComments(
  novelId: number | string,
  params: GetNovelCommentsParams = {},
): Promise<NovelCommentPage> {
  return apiRequest<NovelCommentPage>(`/novels/${novelId}/comments/${buildQueryString(params)}`, {
    auth: false,
  });
}

export function createNovelComment(
  novelId: number | string,
  payload: CreateNovelCommentPayload,
): Promise<NovelComment> {
  requireLogin();
  return apiRequest<NovelComment>(`/novels/${novelId}/comments/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteComment(commentId: number | string): Promise<Record<string, never>> {
  requireLogin("请先登录后再删除评论。");
  return apiRequest<Record<string, never>>(`/comments/${commentId}/`, {
    method: "DELETE",
  });
}
