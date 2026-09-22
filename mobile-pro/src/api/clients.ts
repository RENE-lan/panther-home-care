import { api } from './client';
export const clientsApi = {
  list: (q = '') => api('/clients/?q=' + encodeURIComponent(q)),
  linkFamily: (userId: number, client: string) => api('/admin/link-family/', 'POST', { user_id: userId, client }),
};
