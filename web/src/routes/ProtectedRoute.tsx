import { type ReactNode, useEffect } from "react";

import { useAuth } from "../auth/AuthContext";
import { navigate } from "./navigation";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  useEffect(() => {
    if (!token || !user) navigate("/login", true);
  }, [token, user]);
  if (!token || !user) return null;
  return <>{children}</>;
}
