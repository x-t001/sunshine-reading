"use client";

import { useCallback, useEffect, useState } from "react";
import { logout as logoutApi } from "@/lib/api/auth";
import { getCurrentUser } from "@/lib/api/users";
import { getAccessToken } from "@/lib/auth/token";
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
