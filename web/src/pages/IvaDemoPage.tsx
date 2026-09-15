import { type FormEvent, useEffect, useState } from "react";

import { analyzeIvaRecording, ApiError, getCameras, getProtectedMediaUrl, type Camera, type IvaEvent, type IvaRecording, uploadIvaRecording } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { EventResultCard } from "../components/EventResultCard";

function defaultStartTime(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function seconds(milliseconds: number | null): string {
  const total = Math.floor((milliseconds ?? 0) / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function IvaDemoPage() {
  const { token, user } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [cameraId, setCameraId] = useState("CAM-A01");
  const [startedAt, setStartedAt] = useState(defaultStartTime);
  const [file, setFile] = useState<File | null>(null);
  const [recording, setRecording] = useState<IvaRecording | null>(null);
  const [events, setEvents] = useState<IvaEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    if (!token || user?.role !== "ADMIN") return;
    void getCameras(token)
      .then((items) => { setCameras(items); if (items[0]) setCameraId(items[0].id); })
      .catch((reason: unknown) => setError(reason instanceof ApiError ? reason.message : "Unable to load cameras."));
  }, [token, user]);

  if (user?.role !== "ADMIN") {
    return <AppShell><section className="access-denied-page"><p className="eyebrow">403</p><h1>Không có quyền</h1><p>Only ADMIN can upload and analyze video recordings.</p></section></AppShell>;
  }
  if (!token) return null;
  const activeToken = token;

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) { setError("Choose an MP4 file before uploading."); return; }
    setIsUploading(true); setError(null); setEvents([]);
    try {
      setRecording(await uploadIvaRecording(activeToken, cameraId, new Date(startedAt).toISOString(), file));
    } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.message : "Unable to upload recording."); }
    finally { setIsUploading(false); }
  }

  async function analyze() {
    if (!recording) return;
    setIsAnalyzing(true); setError(null);
    try {
      const result = await analyzeIvaRecording(activeToken, recording.recording_id);
      setRecording(result); setEvents(result.events);
    } catch (reason: unknown) { setError(reason instanceof ApiError ? reason.message : "Video analysis failed."); }
    finally { setIsAnalyzing(false); }
  }

  async function openMedia(path: string | null) {
    if (!path) return;
    try { window.open(await getProtectedMediaUrl(activeToken, path), "_blank", "noopener,noreferrer"); }
    catch (reason: unknown) { setError(reason instanceof ApiError ? reason.message : "Unable to load protected media."); }
  }

  return (
    <AppShell>
      <section className="iva-heading"><div><p className="eyebrow">ADMIN LOCAL DEMO</p><h1>Video IVA Analyzer</h1><p>Upload a short MP4, run the pretrained local detector once, then query stored event metadata.</p></div></section>
      <form className="iva-form" onSubmit={upload}>
        <label>Camera:<select value={cameraId} onChange={(event) => setCameraId(event.target.value)}>{cameras.map((camera) => <option key={camera.id} value={camera.id}>{camera.id} — {camera.name}</option>)}</select></label>
        <label>Recording started at:<input type="datetime-local" value={startedAt} onChange={(event) => setStartedAt(event.target.value)} required /></label>
        <label>Video:<input type="file" accept=".mp4,video/mp4" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></label>
        <button className="primary-button" type="submit" disabled={isUploading}>{isUploading ? "Uploading…" : "Upload"}</button>
      </form>
      {error && <p className="form-error" role="alert">{error}</p>}
      {recording && <section className="iva-recording"><h2>Recording</h2><dl><div><dt>ID</dt><dd>{recording.recording_id}</dd></div><div><dt>Camera</dt><dd>{recording.camera_id}</dd></div><div><dt>Status</dt><dd>{recording.status}</dd></div></dl>{recording.status === "PENDING" && <button className="secondary-button" type="button" onClick={() => void analyze()} disabled={isAnalyzing}>{isAnalyzing ? "Analyzing…" : "Analyze Video"}</button>}</section>}
      {recording?.status === "COMPLETED" && <section className="iva-results"><h2>Analysis completed</h2><p>Duration: {seconds(recording.duration_ms ?? null)} · Events: {events.length}</p><div className="iva-event-list">{events.map((item) => <article className="iva-event-row" key={item.event_id}><div><strong>{seconds(item.start_offset_ms)} – {seconds(item.end_offset_ms)}</strong><span>{item.event_type} · {item.confidence?.toFixed(2) ?? "—"}</span></div><div className="iva-media-actions">{item.snapshot_url && <button type="button" onClick={() => void openMedia(item.snapshot_url)}>View Snapshot</button>}{item.clip_url && <button type="button" onClick={() => void openMedia(item.clip_url)}>Play Clip</button>}</div><EventResultCard event={item} /></article>)}</div></section>}
    </AppShell>
  );
}
