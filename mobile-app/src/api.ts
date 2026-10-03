import AsyncStorage from '@react-native-async-storage/async-storage';

// ── CONFIG ──────────────────────────────────────────────────────────
// Point this at your Django backend.
//  • Android emulator:      http://10.0.2.2:8000
//  • iOS simulator:         http://127.0.0.1:8000
//  • Real phone (same Wi-Fi/hotspot): http://<YOUR-PC-LAN-IP>:8000  e.g. http://192.168.1.20:8000
// Find your PC IP with `ipconfig` (Windows) → "IPv4 Address".
export let API_BASE = 'http://10.0.2.2:8000';
export const normalizeBase = (url: string) =>
  (url || '')
    .replace(/\s+/g, '')          // remove any spaces (incl. pasted %20)
    .replace(/\/+$/, '')          // trailing slashes
    .replace(/\/api\/mobile$/i, '')
    .replace(/\/api$/i, '')       // strip an accidental /api
    .replace(/\/+$/, '');
export const setApiBase = async (url: string) => {
  API_BASE = normalizeBase(url);
  await AsyncStorage.setItem('api_base', API_BASE);
};
export const loadApiBase = async () => {
  const v = await AsyncStorage.getItem('api_base');
  if (v) API_BASE = v;
  return API_BASE;
};

let TOKEN: string | null = null;
export const setToken = async (t: string | null) => {
  TOKEN = t;
  if (t) await AsyncStorage.setItem('token', t);
  else await AsyncStorage.removeItem('token');
};
export const loadToken = async () => {
  TOKEN = await AsyncStorage.getItem('token');
  return TOKEN;
};

async function req(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string>),
  };
  if (TOKEN) headers['Authorization'] = `Token ${TOKEN}`;
  const res = await fetch(`${API_BASE}/api/mobile/${path}`, { ...opts, headers });
  const text = await res.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!res.ok) throw Object.assign(new Error(data?.detail || `Erreur ${res.status}`), { status: res.status, data });
  return data;
}

export const api = {
  login: (username: string, password: string) =>
    req('login/', { method: 'POST', body: JSON.stringify({ login: username, password }) }),
  me: () => req('me/'),
  dashboard: () => req('dashboard/'),
  myVisits: () => req('my-visits/'),
  openVisits: () => req('open-visits/'),
  personnel: () => req('personnel/'),
  copilot: (q: string, history: any[] = []) =>
    req('copilot/', { method: 'POST', body: JSON.stringify({ q, history }) }),
  assign: (visitId: number, caregiverId?: number) =>
    req(`visits/${visitId}/detail/`).catch(() => null), // detail; assignment via web/approve flow
  get: (path: string) => req(path),
  post: (path: string, body: any) => req(path, { method: 'POST', body: JSON.stringify(body) }),
};
