import { useEffect, useState } from "react";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type BackendStatus = "checking" | "ok" | "unavailable";

export default function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");

  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/health`);
        const payload: unknown = await response.json();

        if (
          response.ok &&
          typeof payload === "object" &&
          payload !== null &&
          "status" in payload &&
          payload.status === "ok"
        ) {
          setBackendStatus("ok");
          return;
        }
      } catch {
        // The status below communicates that the local backend is not reachable.
      }

      setBackendStatus("unavailable");
    };

    void checkBackendHealth();
  }, []);

  const statusLabel =
    backendStatus === "ok"
      ? "OK"
      : backendStatus === "checking"
        ? "Checking..."
        : "Unavailable";

  return (
    <main>
      <h1>Access Control Camera Security</h1>
      <p>Backend Status: {statusLabel}</p>
    </main>
  );
}
