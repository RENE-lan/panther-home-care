import { api } from './client';
export const incidentsApi = {
  report: (id: number, payload: any) => api(`/visits/${id}/incident/`, 'POST', payload),
};
