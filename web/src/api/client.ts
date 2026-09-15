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

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
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
