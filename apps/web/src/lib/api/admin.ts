import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  AdminCategory,
  AdminCategoryListParams,
  AdminCategoryPage,
  AdminChapter,
  AdminChapterDetail,
  AdminChapterListParams,
  AdminChapterPage,
  AdminComment,
  AdminCommentDetail,
  AdminCommentListParams,
  AdminCommentPage,
  AdminNovel,
  AdminNovelDetail,
  AdminNovelListParams,
  AdminNovelPage,
  AdminRankingItem,
  AdminRankingItemListParams,
  AdminRankingItemPage,
  AdminRankingType,
  AdminRankingTypeListParams,
  AdminRankingTypePage,
  AdminUser,
  AdminUserDetail,
  AdminUserPage,
  AdminUserRole,
  BanUserPayload,
  CreateAdminCategoryPayload,
  CreateAdminRankingItemPayload,
  CreateAdminRankingTypePayload,
  GetAdminUsersParams,
  UpdateAdminCategoryPayload,
  UpdateAdminRankingItemPayload,
  UpdateAdminRankingTypePayload,
  UpdateCategoryStatusPayload,
  UpdateChapterStatusPayload,
  UpdateCommentStatusPayload,
  UpdateNovelFeaturedPayload,
  UpdateNovelStatusPayload,
  UpdateRankingTypeStatusPayload,
} from "@/types/admin";

function requireLogin(): void {
  if (!getAccessToken()) {
    throw new ApiRequestError("请先登录后再访问运营后台。", 401);
  }
}

export function getAdminUsers(params: GetAdminUsersParams = {}): Promise<AdminUserPage> {
  requireLogin();
  return apiRequest<AdminUserPage>(`/admin/users/${buildQueryString(params)}`);
}

export function getAdminUserDetail(id: number | string): Promise<AdminUserDetail> {
  requireLogin();
  return apiRequest<AdminUserDetail>(`/admin/users/${id}/`);
}

