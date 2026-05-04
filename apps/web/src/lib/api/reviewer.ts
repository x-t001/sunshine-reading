import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  AuditActionResult,
  AuditLogPage,
  GetAuditLogsParams,
  GetPendingChaptersParams,
  GetPendingNovelsParams,
  PendingChapterPage,
  PendingNovelPage,
  RejectPayload,
  ReviewerChapterDetail,
  ReviewerNovelDetail,
} from "@/types/reviewer";

function requireLogin(): void {
  if (!getAccessToken()) {
    throw new ApiRequestError("请先登录后再访问审核中心。", 401);
  }
}

export function getPendingNovels(params: GetPendingNovelsParams = {}): Promise<PendingNovelPage> {
  requireLogin();
  return apiRequest<PendingNovelPage>(`/reviewer/novels/pending/${buildQueryString(params)}`);
}

export function getReviewingNovels(params: GetPendingNovelsParams = {}): Promise<PendingNovelPage> {
  requireLogin();
  return apiRequest<PendingNovelPage>(`/reviewer/novels/reviewing/${buildQueryString(params)}`);
}

export function getReviewerNovelDetail(id: number | string): Promise<ReviewerNovelDetail> {
  requireLogin();
  return apiRequest<ReviewerNovelDetail>(`/reviewer/novels/${id}/`);
}

export function claimNovel(id: number | string): Promise<AuditActionResult> {
  requireLogin();
  return apiRequest<AuditActionResult>(`/reviewer/novels/${id}/claim/`, {
    method: "POST",
  });
}

export function approveNovel(id: number | string): Promise<AuditActionResult> {
  requireLogin();
  return apiRequest<AuditActionResult>(`/reviewer/novels/${id}/approve/`, {
    method: "POST",
  });
}

export function rejectNovel(id: number | string, payload: RejectPayload): Promise<AuditActionResult> {
  requireLogin();
  return apiRequest<AuditActionResult>(`/reviewer/novels/${id}/reject/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getPendingChapters(params: GetPendingChaptersParams = {}): Promise<PendingChapterPage> {
  requireLogin();
  return apiRequest<PendingChapterPage>(`/reviewer/chapters/pending/${buildQueryString(params)}`);
}

export function getReviewingChapters(params: GetPendingChaptersParams = {}): Promise<PendingChapterPage> {
  requireLogin();
  return apiRequest<PendingChapterPage>(`/reviewer/chapters/reviewing/${buildQueryString(params)}`);
}

export function getReviewerChapterDetail(id: number | string): Promise<ReviewerChapterDetail> {
  requireLogin();
  return apiRequest<ReviewerChapterDetail>(`/reviewer/chapters/${id}/`);
}

export function claimChapter(id: number | string): Promise<AuditActionResult> {
  requireLogin();
  return apiRequest<AuditActionResult>(`/reviewer/chapters/${id}/claim/`, {
    method: "POST",
  });
}

export function approveChapter(id: number | string): Promise<AuditActionResult> {
  requireLogin();
  return apiRequest<AuditActionResult>(`/reviewer/chapters/${id}/approve/`, {
    method: "POST",
  });
}

export function rejectChapter(id: number | string, payload: RejectPayload): Promise<AuditActionResult> {
  requireLogin();
  return apiRequest<AuditActionResult>(`/reviewer/chapters/${id}/reject/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAuditLogs(params: GetAuditLogsParams = {}): Promise<AuditLogPage> {
  requireLogin();
  return apiRequest<AuditLogPage>(`/reviewer/audit-logs/${buildQueryString(params)}`);
}
