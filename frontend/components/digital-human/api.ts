export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** fetch with a time limit, which also stops when the caller's signal aborts. */
export async function apiFetch(path: string, init: RequestInit = {}, timeoutMs = 120_000) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  init.signal?.addEventListener("abort", abort);
  const timer = setTimeout(abort, timeoutMs);
  try {
    return await fetch(`${apiUrl}${path}`, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
    init.signal?.removeEventListener("abort", abort);
  }
}
