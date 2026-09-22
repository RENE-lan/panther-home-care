import { api } from './client';
export const aiApi = {
  copilot: (q: string) => api('/copilot/', 'POST', { q }),
  family: () => api('/family/'),
  linkFamily: (code: string) => api('/link-family/', 'POST', { code }),
};
