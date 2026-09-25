import { api } from './client';
export const documentsApi = {
  mine: () => api('/me/'),
};
