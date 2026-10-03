import { api } from './client';
export const visitsApi = {
  mine: () => api('/my-visits/'),
  detail: (id: number) => api(`/visits/${id}/detail/`),
  open: () => api('/open-visits/'),
  request: (id: number) => api(`/open-visits/${id}/request/`, 'POST'),
  schedule: (week = 0) => api('/schedule/?week=' + week),
  matches: (id: number) => api(`/visits/${id}/matches/`),
  assign: (id: number, caregiverId: number) => api(`/visits/${id}/assign/`, 'POST', { caregiver_id: caregiverId }),
};
