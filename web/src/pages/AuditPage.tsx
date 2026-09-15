import { useEffect, useMemo, useState } from "react";

import { ApiError, getAudit, type AuditRecord } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";

type LoadingState = "loading" | "ready" | "denied" | "error";

export function AuditPage() {
  const { token } = useAuth();
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [state, setState] = useState<LoadingState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [userFilter, setUserFilter] = useState("all");
  const [decisionFilter, setDecisionFilter] = useState("all");
  const [stageFilter, setStageFilter] = useState("all");

  useEffect(() => {
    if (!token) return;
    setState("loading");
    void getAudit(token)
      .then((items) => { setRecords(items); setState("ready"); })
      .catch((reason: unknown) => {
        if (reason instanceof ApiError && reason.status === 403) {
          setState("denied");
          return;
        }
        setError(reason instanceof ApiError ? reason.message : "Unable to load audit evidence.");
        setState("error");
      });
  }, [token]);

  const users = useMemo(() => [...new Set(records.map((record) => record.user))].sort(), [records]);
  const stages = useMemo(() => [...new Set(records.map((record) => record.stage))].sort(), [records]);
  const visibleRecords = useMemo(
    () => records.filter((record) =>
      (userFilter === "all" || record.user === userFilter)
      && (decisionFilter === "all" || record.decision === decisionFilter)
      && (stageFilter === "all" || record.stage === stageFilter),
    ),
    [decisionFilter, records, stageFilter, userFilter],
  );

  return (
    <AppShell>
      <section className="audit-heading"><div><p className="eyebrow">SECURITY EVIDENCE</p><h1>Audit</h1><p>Access decisions recorded by the backend security controls.</p></div></section>
      {state === "loading" && <p className="state-message">Loading audit evidence…</p>}
      {state === "denied" && <section className="access-denied-page"><p className="eyebrow">403</p><h1>Không có quyền</h1><p>Tài khoản này không được phép xem audit log.</p></section>}
      {state === "error" && <p className="form-error" role="alert">{error}</p>}
      {state === "ready" && <>
        <section className="audit-filters" aria-label="Audit filters">
          <label>User<select value={userFilter} onChange={(event) => setUserFilter(event.target.value)}><option value="all">All users</option>{users.map((username) => <option key={username} value={username}>{username}</option>)}</select></label>
          <label>Decision<select value={decisionFilter} onChange={(event) => setDecisionFilter(event.target.value)}><option value="all">All decisions</option><option value="ALLOW">ALLOW</option><option value="DENY">DENY</option></select></label>
          <label>Stage<select value={stageFilter} onChange={(event) => setStageFilter(event.target.value)}><option value="all">All stages</option>{stages.map((stage) => <option key={stage} value={stage}>{stage}</option>)}</select></label>
        </section>
        <div className="audit-table-wrap"><table className="audit-table"><thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Resource</th><th>Decision</th><th>Reason</th><th>Stage</th><th>Request ID</th></tr></thead><tbody>
          {visibleRecords.map((record) => <tr key={record.id}><td>{new Date(record.timestamp).toLocaleString()}</td><td>{record.user}</td><td>{record.action}</td><td>{record.resource_type}{record.resource_id ? ` · ${record.resource_id}` : ""}</td><td><span className={record.decision === "ALLOW" ? "trace-value allow" : "trace-value deny"}>{record.decision}</span></td><td>{record.reason}</td><td>{record.stage}</td><td className="trace-id">{record.request_id}</td></tr>)}
          {visibleRecords.length === 0 && <tr><td className="empty-cell" colSpan={8}>No audit records match the current filters.</td></tr>}
        </tbody></table></div>
      </>}
    </AppShell>
  );
}
