import type { UserBasic } from "@/types/user";

export type RegisterPayload = {
  username: string;
  password: string;
  password_confirm: string;
  nickname?: string;
  email?: string;
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type LoginResponse = {
  access: string;
  refresh: string;
  user: UserBasic;
};

export type RefreshTokenResponse = {
  access: string;
};
