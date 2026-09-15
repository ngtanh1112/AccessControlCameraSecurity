const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type LoginResponse = { access_token: string; token_type: "bearer" };

export type UserProfile = {
  id: string;
  username: string;
  display_name: string;
  role: "ADMIN" | "MANAGER" | "OPERATOR";
  manager: { id: string; username: string } | null;
  permissions: string[];
  zones: Array<{ id: string; name: string }>;
};

export type Camera = {
  id: string;
  name: string;
  zone_id: string;
  status: "online" | "offline";
};

export type EventResult = {
  event_id: string;
  camera_id: string | null;
  recording_id: string | null;
  event_type: string | null;
  occurred_at: string | null;
  start_offset_ms: number | null;
  end_offset_ms: number | null;
  confidence: number | null;
  snapshot_url: string | null;
  clip_url: string | null;
};

export type ConversationResponse = {
  request_id: string;
  intent: string;
  pre_authorization: "ALLOW" | "DENY";
  agent_invoked: boolean;
  agent: string | null;
  mcp_invoked: boolean;
  tool: string | null;
  backend_invoked: boolean;
  decision: "ALLOW" | "DENY";
  answer: string;
  data: EventResult[] | unknown[] | Record<string, unknown> | null;
};

export type ManagedUser = {
  id: string;
  username: string;
  display_name: string;
  role: "ADMIN" | "MANAGER" | "OPERATOR";
  manager_id: string | null;
  zone_ids: string[];
};

export type AuditRecord = {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  decision: "ALLOW" | "DENY";
  reason: string;
  stage: string;
  request_id: string;
};

export type IvaRecording = {
  recording_id: string;
  camera_id: string;
  original_filename?: string;
  recording_started_at?: string;
  duration_ms?: number | null;
  status: "PENDING" | "ANALYZING" | "COMPLETED" | "FAILED";
  analyzed_at?: string | null;
  model_name?: string | null;
};

export type IvaEvent = EventResult;

export const demoZones = [
  { id: "ZONE-A", name: "Zone A" },
  { id: "ZONE-B", name: "Zone B" },
] as const;

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const message =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String(payload.detail)
        : "The request could not be completed.";
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export function login(username: string, password: string): Promise<LoginResponse> {
  return request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
}

export function getCurrentUser(token: string): Promise<UserProfile> {
  return request("/api/v1/auth/me", { headers: { Authorization: `Bearer ${token}` } });
}

export function getCameras(token: string): Promise<Camera[]> {
  return request("/api/v1/cameras", { headers: { Authorization: `Bearer ${token}` } });
}

export function sendConversationMessage(token: string, message: string): Promise<ConversationResponse> {
  return request("/api/v1/conversations/messages", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message }),
  });
}

function authorizedRequest<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, { ...init, headers: { Authorization: `Bearer ${token}`, ...init.headers } });
}

export function getAdminUsers(token: string): Promise<ManagedUser[]> {
  return authorizedRequest(token, "/api/v1/admin/users");
}

export function getManagedOperators(token: string): Promise<ManagedUser[]> {
  return authorizedRequest(token, "/api/v1/management/operators");
}

export function updateManagerZones(token: string, managerId: string, zoneIds: string[]): Promise<ManagedUser> {
  return authorizedRequest(token, `/api/v1/admin/managers/${managerId}/zones`, { method: "PUT", body: JSON.stringify({ zone_ids: zoneIds }) });
}

export function updateOperatorManager(token: string, operatorId: string, managerId: string | null): Promise<ManagedUser> {
  return authorizedRequest(token, `/api/v1/admin/operators/${operatorId}/manager`, { method: "PUT", body: JSON.stringify({ manager_id: managerId }) });
}

export function updateOperatorZones(token: string, operatorId: string, zoneIds: string[]): Promise<ManagedUser> {
  return authorizedRequest(token, `/api/v1/admin/operators/${operatorId}/zones`, { method: "PUT", body: JSON.stringify({ zone_ids: zoneIds }) });
}

export function updateManagedOperatorZones(token: string, operatorId: string, zoneIds: string[]): Promise<ManagedUser> {
  return authorizedRequest(token, `/api/v1/management/operators/${operatorId}/zones`, { method: "PUT", body: JSON.stringify({ zone_ids: zoneIds }) });
}

export function getAudit(token: string): Promise<AuditRecord[]> {
  return authorizedRequest(token, "/api/v1/audit");
}

export function uploadIvaRecording(token: string, cameraId: string, recordingStartedAt: string, file: File): Promise<IvaRecording> {
  const body = new FormData();
  body.append("camera_id", cameraId);
  body.append("recording_started_at", recordingStartedAt);
  body.append("file", file);
  return authorizedRequest(token, "/api/v1/iva/recordings", { method: "POST", body });
}

export function analyzeIvaRecording(token: string, recordingId: string): Promise<IvaRecording & { events: IvaEvent[] }> {
  return authorizedRequest(token, `/api/v1/iva/recordings/${recordingId}/analyze`, { method: "POST" });
}

export async function getProtectedMediaUrl(token: string, path: string): Promise<string> {
  const response = await fetch(`${apiBaseUrl}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new ApiError("Unable to load protected media.", response.status);
  return URL.createObjectURL(await response.blob());
}
