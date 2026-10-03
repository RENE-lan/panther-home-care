import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, loadToken, setToken, loadApiBase } from './api';

type User = { name?: string; role?: string; username?: string; role_label?: string } | null;
type Ctx = {
  user: User; ready: boolean;
  signIn: (u: string, p: string) => Promise<void>;
  signOut: () => Promise<void>;
};
const AuthCtx = createContext<Ctx>({} as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      await loadApiBase();
      const t = await loadToken();
      if (t) { try { const me = await api.me(); setUser(me); } catch { await setToken(null); } }
      setReady(true);
    })();
  }, []);

  const signIn = async (u: string, p: string) => {
    const r = await api.login(u, p);
    await setToken(r.token);
    setUser({ name: r.name, role: r.role, role_label: r.role_label });
  };
  const signOut = async () => { await setToken(null); setUser(null); };

  return <AuthCtx.Provider value={{ user, ready, signIn, signOut }}>{children}</AuthCtx.Provider>;
}
