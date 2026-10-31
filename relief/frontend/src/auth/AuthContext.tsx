import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { api, hasToken, setToken, setUnauthorizedHandler } from "../api/client";
import type { User } from "../api/types";

interface Ctx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string, role?: "facilitator" | "admin") => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
}
const AuthCtx = createContext<Ctx>(null as unknown as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(hasToken());

  const logout = useCallback(() => { setToken(null); setUser(null); }, []);
  const refresh = useCallback(async () => { setUser(await api<User>("/auth/me")); }, []);

  useEffect(() => { setUnauthorizedHandler(() => setUser(null)); }, []);
  useEffect(() => {
    if (!hasToken()) return;
    refresh().catch(() => setUser(null)).finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ token: string; user: User }>("/auth/login", { body: { email, password } });
    setToken(r.token); setUser(r.user); return r.user;
  }, []);

  const register = useCallback(async (name: string, email: string, password: string, role: "facilitator" | "admin" = "facilitator") => {
    const r = await api<{ token: string; user: User }>("/auth/register", { body: { name, email, password, role } });
    setToken(r.token); setUser(r.user); return r.user;
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout, refresh }), [user, loading, login, register, logout, refresh]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
