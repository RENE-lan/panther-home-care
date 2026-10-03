import { api } from './client';
export const careApi = {
  reports: () => api('/reports/'),
};
