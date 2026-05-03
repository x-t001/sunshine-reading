"use client";

import { useCallback, useEffect, useState } from "react";
import { logout as logoutApi } from "@/lib/api/auth";
import { getCurrentUser } from "@/lib/api/users";
import { ApiRequestError } from "@/lib/api/request";
import { AUTH_TOKEN_CHANGED_EVENT, AUTH_TOKEN_STORAGE_KEYS, clearTokens, getAccessToken } from "@/lib/auth/token";
import type { CurrentUser } from "@/types/user";

type UseAuthState = {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  reload: () => Promise<void>;
  logout: () => void;
};

function getMessage(error: unknown): string {
  return error instanceof Error ? error.message : "用户信息加载失败。";
}

export function useAuth(): UseAuthState {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const access = getAccessToken();
    if (!access) {
      setUser(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setError(null);
    } catch (loadError) {
      if (loadError instanceof ApiRequestError && loadError.status === 401) {
        clearTokens();
      }
      setUser(null);
      setError(getMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    void (async () => {
      await Promise.resolve();
      if (!active) {
        return;
      }

      const access = getAccessToken();
      if (!access) {
        setUser(null);
        setError(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const currentUser = await getCurrentUser();
        if (active) {
          setUser(currentUser);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          if (loadError instanceof ApiRequestError && loadError.status === 401) {
            clearTokens();
          }
          setUser(null);
          setError(getMessage(loadError));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    function handleTokenChanged() {
      void reload();
    }

    function handleStorageChanged(event: StorageEvent) {
      if (event.key && !AUTH_TOKEN_STORAGE_KEYS.includes(event.key as (typeof AUTH_TOKEN_STORAGE_KEYS)[number])) {
        return;
      }
      void reload();
    }

    window.addEventListener(AUTH_TOKEN_CHANGED_EVENT, handleTokenChanged);
    window.addEventListener("storage", handleStorageChanged);
    return () => {
      window.removeEventListener(AUTH_TOKEN_CHANGED_EVENT, handleTokenChanged);
      window.removeEventListener("storage", handleStorageChanged);
    };
  }, [reload]);

  const logout = useCallback(() => {
    logoutApi();
    setUser(null);
    setError(null);
  }, []);

  return {
    user,
    loading,
    error,
    isAuthenticated: Boolean(user),
    reload,
    logout,
  };
}
