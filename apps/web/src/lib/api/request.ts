import type { ApiEnvelope } from "@/types/api";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
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

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${getApiBaseUrl()}${normalizedPath}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      cache: init.cache ?? "no-store",
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

  if (!response.ok) {
    throw new ApiRequestError(payload.message || `请求失败。HTTP ${response.status}`, response.status);
  }

  if (payload.code !== 0) {
    throw new ApiRequestError(payload.message || "后端返回业务错误。", response.status);
  }

  return payload.data;
}
