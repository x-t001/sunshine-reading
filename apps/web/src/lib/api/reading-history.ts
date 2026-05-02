import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  GetReadingHistoryParams,
  ReadingHistoryItem,
  ReadingHistoryPage,
  ReportReadingHistoryPayload,
} from "@/types/reading-history";

function requireLogin(message = "请先登录后再同步阅读历史。"): void {
  if (!getAccessToken()) {
    throw new ApiRequestError(message, 401);
  }
}

export function getReadingHistory(params: GetReadingHistoryParams = {}): Promise<ReadingHistoryPage> {
  requireLogin("请先登录后再查看阅读历史。");
  return apiRequest<ReadingHistoryPage>(`/reading-history/${buildQueryString(params)}`);
}

export function reportReadingHistory(payload: ReportReadingHistoryPayload): Promise<ReadingHistoryItem> {
  requireLogin();
  return apiRequest<ReadingHistoryItem>("/reading-history/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
