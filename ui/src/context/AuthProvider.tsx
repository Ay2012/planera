import type { PropsWithChildren } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginRequest, meRequest, signupRequest } from "@/api/auth";
import { AuthContext, type AuthContextValue, type AuthState } from "@/context/auth-context";
import { AUTH_ACCESS_TOKEN_KEY } from "@/lib/authToken";
import type { SignupRequestBody } from "@/types/auth";

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(AUTH_ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

function persistToken(token: string | null) {
  try {
    if (token) {
      localStorage.setItem(AUTH_ACCESS_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_ACCESS_TOKEN_KEY);
    }
  } catch {
    // Ignore storage failures (private mode, etc.)
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const [{ user, token, isReady }, setState] = useState<AuthState>({
    user: null,
    token: null,
    isReady: false,
  });

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const stored = readStoredToken();
      if (!stored) {
        if (!cancelled) {
          setState({ user: null, token: null, isReady: true });
        }
        return;
      }

      try {
        const me = await meRequest(stored);
        if (cancelled) return;
        setState({ user: me.user, token: stored, isReady: true });
      } catch {
        persistToken(null);
        if (!cancelled) {
          setState({ user: null, token: null, isReady: true });
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const trimmedEmail = email.trim().toLowerCase();
    const res = await loginRequest({ email: trimmedEmail, password });
    persistToken(res.access_token);
    setState({ user: res.user, token: res.access_token, isReady: true });
  }, []);

  const signUp = useCallback(async (email: string, password: string, displayName?: string | null) => {
    const trimmedEmail = email.trim().toLowerCase();
    const payload: SignupRequestBody = {
      email: trimmedEmail,
      password,
    };
    if (displayName?.trim()) {
      payload.display_name = displayName.trim();
    }
    const res = await signupRequest(payload);
    persistToken(res.access_token);
    setState({ user: res.user, token: res.access_token, isReady: true });
  }, []);

  const logout = useCallback(() => {
    persistToken(null);
    setState({ user: null, token: null, isReady: true });
    navigate("/sign-in", { replace: true });
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isReady,
      isAuthenticated: Boolean(user && token),
      login,
      signUp,
      logout,
    }),
    [user, token, isReady, login, signUp, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
