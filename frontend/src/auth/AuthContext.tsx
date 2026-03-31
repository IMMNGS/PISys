import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  fetchSession,
  login as loginRequest,
  logout as logoutRequest,
} from "../api/client";
import { AuthContext, type AuthContextValue } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const session = await fetchSession();
    const nextUser = session.authenticated ? session.user : null;
    setUser(nextUser);
    return nextUser;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    refresh()
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      refresh,
      login: async (username: string, password: string) => {
        const session = await loginRequest(username, password);
        const nextUser = session.user;
        setUser(nextUser);
        return nextUser as AuthUser;
      },
      logout: async () => {
        await logoutRequest();
        setUser(null);
      },
      isAdmin: (user?.role || "") === "admin",
    }),
    [loading, user, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
