import { api } from './client';
export const dashboardApi = {
  get: () => api('/dashboard/'),
  cgHome: () => api('/cg-home/'),
};
