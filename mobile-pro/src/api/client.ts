import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE } from '../config';

let TOKEN: string | null = null;
let BASE = API_BASE;

export async function loadSession() {
  TOKEN = await AsyncStorage.getItem('tok');
  const b = await AsyncStorage.getItem('apibase'); if (b) BASE = b;
  return TOKEN;
}
export function setToken(t: string | null) { TOKEN = t; }
export async function setBase(b: string) { BASE = b.replace(/\/$/, ''); await AsyncStorage.setItem('apibase', BASE); }
export function getBase() { return BASE; }

export async function api<T = any>(path: string, method = 'GET', body?: any): Promise<T> {
  const headers: any = { 'Content-Type': 'application/json' };
  if (TOKEN) headers.Authorization = 'Token ' + TOKEN;
  const res = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data: any = {}; try { data = await res.json(); } catch (e) {}
  if (!res.ok) { const err: any = new Error(data.detail || 'Erreur'); err.status = res.status; throw err; }
  return data as T;
}
