import { ApiRequestError, apiRequest, buildQueryString } from "@/lib/api/request";
import { getAccessToken } from "@/lib/auth/token";
import type {
  AdminUser,
  AdminUserDetail,
  AdminUserPage,
  AdminUserRole,
  BanUserPayload,
  GetAdminUsersParams,
} from "@/types/admin";

function requireLogin(): void {
  if (!getAccessToken()) {
    throw new ApiRequestError("请先登录后再访问管理后台。", 401);
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
