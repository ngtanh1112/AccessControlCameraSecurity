import type { ConversationResponse } from "../api/client";

function Flag({ value }: { value: boolean }) {
  return <span className={value ? "trace-value allow" : "trace-value deny"}>{value ? "YES" : "NO"}</span>;
}

function Decision({ value }: { value: "ALLOW" | "DENY" }) {
  return <span className={value === "ALLOW" ? "trace-value allow" : "trace-value deny"}>{value}</span>;
}

export function ExecutionTracePanel({ trace }: { trace: ConversationResponse | null }) {
  if (trace === null) {
    return <aside className="trace-panel empty-trace"><p className="eyebrow">EXECUTION TRACE</p><h2>No request selected</h2><p>Send a prompt to inspect its authorization and execution path.</p></aside>;
  }

  return (
    <aside className="trace-panel" aria-label="Execution Trace">
      <p className="eyebrow">EXECUTION TRACE</p>
      <h2>Request path</h2>
      <dl className="trace-list">
        <div><dt>Request ID</dt><dd className="trace-id">{trace.request_id}</dd></div>
        <div><dt>Intent</dt><dd>{trace.intent}</dd></div>
        <div><dt>Pre-Authorization</dt><dd><Decision value={trace.pre_authorization} /></dd></div>
        <div><dt>Agent Invoked</dt><dd><Flag value={trace.agent_invoked} /></dd></div>
        <div><dt>Sub Agent</dt><dd>{trace.agent ?? "—"}</dd></div>
        <div><dt>MCP Invoked</dt><dd><Flag value={trace.mcp_invoked} /></dd></div>
        <div><dt>MCP Tool</dt><dd>{trace.tool ?? "—"}</dd></div>
        <div><dt>Backend Invoked</dt><dd><Flag value={trace.backend_invoked} /></dd></div>
        <div><dt>Final Decision</dt><dd><Decision value={trace.decision} /></dd></div>
      </dl>
    </aside>
  );
}
