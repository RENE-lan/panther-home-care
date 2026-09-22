import { api } from './client';
export const adminApi = {
  users: (q = '') => api('/admin/users/?q=' + encodeURIComponent(q)),
  roles: () => api('/roles/'),
  create: (p: any) => api('/admin/users/create/', 'POST', p),
  resetPassword: (id: number, password: string) => api(`/admin/users/${id}/password/`, 'POST', { password }),
  setRole: (id: number, role: string) => api(`/admin/users/${id}/role/`, 'POST', { role }),
  toggleActive: (id: number) => api(`/admin/users/${id}/active/`, 'POST'),
};
