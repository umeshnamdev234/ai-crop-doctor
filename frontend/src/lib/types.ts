export type Role = "user" | "assistant";
export type Lang = "en" | "hi";

export interface ImageAttachment {
  type: string; // mime type
  data: string; // base64 (no data: prefix)
}

export interface ChatMessage {
  role: Role;
  content: string;
  images?: ImageAttachment[];
  error?: string;
  emergency?: string | null;
  stats?: string;
  recommendation?: Recommendation;
  recLoading?: boolean;
  recError?: string;
}

export interface Chat {
  id: string;
  title: string;
  messages: ChatMessage[];
  updated: number;
}

export type Theme = "auto" | "light" | "dark";

export interface ServerStatus {
  state: "ok" | "warn" | "err" | "loading";
  text: string;
  sub: string;
}

export type ProblemType = "disease" | "pest" | "nutrient" | "water" | "weed" | "soil" | "general";
export type Severity = "low" | "medium" | "high" | "critical";

export interface Triage {
  crop: string;
  problem_type: ProblemType;
  likely_issues: string[];
  severity: Severity;
  source: "ai" | "keywords";
  emergency: boolean;
}

interface Ranked {
  score: number;
  match_reasons: string[];
}

export interface Expert extends Ranked {
  id: string;
  name: string;
  expert_type: string;
  crops: string[];
  expertise: string[];
  organisation: string;
  qualifications: string;
  experience_years: number;
  languages: string[];
  state: string;
  district: string;
  rating: number;
  review_count: number;
  fee: number;
  phone_consult: boolean;
  field_visit: boolean;
  next_available: string | null;
}

export interface Product extends Ranked {
  id: string;
  name: string;
  category: string;
  active_ingredient: string;
  targets: string[];
  crops: string[];
  organic: boolean;
  dose: string;
  safety_notes: string;
  waiting_period_days: number | null;
  price_inr: number | null;
  unit: string;
}

export interface Centre extends Ranked {
  id: string;
  name: string;
  centre_type: string;
  services: string[];
  state: string;
  district: string;
  address: string;
  languages: string[];
  free_service: boolean;
  next_open: string | null;
}

export interface RecFilters {
  state?: string;
  district?: string;
  language?: string;
  organic_only?: boolean;
}

export interface Recommendation {
  triage: Triage;
  emergency_notice: string | null;
  safety_reminder: string | null;
  filters: RecFilters;
  experts: Expert[];
  products: Product[];
  centres: Centre[];
}

export interface DirectoryMeta {
  counts: { experts: number; products: number; centres: number };
  states: Record<string, string[]>;
  languages: string[];
}
