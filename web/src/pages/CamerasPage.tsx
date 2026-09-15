import { useEffect, useState } from "react";

import { ApiError, getCameras, type Camera } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";

export function CamerasPage() {
  const { token } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    setState("loading");
    void getCameras(token)
      .then((items) => { setCameras(items); setState("ready"); })
      .catch((reason: unknown) => { setError(reason instanceof ApiError ? reason.message : "Unable to load cameras."); setState("error"); });
  }, [token]);

  return (
    <AppShell>
      <section className="page-heading camera-heading"><div><p className="eyebrow">PROTECTED INVENTORY</p><h1>Cameras</h1><p>Only cameras returned by the protected backend API appear here.</p></div>{state === "ready" && <span className="camera-count">{cameras.length} available</span>}</section>
      {state === "loading" && <p className="state-message">Loading authorized cameras…</p>}
      {state === "error" && <p className="form-error" role="alert">{error}</p>}
      {state === "ready" && <section className="camera-grid" aria-label="Available cameras">
        {cameras.map((camera) => <article className="camera-card" key={camera.id}>
          <header><span className={`camera-status ${camera.status}`} aria-label={`Status: ${camera.status}`} /><span>{camera.status}</span></header>
          <h2>{camera.name}</h2>
          <dl><div><dt>Camera ID</dt><dd>{camera.id}</dd></div><div><dt>Zone</dt><dd>{camera.zone_id}</dd></div><div><dt>Status</dt><dd>{camera.status}</dd></div></dl>
        </article>)}
        {cameras.length === 0 && <p className="state-message">No cameras are assigned to this account.</p>}
      </section>}
    </AppShell>
  );
}
