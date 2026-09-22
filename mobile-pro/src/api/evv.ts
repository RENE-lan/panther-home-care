import { api } from './client';
export const evvApi = {
  checkin: (id: number, coords: any) => api(`/visits/${id}/checkin/`, 'POST', coords),
  checkout: (id: number, payload: any) => api(`/visits/${id}/checkout/`, 'POST', payload),
  timesheet: () => api('/timesheet/'),
};
