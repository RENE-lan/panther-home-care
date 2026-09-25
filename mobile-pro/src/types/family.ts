export interface LovedOne { id?: number; name: string; status: 'stable' | 'attention' | 'urgent'; status_label?: string; next_visit?: any; last_visit?: any; care_plan?: string[]; }
export interface FamilyReport { id: number; date: string; time?: string; caregiver: string; mood?: string; notes?: string; signed?: boolean; arrival?: string; departure?: string; evv?: string; tasks?: string[]; }
export interface FamilyInvoice { id: number; number: string; period: string; amount: number; paid: boolean; status?: string; }
