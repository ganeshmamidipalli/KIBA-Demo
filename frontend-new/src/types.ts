export interface SpecRequirement {
  key: string;
  value: string;
}

export interface CandidateVendor {
  name: string;
  notes?: string;
}

export interface SpecVariant {
  id: string;
  title: string;
  summary: string;
  quantity: number;
  est_unit_price_usd: number;
  est_total_usd: number;
  lead_time_days: number;
  profile: string;
  metrics: Record<string, any>;
  must: SpecRequirement[];
  should: SpecRequirement[];
  nice: SpecRequirement[];
  preferred_vendors?: CandidateVendor[];
  risks?: string[];
  rationale_summary: string[];
}

export interface Recommendation {
  recommended_id: string;
  reason: string;
  scores: Record<string, number>;
  checks: Record<string, boolean>;
}

export interface RecommendationsResponse {
  variants: SpecVariant[];
  recommendation?: Recommendation;
  decision_notes: string;
}

export interface Attachment {
  id: string;
  name: string;
  mime: string;
  size: number;
  text_preview?: string;
  summary?: string;
}

export interface RFQResult {
  rfq_id: string;
  created_at: string;
  vendor_count: number;
  is_competitive: boolean;
  html_url: string;
}

// KPA One-Flow types
export interface IntakeData {
  status: 'questions' | 'ready';
  requirements_summary: string;
  missing_info_questions: string[];
}

export interface KPARecommendation {
  id: string;
  name: string;
  specs: string[];
  estimated_price_usd: number | null;
  meets_budget: boolean;
  value_note: string;
  rationale: string;
  score: number;
  vendor_search: {
    model_name: string;
    spec_fragments: string[];
    region_hint: string | null;
    budget_hint_usd: number | null;
    query_seed: string;
  };
}

export interface KPARecommendations {
  schema_version: string;
  summary: string;
  recommendations: KPARecommendation[];
  recommended_index: number;
  selection_mode: string;
  disclaimer: string;
}



