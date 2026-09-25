import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authApi } from '../api/auth';
import { loadSession, setToken } from '../api/client';

type AuthState = {
  token: string | null; me: any | null; ready: boolean;
  restore: () => Promise<void>;
  setSession: (data: any) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  token: null, me: null, ready: false,
  restore: async () => {
    const t = await loadSession();
    const m = await AsyncStorage.getItem('me');
    if (t && m) { try { await authApi.me(); set({ token: t, me: JSON.parse(m) }); } catch (e) { setToken(null); } }
    set({ ready: true });
  },
  setSession: async (data) => {
    setToken(data.token); await AsyncStorage.setItem('tok', data.token); await AsyncStorage.setItem('me', JSON.stringify(data));
    set({ token: data.token, me: data });
  },
  logout: async () => {
    try { await authApi.logout(); } catch (e) {}
    setToken(null); await AsyncStorage.multiRemove(['tok', 'me']); set({ token: null, me: null });
  },
}));
