const ACCESS_TOKEN_KEY = "sunshine_reading_access_token";
const REFRESH_TOKEN_KEY = "sunshine_reading_refresh_token";
export const AUTH_TOKEN_CHANGED_EVENT = "sunshine_reading_auth_token_changed";
export const AUTH_TOKEN_STORAGE_KEYS = [ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY] as const;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function dispatchTokenChanged(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(AUTH_TOKEN_CHANGED_EVENT));
}

export function getAccessToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  dispatchTokenChanged();
}

export function setAccessToken(access: string): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  dispatchTokenChanged();
}

export function clearTokens(): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  dispatchTokenChanged();
}
