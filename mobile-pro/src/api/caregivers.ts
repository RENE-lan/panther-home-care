import { api } from './client';
export const caregiversApi = {
  list: () => api('/caregivers/'),
  personnel: () => api('/personnel/'),
};
