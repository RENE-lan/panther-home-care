import { api } from './client';
export const authApi = {
  login: (login: string, password: string) => api('/login/', 'POST', { login, password }),
  signup: (payload: any) => api('/signup/', 'POST', payload),
  me: () => api('/me/'),
  logout: () => api('/logout/', 'POST'),
};