export function updateUserRole(id: number | string, role: AdminUserRole): Promise<AdminUser> {
  requireLogin();
  return apiRequest<AdminUser>(`/admin/users/${id}/role/`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function banUser(id: number | string, payload: BanUserPayload = {}): Promise<AdminUser> {
  requireLogin();
  return apiRequest<AdminUser>(`/admin/users/${id}/ban/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function unbanUser(id: number | string): Promise<AdminUser> {
  requireLogin();
  return apiRequest<AdminUser>(`/admin/users/${id}/unban/`, {
    method: "POST",
  });
}

export function getAdminCategories(params: AdminCategoryListParams = {}): Promise<AdminCategoryPage> {
  requireLogin();
  return apiRequest<AdminCategoryPage>(`/admin/categories/${buildQueryString(params)}`);
}

export function createAdminCategory(payload: CreateAdminCategoryPayload): Promise<AdminCategory> {
  requireLogin();
  return apiRequest<AdminCategory>("/admin/categories/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminCategoryDetail(id: number | string): Promise<AdminCategory> {
  requireLogin();
  return apiRequest<AdminCategory>(`/admin/categories/${id}/`);
}

export function updateAdminCategory(id: number | string, payload: UpdateAdminCategoryPayload): Promise<AdminCategory> {
  requireLogin();
  return apiRequest<AdminCategory>(`/admin/categories/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function updateAdminCategoryStatus(
  id: number | string,
  payload: UpdateCategoryStatusPayload,
): Promise<AdminCategory> {
  requireLogin();
  return apiRequest<AdminCategory>(`/admin/categories/${id}/status/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAdminRankingTypes(params: AdminRankingTypeListParams = {}): Promise<AdminRankingTypePage> {
  requireLogin();
  return apiRequest<AdminRankingTypePage>(`/admin/ranking-types/${buildQueryString(params)}`);
}

export function createAdminRankingType(payload: CreateAdminRankingTypePayload): Promise<AdminRankingType> {
  requireLogin();
  return apiRequest<AdminRankingType>("/admin/ranking-types/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminRankingTypeDetail(id: number | string): Promise<AdminRankingType> {
  requireLogin();
  return apiRequest<AdminRankingType>(`/admin/ranking-types/${id}/`);
}

export function updateAdminRankingType(
  id: number | string,
  payload: UpdateAdminRankingTypePayload,
): Promise<AdminRankingType> {
  requireLogin();
  return apiRequest<AdminRankingType>(`/admin/ranking-types/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function updateAdminRankingTypeStatus(
  id: number | string,
  payload: UpdateRankingTypeStatusPayload,
): Promise<AdminRankingType> {
  requireLogin();
  return apiRequest<AdminRankingType>(`/admin/ranking-types/${id}/status/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAdminRankingItems(params: AdminRankingItemListParams = {}): Promise<AdminRankingItemPage> {
  requireLogin();
  return apiRequest<AdminRankingItemPage>(`/admin/ranking-items/${buildQueryString(params)}`);
}

export function createAdminRankingItem(payload: CreateAdminRankingItemPayload): Promise<AdminRankingItem> {
  requireLogin();
  return apiRequest<AdminRankingItem>("/admin/ranking-items/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAdminRankingItemDetail(id: number | string): Promise<AdminRankingItem> {
  requireLogin();
  return apiRequest<AdminRankingItem>(`/admin/ranking-items/${id}/`);
}

export function updateAdminRankingItem(
  id: number | string,
  payload: UpdateAdminRankingItemPayload,
): Promise<AdminRankingItem> {
  requireLogin();
  return apiRequest<AdminRankingItem>(`/admin/ranking-items/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAdminNovels(params: AdminNovelListParams = {}): Promise<AdminNovelPage> {
  requireLogin();
  return apiRequest<AdminNovelPage>(`/admin/novels/${buildQueryString(params)}`);
}

export function getAdminNovelDetail(id: number | string): Promise<AdminNovelDetail> {
  requireLogin();
  return apiRequest<AdminNovelDetail>(`/admin/novels/${id}/`);
}

export function updateAdminNovelStatus(id: number | string, payload: UpdateNovelStatusPayload): Promise<AdminNovel> {
  requireLogin();
  return apiRequest<AdminNovel>(`/admin/novels/${id}/status/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function updateAdminNovelFeatured(id: number | string, payload: UpdateNovelFeaturedPayload): Promise<AdminNovel> {
  requireLogin();
  return apiRequest<AdminNovel>(`/admin/novels/${id}/featured/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAdminChapters(params: AdminChapterListParams = {}): Promise<AdminChapterPage> {
  requireLogin();
  return apiRequest<AdminChapterPage>(`/admin/chapters/${buildQueryString(params)}`);
}

export function getAdminChapterDetail(id: number | string): Promise<AdminChapterDetail> {
  requireLogin();
  return apiRequest<AdminChapterDetail>(`/admin/chapters/${id}/`);
}

export function updateAdminChapterStatus(id: number | string, payload: UpdateChapterStatusPayload): Promise<AdminChapter> {
  requireLogin();
  return apiRequest<AdminChapter>(`/admin/chapters/${id}/status/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getAdminComments(params: AdminCommentListParams = {}): Promise<AdminCommentPage> {
  requireLogin();
  return apiRequest<AdminCommentPage>(`/admin/comments/${buildQueryString(params)}`);
}

export function getAdminCommentDetail(id: number | string): Promise<AdminCommentDetail> {
  requireLogin();
  return apiRequest<AdminCommentDetail>(`/admin/comments/${id}/`);
}

export function updateAdminCommentStatus(id: number | string, payload: UpdateCommentStatusPayload): Promise<AdminComment> {
  requireLogin();
  return apiRequest<AdminComment>(`/admin/comments/${id}/status/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
