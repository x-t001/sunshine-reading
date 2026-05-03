import { ApiRequestError, apiRequest } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type { RatingSummary, SubmitRatingPayload } from "@/types/rating";

function requireLogin(message = "请先登录后再评分。"): void {
  if (!getAccessToken()) {
    throw new ApiRequestError(message, 401);
  }
}

export async function getNovelRatingSummary(novelId: number | string): Promise<RatingSummary> {
  try {
    return await apiRequest<RatingSummary>(`/novels/${novelId}/ratings/summary/`, {
      auth: Boolean(getAccessToken()),
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 401) {
      return apiRequest<RatingSummary>(`/novels/${novelId}/ratings/summary/`, {
        auth: false,
      });
    }
    throw error;
  }
}

export function submitNovelRating(
  novelId: number | string,
  payload: SubmitRatingPayload,
): Promise<RatingSummary> {
  requireLogin();
  return apiRequest<RatingSummary>(`/novels/${novelId}/ratings/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteNovelRating(novelId: number | string): Promise<RatingSummary> {
  requireLogin("请先登录后再删除评分。");
  return apiRequest<RatingSummary>(`/novels/${novelId}/ratings/`, {
    method: "DELETE",
  });
}
