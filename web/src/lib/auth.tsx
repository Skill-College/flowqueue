import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import api, { setAccessToken } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const me = await api.get<User>("/auth/me");
    setUser(me.data);
  }, []);

  // Bootstrap: try to mint an access token from the refresh cookie, then load user.
  useEffect(() => {
    (async () => {
      try {
        const r = await api.post("/auth/refresh", {});
        setAccessToken(r.data.access_token);
        await loadMe();
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [loadMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const r = await api.post("/auth/login", { email, password });
      setAccessToken(r.data.access_token);
      await loadMe();
    },
    [loadMe]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      const r = await api.post("/auth/register", { email, password });
      setAccessToken(r.data.access_token);
      await loadMe();
    },
    [loadMe]
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout", {});
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
