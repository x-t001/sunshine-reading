import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  AddBookshelfPayload,
  BookshelfCheckResult,
  BookshelfItem,
  BookshelfPage,
  GetBookshelfParams,
} from "@/types/bookshelf";

function requireLogin(message = "请先登录后再操作书架。"): void {
  if (!getAccessToken()) {
    throw new ApiRequestError(message, 401);
  }
}

export function getBookshelf(params: GetBookshelfParams = {}): Promise<BookshelfPage> {
  requireLogin("请先登录后再查看书架。");
  return apiRequest<BookshelfPage>(`/bookshelf/${buildQueryString(params)}`);
}

export function addToBookshelf(novelId: number | string): Promise<BookshelfItem> {
  requireLogin();
  const payload: AddBookshelfPayload = { novel_id: Number(novelId) };
  return apiRequest<BookshelfItem>("/bookshelf/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeFromBookshelf(novelId: number | string): Promise<Record<string, never>> {
  requireLogin();
  return apiRequest<Record<string, never>>(`/bookshelf/${novelId}/`, {
    method: "DELETE",
  });
}

export function checkInBookshelf(novelId: number | string): Promise<BookshelfCheckResult> {
  requireLogin("请先登录后再检查书架状态。");
  return apiRequest<BookshelfCheckResult>(`/bookshelf/check/${buildQueryString({ novel_id: novelId })}`);
}
