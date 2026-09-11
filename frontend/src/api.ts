import type { User, DashboardData, ClientRow, Analytics } from "./types";

// In dev, the Vite proxy handles /api (same origin). In production the SPA is hosted
// separately, so set VITE_API_URL to the backend URL at build time.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...init,
  });
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    req<{ user: User }>("/auth/login/", {
      method: "POST", body: JSON.stringify({ username, password }),
    }),
  logout: () => req<{ ok: boolean }>("/auth/logout/", { method: "POST" }),
  me: () => req<{ user: User }>("/auth/me/"),
  dashboard: () => req<DashboardData>("/dashboard/"),
  clients: (q = "") => req<{ results: ClientRow[] }>(`/clients/?q=${encodeURIComponent(q)}`),
  analytics: (days = 14) => req<Analytics>(`/analytics/?days=${days}`),
};
