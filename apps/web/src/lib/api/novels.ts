import { apiRequest, buildQueryString } from "@/lib/api/request";
import type { PaginatedResponse } from "@/types/api";
import type { NovelDetail, NovelListItem, NovelStatus } from "@/types/novel";

export type GetNovelsParams = {
  page?: number | string;
  page_size?: number | string;
  category?: number | string;
  status?: NovelStatus | string;
  ordering?: "latest" | "views" | "collects" | "rating" | string;
  keyword?: string;
};

export function getNovels(params: GetNovelsParams = {}): Promise<PaginatedResponse<NovelListItem>> {
  return apiRequest<PaginatedResponse<NovelListItem>>(`/novels/${buildQueryString(params)}`, {
    auth: false,
  });
}

export function getNovelDetail(id: number | string): Promise<NovelDetail> {
  return apiRequest<NovelDetail>(`/novels/${id}/`, {
    auth: false,
  });
}
