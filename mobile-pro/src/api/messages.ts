import { api } from './client';
export const messagesApi = {
  list: () => api('/messages/'),
  send: (body: string) => api('/messages/', 'POST', { body }),
};
