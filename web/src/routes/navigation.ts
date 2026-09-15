import { useEffect, useState } from "react";

const NAVIGATION_EVENT = "access-control:navigation";

export function navigate(path: string, replace = false): void {
  if (window.location.pathname === path) return;
  window.history[replace ? "replaceState" : "pushState"]({}, "", path);
  window.dispatchEvent(new Event(NAVIGATION_EVENT));
}

export function useCurrentPath(): string {
  const [path, setPath] = useState(() => window.location.pathname);
  useEffect(() => {
    const updatePath = () => setPath(window.location.pathname);
    window.addEventListener("popstate", updatePath);
    window.addEventListener(NAVIGATION_EVENT, updatePath);
    return () => {
      window.removeEventListener("popstate", updatePath);
      window.removeEventListener(NAVIGATION_EVENT, updatePath);
    };
  }, []);
  return path;
}
