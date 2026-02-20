/**
 * Insights API Client — typed Axios wrappers for all Phase 1-3 endpoints.
 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/insights',
  headers: { 'Content-Type': 'application/json' },
});

/* ═══════════════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════════════ */

export interface Job {
  job_id: string;
  first_date: string;
  last_date: string;
  report_count: number;
  sample_count: number;
  chemical_txn_count: number;
}

export interface JobSummary {
  job_id: string;
  first_date: string | null;
  last_date: string | null;
  total_days: number;
  max_depth_md: number | null;
  max_depth_tvd: number | null;
  mud_type: string | null;
  unique_chemicals: number;
  total_samples: number;
  equipment_days: number;
  chemical_transactions: number;
  engineers: string[];
}

export interface Shaker {
  name: string;
  hours: number;
  mesh: (number | null)[];
}

export interface Centrifuge {
  name: string;
  hours: number;
  feed_rate: number | null;
  type: string | null;
}

export interface Hydrocyclone {
  hours: number;
  size: string | null;
  cones: number | null;
}

export interface EquipmentData {
  shakers: Shaker[];
  centrifuges: Centrifuge[];
  hydrocyclones: {
    desander: Hydrocyclone;
    desilter: Hydrocyclone;
    mud_cleaner: Hydrocyclone;
  };
}

export interface MudProperties {
  mud_weight: number | null;
  pv: number | null;
  yp: number | null;
  gel_10s: number | null;
  gel_10m: number | null;
  gel_30m: number | null;
  solids: number | null;
  sand: number | null;
  lgs: number | null;
  hgs: number | null;
  drill_solids: number | null;
  ph: number | null;
  chloride: number | null;
  filtrate: number | null;
  oil_ratio: number | null;
  es: number | null;
  samples_count: number;
}

export interface ChemicalEntry {
  item: string;
  add_loss: string;
  quantity: number;
  units: string;
  category: string;
}

export interface Volumes {
  total_circ: number | null;
  pits: number | null;
  in_storage: number | null;
  mud_type: string | null;
}

export interface TimelineDay {
  date: string;
  depth_md: number | null;
  depth_tvd: number | null;
  activity: string | null;
  equipment: EquipmentData;
  mud_properties: MudProperties;
  mud_properties_by_shift: Record<string, MudProperties>;
  chemicals: ChemicalEntry[];
  volumes: Volumes | null;
  remarks: string | null;
  engineer: string | null;
}

export interface Event {
  id: string;
  event_type: string;
  severity: 'high' | 'medium' | 'low';
  date: string;
  title: string;
  description: string;
  values: Record<string, unknown>;
  related_events: string[];
}

export interface CausalLink {
  cause_event_id: string;
  effect_event_id: string;
  rule_name: string;
  explanation: string;
  confidence: string;
}

export interface InsightItem {
  severity: string;
  title: string;
  narrative: string;
  cause: string | null;
  recommendation: string;
  event_type?: string;
  values?: Record<string, unknown>;
}

export interface InsightsResponse {
  date: string;
  summary: string;
  insights: InsightItem[];
  shift_notes: Record<string, string>;
  recommendations: string[];
}

export interface ChemicalFirstAppearance {
  item_name: string;
  category: string;
  first_date: string;
  first_quantity: number | null;
  units: string | null;
}

/* ═══════════════════════════════════════════════════════════════════════════
   API Functions
   ═══════════════════════════════════════════════════════════════════════════ */

export async function getJobs(): Promise<Job[]> {
  const { data } = await api.get<{ jobs: Job[] }>('/jobs');
  return data.jobs;
}

export async function getJobSummary(jobId: string): Promise<JobSummary> {
  const { data } = await api.get<JobSummary>(`/jobs/${jobId}/summary`);
  return data;
}

export async function getTimeline(
  jobId: string,
  start?: string,
  end?: string,
): Promise<TimelineDay[]> {
  const params: Record<string, string> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  const { data } = await api.get<{ timeline: TimelineDay[] }>(`/jobs/${jobId}/timeline`, { params });
  return data.timeline;
}

export async function getEvents(
  jobId: string,
  start?: string,
  end?: string,
  severity?: string,
): Promise<{ events: Event[]; causal_links: CausalLink[]; total: number }> {
  const params: Record<string, string> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  if (severity) params.severity = severity;
  const { data } = await api.get(`/jobs/${jobId}/events`, { params });
  return data;
}

export async function getInsights(jobId: string, date: string, signal?: AbortSignal): Promise<InsightsResponse> {
  const { data } = await api.get<InsightsResponse>(`/jobs/${jobId}/insights/${date}`, { signal });
  return data;
}

export async function getNewChemicals(jobId: string): Promise<ChemicalFirstAppearance[]> {
  const { data } = await api.get<{ new_chemicals: ChemicalFirstAppearance[] }>(`/jobs/${jobId}/chemicals/new`);
  return data.new_chemicals;
}

export function getReportPdfUrl(jobId: string, date: string, shift = 'day'): string {
  return `/api/insights/jobs/${jobId}/report/${date}?format=pdf&shift=${shift}`;
}
