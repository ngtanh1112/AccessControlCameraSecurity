import type { ReactNode } from "react";

import { useAuth } from "../auth/AuthContext";
import { navigate, useCurrentPath } from "../routes/navigation";

export function AppShell({ children }: { children: ReactNode }) {
  const path = useCurrentPath();
  const { user, signOut } = useAuth();

  function logout() {
    signOut();
    navigate("/login", true);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => navigate("/dashboard")}>
          <span className="brand-mark" aria-hidden="true">◉</span>
          <span>Camera Security</span>
        </button>
        <div className="identity">
          <span>{user?.display_name}</span>
          <span className="role-badge">{user?.role}</span>
          <button className="text-button" type="button" onClick={logout}>Logout</button>
        </div>
      </header>
      <div className="workspace">
        <nav className="sidebar" aria-label="Main navigation">
          <button className={path === "/dashboard" ? "nav-link active" : "nav-link"} type="button" onClick={() => navigate("/dashboard")}>Dashboard</button>
          <button className={path === "/cameras" ? "nav-link active" : "nav-link"} type="button" onClick={() => navigate("/cameras")}>Cameras</button>
          <button className={path === "/chat" ? "nav-link active" : "nav-link"} type="button" onClick={() => navigate("/chat")}>Chat</button>
        </nav>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
