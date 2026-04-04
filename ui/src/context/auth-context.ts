import { createContext } from "react";
import type { AuthUser } from "@/types/auth";

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isReady: boolean;
}

export interface AuthContextValue extends AuthState {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName?: string | null) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
