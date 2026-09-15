import type { EventResult } from "../api/client";

function displayOffset(milliseconds: number | null): string {
  if (milliseconds === null) return "—";
  const seconds = Math.floor(milliseconds / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function hasRenderableMedia(url: string | null): url is string {
  return url !== null && /^(https?:\/\/|\/|data:)/.test(url);
}

export function EventResultCard({ event }: { event: EventResult }) {
  const snapshotUrl = hasRenderableMedia(event.snapshot_url) ? event.snapshot_url : null;
  const clipUrl = hasRenderableMedia(event.clip_url) ? event.clip_url : null;

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
