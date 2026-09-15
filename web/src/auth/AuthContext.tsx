import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { ApiError, getCurrentUser, login, type UserProfile } from "../api/client";
import { clearToken, readToken, saveToken } from "./token";

type AuthContextValue = {
  token: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readToken());
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token === null) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    void getCurrentUser(token)
      .then(setUser)
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          clearToken();
          setToken(null);
        }
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isLoading,
      async signIn(username, password) {
        const response = await login(username, password);
        const profile = await getCurrentUser(response.access_token);
        saveToken(response.access_token);
        setUser(profile);
        setToken(response.access_token);
      },
      signOut() {
        clearToken();
        setUser(null);
        setToken(null);
      },
    }),
    [isLoading, token, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
