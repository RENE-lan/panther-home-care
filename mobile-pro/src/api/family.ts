import { api } from './client';
// Family module — wraps the existing /api/mobile endpoints (single source of truth)
export const familyApi = {
  me: () => api('/family/'),
  lovedOne: () => api('/family/'),
  reports: () => api('/reports/'),
  invoices: () => api('/family/'),
  messages: () => api('/messages/'),
  sendMessage: (body: string) => api('/messages/', 'POST', { body }),
  payInvoice: (id: number) => api(`/invoices/${id}/pay/`, 'POST'),
  linkLovedOne: (code: string) => api('/link-family/', 'POST', { code }),
};
