import { useEffect, useState } from "react";

import { getProtectedMediaUrl, type EventResult } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function displayOffset(milliseconds: number | null): string {
  if (milliseconds === null) return "—";
  const seconds = Math.floor(milliseconds / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function useMediaUrl(path: string | null): string | null {
  const { token } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!path || !token) return;
    let currentUrl: string | null = null;
    void getProtectedMediaUrl(token, path).then((nextUrl) => {
      currentUrl = nextUrl;
      setUrl(nextUrl);
    }).catch(() => setUrl(null));
    return () => { if (currentUrl) URL.revokeObjectURL(currentUrl); };
  }, [path, token]);
  return url;
}

export function EventResultCard({ event }: { event: EventResult }) {
  const snapshotUrl = useMediaUrl(event.snapshot_url);
  const clipUrl = useMediaUrl(event.clip_url);

  return (
    <article className="event-card">
      <header><span className="event-type">{event.event_type ?? "event"}</span><strong>{event.event_id}</strong></header>
      <dl>
        <div><dt>Camera</dt><dd>{event.camera_id ?? "—"}</dd></div>
        <div><dt>Event type</dt><dd>{event.event_type ?? "—"}</dd></div>
        <div><dt>Occurred at</dt><dd>{event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "—"}</dd></div>
        <div><dt>Video offset</dt><dd>{displayOffset(event.start_offset_ms)} – {displayOffset(event.end_offset_ms)}</dd></div>
        <div><dt>Confidence</dt><dd>{event.confidence === null ? "—" : `${Math.round(event.confidence * 100)}%`}</dd></div>
      </dl>
      {snapshotUrl !== null && <img className="event-thumbnail" src={snapshotUrl} alt={`Snapshot for ${event.event_id}`} />}
      {clipUrl !== null && <div className="clip-area"><a className="clip-link" href={clipUrl} target="_blank" rel="noreferrer">Play Clip</a><video controls src={clipUrl}>Video playback is not supported by this browser.</video></div>}
    </article>
  );
}
