import { apiRequest, buildQueryString } from "@/lib/api/request";
import type { PaginatedResponse } from "@/types/api";
import type { ChapterCatalogItem, ChapterDetail } from "@/types/chapter";

export function getNovelChapters(
  novelId: number | string,
  params: { page?: number | string; page_size?: number | string } = {},
): Promise<PaginatedResponse<ChapterCatalogItem>> {
  return apiRequest<PaginatedResponse<ChapterCatalogItem>>(`/novels/${novelId}/chapters/${buildQueryString(params)}`, {
    auth: false,
  });
}

export function getChapterDetail(id: number | string): Promise<ChapterDetail> {
  return apiRequest<ChapterDetail>(`/chapters/${id}/`, {
    auth: false,
  });
}
