import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";

function roleScope(role: string, zones: Array<{ name: string }>): string {
  if (role === "ADMIN") return "Scope: All organization zones";
  if (role === "MANAGER") return `Managed role: MANAGER · Allowed Zones: ${zones.map((zone) => zone.name).join(" + ")}`;
  return "Operator access is limited to the assigned zones below.";
}

export function DashboardPage() {
  const { user } = useAuth();
  if (user === null) return null;

  return (
    <AppShell>
      <section className="page-heading"><div><p className="eyebrow">ACCOUNT SCOPE</p><h1>Dashboard</h1><p>{roleScope(user.role, user.zones)}</p></div></section>
      <section className="profile-grid" aria-label="Security profile">
        <article className="profile-card primary-profile"><span className="field-label">Username</span><strong>{user.username}</strong><span className="display-name">{user.display_name}</span></article>
        <article className="profile-card"><span className="field-label">Role</span><strong>{user.role}</strong></article>
        <article className="profile-card"><span className="field-label">Manager</span><strong>{user.manager?.username ?? "Not assigned"}</strong></article>
      </section>
      <section className="detail-grid">
        <article className="detail-card"><h2>Allowed Zones</h2>{user.role === "ADMIN" && <p>Scope: All organization zones</p>}<ul className="token-list">{user.zones.map((zone) => <li key={zone.id}>{zone.name}</li>)}</ul></article>
        <article className="detail-card"><h2>Permissions</h2><ul className="permission-list">{user.permissions.map((permission) => <li key={permission}>{permission}</li>)}</ul></article>
      </section>
    </AppShell>
  );
}
