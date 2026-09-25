export interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  role: string;
  role_label: string;
}

export interface MatchComponents {
  skills: number; distance: number; reliability: number;
  punctuality: number; workload: number; language: number;
}

export interface Recommendation {
  visit_id: number;
  client: string;
  care_type: string;
  start: string;
  end: string;
  match: {
    caregiver_id: number;
    code: string;
    name: string;
    score: number;
    distance_km: number | null;
    components: MatchComponents;
    skills_ok: boolean;
    workload: string;
  } | null;
}

export interface DashboardData {
  kpis: {
    clients: number; caregivers: number; visits_today: number;
    completed: number; incidents_open: number; incidents_critical: number;
  };
  recommendation: Recommendation | null;
  brief: { on_schedule_pct: number; confirmed: number; scheduled: number;
    completed: number; uncovered: number; late: number; summary: string };
  late: { caregiver: string; minutes_late: number; client: string; time: string }[];
  flags: { client: string; concern: string; time: string }[];
  critical: { title: string; client: string | null; at: string }[];
}

export interface ClientRow {
  id: number; code: string; name: string; risk: string; risk_label: string;
  care_type: string; address: string; language: string;
}

export interface Analytics {
  labels: string[];
  visits_total: number[]; visits_done: number[]; flags: number[]; mood: number[];
  risk_labels: string[]; risk_counts: number[]; sev_counts: number[];
  occ_labels: string[]; occ_hours: number[];
  kpi: { utilization: number; avg_visits_day: number; satisfaction: number;
    completed_30: number; open_incidents: number };
}
