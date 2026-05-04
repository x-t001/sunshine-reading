import type { PaginatedResponse } from "@/types/api";

export type AdminUserRole = "reader" | "author" | "reviewer" | "admin";

export type AdminUser = {
  id: number;
  username: string;
  nickname: string;
  email: string;
  phone: string;
  role: AdminUserRole;
  is_banned: boolean;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
};

export type AdminUserDetail = AdminUser & {
  avatar: string;
  bio: string;
  novel_count: number;
  comment_count: number;
  bookshelf_count: number;
  rating_count: number;
};

export type GetAdminUsersParams = {
  page?: number | string;
  page_size?: number | string;
  keyword?: string;
  role?: AdminUserRole | "";
  is_banned?: boolean | "";
};

export type UpdateUserRolePayload = {
  role: AdminUserRole;
};

export type BanUserPayload = {
  reason?: string;
};

export type AdminUserPage = PaginatedResponse<AdminUser>;
