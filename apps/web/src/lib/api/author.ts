import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  AuthorChapterDetail,
  AuthorChapterPage,
  AuthorChapterSubmitResult,
  AuthorNovelDetail,
  AuthorNovelPage,
  AuthorNovelSubmitResult,
  CreateAuthorChapterPayload,
  CreateAuthorNovelPayload,
  GetAuthorChaptersParams,
  GetAuthorNovelsParams,
  UpdateAuthorChapterPayload,
  UpdateAuthorNovelPayload,
} from "@/types/author";

function requireLogin(): void {
  if (!getAccessToken()) {
    throw new ApiRequestError("请先登录后再访问作者中心。", 401);
  }
}

export function getAuthorNovels(params: GetAuthorNovelsParams = {}): Promise<AuthorNovelPage> {
  requireLogin();
  return apiRequest<AuthorNovelPage>(`/author/novels/${buildQueryString(params)}`);
}

export function createAuthorNovel(payload: CreateAuthorNovelPayload): Promise<AuthorNovelDetail> {
  requireLogin();
  return apiRequest<AuthorNovelDetail>("/author/novels/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAuthorNovelDetail(id: number | string): Promise<AuthorNovelDetail> {
  requireLogin();
  return apiRequest<AuthorNovelDetail>(`/author/novels/${id}/`);
}

export function updateAuthorNovel(id: number | string, payload: UpdateAuthorNovelPayload): Promise<AuthorNovelDetail> {
  requireLogin();
  return apiRequest<AuthorNovelDetail>(`/author/novels/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function submitAuthorNovel(id: number | string): Promise<AuthorNovelSubmitResult> {
  requireLogin();
  return apiRequest<AuthorNovelSubmitResult>(`/author/novels/${id}/submit/`, {
    method: "POST",
  });
}

export function getAuthorNovelChapters(
  novelId: number | string,
  params: GetAuthorChaptersParams = {},
): Promise<AuthorChapterPage> {
  requireLogin();
  return apiRequest<AuthorChapterPage>(`/author/novels/${novelId}/chapters/${buildQueryString(params)}`);
}

export function createAuthorChapter(
  novelId: number | string,
  payload: CreateAuthorChapterPayload,
): Promise<AuthorChapterDetail> {
  requireLogin();
  return apiRequest<AuthorChapterDetail>(`/author/novels/${novelId}/chapters/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAuthorChapterDetail(id: number | string): Promise<AuthorChapterDetail> {
  requireLogin();
  return apiRequest<AuthorChapterDetail>(`/author/chapters/${id}/`);
}

export function updateAuthorChapter(
  id: number | string,
  payload: UpdateAuthorChapterPayload,
): Promise<AuthorChapterDetail> {
  requireLogin();
  return apiRequest<AuthorChapterDetail>(`/author/chapters/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function submitAuthorChapter(id: number | string): Promise<AuthorChapterSubmitResult> {
  requireLogin();
  return apiRequest<AuthorChapterSubmitResult>(`/author/chapters/${id}/submit/`, {
    method: "POST",
  });
}
