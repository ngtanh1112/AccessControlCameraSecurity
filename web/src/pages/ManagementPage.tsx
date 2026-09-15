import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  demoZones,
  getAdminUsers,
  getManagedOperators,
  type ManagedUser,
  updateManagedOperatorZones,
  updateManagerZones,
  updateOperatorManager,
  updateOperatorZones,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { UserScopeEditor } from "../components/UserScopeEditor";

function messageFor(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) return "Không có quyền thực hiện thay đổi này.";
  return error instanceof ApiError ? error.message : "Unable to update scope.";
}

export function ManagementPage() {
  const { token, user } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const managers = useMemo(() => users.filter((entry) => entry.role === "MANAGER"), [users]);
  const operators = useMemo(() => users.filter((entry) => entry.role === "OPERATOR"), [users]);

  useEffect(() => {
    if (!token || !user || user.role === "OPERATOR") return;
    setState("loading");
    const loader = user.role === "ADMIN" ? getAdminUsers(token) : getManagedOperators(token);
    void loader
      .then((loaded) => { setUsers(loaded); setState("ready"); })
      .catch((reason: unknown) => { setError(messageFor(reason)); setState("error"); });
  }, [token, user]);

  function replaceUser(updated: ManagedUser) {
    setUsers((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
  }

  if (user?.role === "OPERATOR") {
    return <AppShell><section className="access-denied-page"><p className="eyebrow">403</p><h1>Không có quyền</h1><p>Tài khoản OPERATOR không được phép truy cập quản lý scope.</p></section></AppShell>;
  }

  if (!user || !token) return null;
  const activeToken = token;

  async function saveAdminManagerZones(manager: ManagedUser, zoneIds: string[]) {
    try {
      replaceUser(await updateManagerZones(activeToken, manager.id, zoneIds));
      setError(null);
    } catch (reason: unknown) { setError(messageFor(reason)); }
  }

  async function saveAdminOperatorZones(operator: ManagedUser, zoneIds: string[]) {
    try {
      replaceUser(await updateOperatorZones(activeToken, operator.id, zoneIds));
      setError(null);
    } catch (reason: unknown) { setError(messageFor(reason)); }
  }

  async function saveManagerOperatorZones(operator: ManagedUser, zoneIds: string[]) {
    try {
      replaceUser(await updateManagedOperatorZones(activeToken, operator.id, zoneIds));
      setError(null);
    } catch (reason: unknown) { setError(messageFor(reason)); }
  }

  return (
    <AppShell>
      <section className="management-heading"><div><p className="eyebrow">DELEGATION HIERARCHY</p><h1>Management</h1><p>{user.role === "ADMIN" ? "Manage managers, operators, assignments and current scopes." : "Manage scopes for your assigned operators."}</p></div></section>
      {error !== null && <p className="form-error" role="alert">{error}</p>}
      {state === "loading" && <p className="state-message">Loading management scope…</p>}
      {state === "error" && <p className="state-message">The management API could not load this view.</p>}
      {state === "ready" && user.role === "ADMIN" && <section className="management-sections">
        <section><h2>Managers</h2><div className="scope-editor-grid">{managers.map((manager) => <UserScopeEditor key={manager.id} title="Current scopes" user={manager} zones={demoZones} onSave={(zoneIds) => saveAdminManagerZones(manager, zoneIds)} />)}</div></section>
        <section><h2>Operators</h2><div className="operator-list">{operators.map((operator) => <article className="operator-management-card" key={operator.id}>
          <div><p className="field-label">Operator</p><h3>{operator.display_name}</h3><span>@{operator.username}</span></div>
          <label className="manager-selector">Manager assignment<select value={operator.manager_id ?? ""} onChange={(event) => void updateOperatorManager(activeToken, operator.id, event.target.value || null).then(replaceUser).catch((reason: unknown) => setError(messageFor(reason)))}><option value="">Unassigned</option>{managers.map((manager) => <option key={manager.id} value={manager.id}>{manager.display_name}</option>)}</select></label>
          <UserScopeEditor title="Current scopes" user={operator} zones={demoZones} onSave={(zoneIds) => saveAdminOperatorZones(operator, zoneIds)} />
        </article>)}</div></section>
      </section>}
      {state === "ready" && user.role === "MANAGER" && <section className="management-sections"><section className="manager-scope-summary"><h2>Manager Scope</h2><ul>{user.zones.map((zone) => <li key={zone.id}>✓ {zone.name}</li>)}</ul></section><section><h2>Managed Operators</h2><p className="state-message">Updates are verified by the backend delegation rules.</p><div className="scope-editor-grid">{operators.map((operator) => <UserScopeEditor key={operator.id} title={`${operator.display_name} Scope`} user={operator} zones={demoZones.filter((zone) => user.zones.some((allowed) => allowed.id === zone.id))} onSave={(zoneIds) => saveManagerOperatorZones(operator, zoneIds)} />)}{operators.length === 0 && <p className="state-message">No operators are assigned to you.</p>}</div></section></section>}
    </AppShell>
  );
}
