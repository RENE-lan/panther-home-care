import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from '../api/client';
export async function queuedApi(path: string, method: string, body?: any) {
  try { return await api(path, method, body); } catch (e: any) {
    if (!e.status) { const q = JSON.parse((await AsyncStorage.getItem('queue')) || '[]'); q.push({ path, method, body }); await AsyncStorage.setItem('queue', JSON.stringify(q)); return { __queued: true }; }
    throw e; } }
export async function flushQueue() {
  const q = JSON.parse((await AsyncStorage.getItem('queue')) || '[]'); if (!q.length) return 0;
  const rest: any[] = []; let done = 0;
  for (const it of q) { try { await api(it.path, it.method, it.body); done++; } catch (e) { rest.push(it); } }
  await AsyncStorage.setItem('queue', JSON.stringify(rest)); return done; }
