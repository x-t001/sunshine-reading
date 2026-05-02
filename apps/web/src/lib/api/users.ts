import { apiRequest } from "@/lib/api/request";
import type { CurrentUser, UpdateCurrentUserPayload } from "@/types/user";

export function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/users/me/");
}

export function updateCurrentUser(payload: UpdateCurrentUserPayload): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/users/me/", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
