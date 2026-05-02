import { apiRequest } from "@/lib/api/request";
import { clearTokens, setAccessToken, setTokens } from "@/lib/auth/token";
import type { LoginPayload, LoginResponse, RefreshTokenResponse, RegisterPayload } from "@/types/auth";
import type { UserBasic } from "@/types/user";

export async function register(payload: RegisterPayload): Promise<UserBasic> {
  return apiRequest<UserBasic>("/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const result = await apiRequest<LoginResponse>("/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setTokens(result.access, result.refresh);
  return result;
}

export async function refreshToken(refresh: string): Promise<RefreshTokenResponse> {
  const result = await apiRequest<RefreshTokenResponse>("/auth/refresh/", {
    method: "POST",
    body: JSON.stringify({ refresh }),
  });
  setAccessToken(result.access);
  return result;
}

export function logout(): void {
  clearTokens();
}
