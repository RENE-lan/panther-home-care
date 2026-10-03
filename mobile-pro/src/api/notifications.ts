import { api } from './client';
export const notificationsApi = {
  registerPushToken: (token: string) => api('/push-token/', 'POST', { token }),
};
