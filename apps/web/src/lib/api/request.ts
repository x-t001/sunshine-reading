import type { ApiEnvelope } from "@/types/api";
import { clearTokens, getAccessToken } from "@/lib/auth/token";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api";
const AUTH_EXPIRED_MESSAGE = "登录已过期，请重新登录。";

function isLoopbackHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1" || hostname === "[::1]";
}

function usesLoopbackHost(url: string): boolean {
  try {
    return isLoopbackHostname(new URL(url).hostname);
  } catch {
    return false;
  }
}

function formatUrlHostname(hostname: string): string {
  return hostname.includes(":") && !hostname.startsWith("[") ? `[${hostname}]` : hostname;
}

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export type ApiRequestInit = RequestInit & {
  auth?: boolean;
};

export type ApiFileDownload = {
  blob: Blob;
  fileName: string;
};

export function getApiBaseUrl(): string {
  const configuredBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).trim().replace(/\/+$/, "");

  if (typeof window === "undefined") {
    return configuredBaseUrl;
  }

  const pageHostname = window.location.hostname;
  if (!isLoopbackHostname(pageHostname) && usesLoopbackHost(configuredBaseUrl)) {
    return `${window.location.protocol}//${formatUrlHostname(pageHostname)}:8000/api`;
  }

  return configuredBaseUrl;
}

export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    searchParams.set(key, String(value));
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "请求失败，请稍后重试。";
}

export async function apiRequest<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { auth = true, ...requestInit } = init;
  const headers = new Headers(requestInit.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (requestInit.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const accessToken = getAccessToken();
  if (auth && accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${getApiBaseUrl()}${normalizedPath}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...requestInit,
      headers,
      cache: requestInit.cache ?? "no-store",
    });
  } catch (error) {
    throw new ApiRequestError(`无法连接后端 API：${getApiErrorMessage(error)}`);
  }

  let payload: ApiEnvelope<T> | null = null;
  try {
    payload = (await response.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiRequestError(`后端返回了无法解析的响应。HTTP ${response.status}`, response.status);
  }

  if (auth && response.status === 401) {
    clearTokens();
    throw new ApiRequestError(payload.message || AUTH_EXPIRED_MESSAGE, response.status);
  }

  if (!response.ok) {
    throw new ApiRequestError(payload.message || `请求失败。HTTP ${response.status}`, response.status);
  }

  if (payload.code !== 0) {
    throw new ApiRequestError(payload.message || "后端返回业务错误。", response.status);
  }

  return payload.data;
}

function getDownloadFileName(contentDisposition: string | null, fallbackFileName: string): string {
  if (!contentDisposition) {
    return fallbackFileName;
  }

  const encodedMatch = contentDisposition.match(/filename\*=utf-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      return fallbackFileName;
    }
  }

  const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);
  return quotedMatch?.[1] || fallbackFileName;
}

export async function apiFileRequest(path: string, fallbackFileName: string): Promise<ApiFileDownload> {
  const headers = new Headers({ Accept: "*/*" });
  const accessToken = getAccessToken();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${normalizedPath}`, {
      headers,
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiRequestError(`无法连接后端 API：${getApiErrorMessage(error)}`);
  }

  if (!response.ok) {
    let message = `文件下载失败。HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as ApiEnvelope<unknown>;
      message = payload.message || message;
    } catch {
      // 二进制接口异常时可能没有 JSON 响应体。
    }
    if (response.status === 401) {
      clearTokens();
      message = message || AUTH_EXPIRED_MESSAGE;
    }
    throw new ApiRequestError(message, response.status);
  }

  return {
    blob: await response.blob(),
    fileName: getDownloadFileName(response.headers.get("Content-Disposition"), fallbackFileName),
  };
}
