import { useEffect } from "react";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { CamerasPage } from "./pages/CamerasPage";
import { AuditPage } from "./pages/AuditPage";
import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { IvaDemoPage } from "./pages/IvaDemoPage";
import { ManagementPage } from "./pages/ManagementPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { navigate, useCurrentPath } from "./routes/navigation";

function Redirect({ to }: { to: string }) {
  useEffect(() => navigate(to, true), [to]);
  return null;
}

function AppRouter() {
  const path = useCurrentPath();
  const { isLoading, token } = useAuth();

  if (isLoading) return <main className="app-loading">Restoring your local session…</main>;
  if (!token) {
    if (path !== "/login") return <Redirect to="/login" />;
    return <LoginPage />;
  }
  if (path === "/login") return <Redirect to="/dashboard" />;
  if (path === "/cameras") {
    return <ProtectedRoute><CamerasPage /></ProtectedRoute>;
  }
  if (path === "/chat") {
    return <ProtectedRoute><ChatPage /></ProtectedRoute>;
  }
  if (path === "/management") {
    return <ProtectedRoute><ManagementPage /></ProtectedRoute>;
  }
  if (path === "/audit") {
    return <ProtectedRoute><AuditPage /></ProtectedRoute>;
  }
  if (path === "/iva-demo") {
    return <ProtectedRoute><IvaDemoPage /></ProtectedRoute>;
  }
  if (path !== "/dashboard") return <Redirect to="/dashboard" />;
  return <ProtectedRoute><DashboardPage /></ProtectedRoute>;
}

export default function App() {
  return <AuthProvider><AppRouter /></AuthProvider>;
}
