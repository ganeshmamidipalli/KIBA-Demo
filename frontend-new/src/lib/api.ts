export const API_BASE = 'http://localhost:8000';

export interface GenerateRecommendationsRequest {
  project_context: any;
  product_details: any;
  combined_scope: string;
  uploaded_summaries?: string[];
  scope_bullets?: string[];
}

// KPA One-Flow interfaces
export interface IntakeRequest {
  session_id?: string;
  product_name: string;
  budget_usd: number;
  quantity: number;
  scope_text: string;
  vendors?: string[];
  uploaded_summaries?: string[];
  project_context?: any;
}

export interface IntakeResponse {
  session_id: string;
  intake: {
    status: 'questions' | 'ready';
    requirements_summary: string;
    missing_info_questions: string[];
  };
}

export interface FollowupRequest {
  session_id: string;
  followup_answers: Record<string, string>;
}

export interface FollowupResponse {
  session_id: string;
  recommendations: {
    schema_version: string;
    summary: string;
    recommendations: Array<{
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
    }>;
    recommended_index: number;
    selection_mode: string;
    disclaimer: string;
  };
}

export async function uploadFiles(files: File[]) {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_BASE}/api/files/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`File upload failed: ${response.statusText}`);
  }

  return response.json();
}

export async function analyzeFiles(files: File[]) {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await fetch(`${API_BASE}/api/files/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`File analysis failed: ${response.statusText}`);
  }

  return response.json();
}

export async function suggestVendors(product: string, category?: string) {
  const response = await fetch(`${API_BASE}/api/suggest-vendors`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ product, category }),
  });

  if (!response.ok) {
    throw new Error(`Vendor suggestion failed: ${response.statusText}`);
  }

  return response.json();
}

export async function generateRecommendations(request: GenerateRecommendationsRequest) {
  const response = await fetch(`${API_BASE}/api/generate_recommendations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Recommendations generation failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getTokenUsage() {
  const response = await fetch(`${API_BASE}/api/token-usage`);

  if (!response.ok) {
    throw new Error('Failed to fetch token usage');
  }

  return response.json();
}

// KPA One-Flow API functions
export async function startIntake(request: IntakeRequest): Promise<IntakeResponse> {
  const response = await fetch(`${API_BASE}/api/intake_recommendations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Intake failed: ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

export async function submitFollowups(request: FollowupRequest): Promise<FollowupResponse> {
  const response = await fetch(`${API_BASE}/api/submit_followups`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Follow-up submission failed: ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

export async function getSession(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/session/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`);
  }

  return response.json();
}

export async function patchAnswers(sessionId: string, followupAnswers: Record<string, string>) {
  const response = await fetch(`${API_BASE}/api/session/${sessionId}/answers`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ followup_answers: followupAnswers }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Answer update failed: ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

export async function regenerateRecommendations(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/session/${sessionId}/regenerate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Regeneration failed: ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

export async function generateProjectSummary(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/session/${sessionId}/generate_summary`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Project summary generation failed: ${response.statusText} - ${errorText}`);
  }

  return response.json();
}

export async function generateFinalRecommendations(sessionId: string) {
  const response = await fetch(`${API_BASE}/api/session/${sessionId}/generate_recommendations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Final recommendations generation failed: ${response.statusText} - ${errorText}`);
  }

  return response.json();
}


