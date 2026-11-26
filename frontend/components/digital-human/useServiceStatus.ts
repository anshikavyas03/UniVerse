"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "./api";

type Health = { database: string; model: string; documents: number | null };

/** Checks the services every 20 seconds and describes the first problem found. */
export function useServiceStatus() {
  const [warning, setWarning] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    async function check() {
      let next: string | null;
      try {
        const response = await apiFetch("/health", {}, 6000);
        if (!response.ok) throw new Error("Unhealthy");
        const health: Health = await response.json();
        next = health.database === "unavailable" ? "The knowledge database is offline. Start Docker and PostgreSQL."
          : health.model !== "ok" ? "The answering model is offline. Start Ollama or check the provider key."
          : health.documents === 0 ? "No university documents are uploaded yet, so I can’t verify university facts."
          : null;
      } catch {
        next = "The assistant backend is offline. Start it on port 8000.";
      }
      if (active) setWarning(next);
    }
    void check();
    const timer = window.setInterval(check, 20_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return warning;
}
