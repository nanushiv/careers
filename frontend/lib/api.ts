/**
 * CareerOS API Client
 * Typed wrapper for all backend API calls.
 * All methods return typed responses and throw on error.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    upgrade_url?: string;
  };
}

export interface User {
  id: string;
  clerk_id: string;
  email: string;
  full_name?: string;
  plan: "free" | "pro" | "team";
  target_roles: string[];
  career_health_score?: number;
  onboarding_completed: boolean;
  onboarding_step?: number;
}

export interface Resume {
  id: string;
  file_name: string;
  version_label: string;
  version_number: number;
  is_primary: boolean;
  parse_status: "pending" | "processing" | "completed" | "failed";
  callback_rate?: number;
  applications_used: number;
  ats_score_avg?: number;
  created_at: string;
}

export interface Analysis {
  id: string;
  analysis_type: "ats" | "recruiter" | "role_fit" | "readiness" | "rewrite";
  overall_score?: number;
  rewrite_status?: "pending" | "processing" | "completed" | "failed";
  improved_resume_url?: string;
  improved_pdf_url?: string;
  gaps: Gap[];
  strengths: Strength[];
  improvements: Improvement[];
  keyword_analysis: KeywordAnalysis;
  recruiter_signals?: RecruiterSignals;
  improvement_roadmap: RoadmapItem[];
  interview_questions: InterviewQuestion[];
  ats_red_flags?: string[];
  keyword_score?: number;
  format_score?: number;
  experience_score?: number;
  model_used?: string;
  cache_hit: boolean;
  created_at: string;
}

export interface Gap {
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  keyword?: string;
  description: string;
  fix?: string;
}

export interface Strength {
  area: string;
  description: string;
}

export interface Improvement {
  priority: string;
  action: string;
  impact: "high" | "medium" | "low";
  effort: string;
}

export interface KeywordAnalysis {
  required_found: string[];
  required_missing: string[];
  preferred_found: string[];
  preferred_missing: string[];
  density: Record<string, number>;
}

export interface RecruiterSignals {
  perception_score: number;
  first_impression: string;
  likelihood_to_shortlist: "low" | "medium" | "high" | "very_high";
  standout_positives: Array<{ point: string; why_it_matters: string }>;
  immediate_concerns: Array<{ concern: string; severity: string; context: string }>;
  positioning_gaps: Array<{ gap: string; what_recruiter_thinks: string; how_to_fix: string }>;
  narrative_story: string;
  recommended_changes: Array<{ change: string; before_example: string; after_example: string }>;
}

export interface RoadmapItem {
  week: number;
  action: string;
  resource?: string;
  impact: string;
}

export interface InterviewQuestion {
  question: string;
  type: string;
  difficulty: "easy" | "medium" | "hard";
  why_theyll_ask_this: string;
  strong_answer_framework: string;
}

export interface Application {
  id: string;
  company_name: string;
  role_title: string;
  role_category?: string;
  stage: string;
  applied_date?: string;
  application_source: string;
  has_referral: boolean;
  role_fit_score?: number;
  recruiter_fit_score?: number;
  outcome?: string;
  notes?: string;
  priority: "low" | "medium" | "high";
  is_dream_role: boolean;
  days_since_last_event?: number;
  created_at: string;
}

export interface ApplicationEvent {
  id: string;
  event_type: string;
  event_date: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface Insight {
  id: string;
  insight_type: string;
  title: string;
  summary: string;
  detail?: string;
  action?: string;
  impact?: string;
  priority: "critical" | "high" | "medium" | "low";
  is_dismissed: boolean;
  created_at: string;
}

export interface DashboardData {
  career_health_score: number;
  user: Partial<User>;
  pipeline_summary: {
    total: number;
    active: number;
    this_week: number;
    callback_rate: number;
    stage_distribution: Record<string, number>;
  };
  follow_ups: Array<{
    id: string;
    due_date: string;
    follow_up_type: string;
    applications: { company_name: string; role_title: string; stage: string };
  }>;
  insights: Insight[];
  resumes: Resume[];
  recent_applications: Application[];
}

// ── API Client ──────────────────────────────────────────────────────────────

async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    const error = data.error || { code: "UNKNOWN_ERROR", message: "Request failed" };
    if (response.status === 402) {
      // Quota exceeded — throw with upgrade info
      throw new QuotaExceededError(error.message, error.upgrade_url);
    }
    throw new ApiError(response.status, error.code, error.message);
  }

  return data;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class QuotaExceededError extends Error {
  constructor(message: string, public upgradeUrl?: string) {
    super(message);
    this.name = "QuotaExceededError";
  }
}

// ── API Methods ───────────────────────────────────────────────────────────────

export const api = {
  // ── User ──────────────────────────────────────────────────────────────────
  async getMe(token: string) {
    return fetchApi<User>("/users/me", {}, token);
  },

  async updateMe(token: string, data: Partial<User>) {
    return fetchApi<User>("/users/me", { method: "PATCH", body: JSON.stringify(data) }, token);
  },

  // ── Resumes ───────────────────────────────────────────────────────────────
  async listResumes(token: string) {
    return fetchApi<Resume[]>("/resumes", {}, token);
  },

  async deleteResume(token: string, id: string) {
    return fetchApi<{ deleted: boolean }>(`/resumes/${id}`, { method: "DELETE" }, token);
  },

  async setPrimaryResume(token: string, id: string) {
    return fetchApi<Resume>(`/resumes/${id}`, {
      method: "PUT",
      body: JSON.stringify({ is_primary: true }),
    }, token);
  },

  async triggerRewrite(token: string, resumeId: string) {
    return fetchApi<{ job_id: string; status: string; estimated_seconds: number }>(
      `/resumes/${resumeId}/rewrite`,
      { method: "POST" },
      token
    );
  },

  // ── Analyses ──────────────────────────────────────────────────────────────
  async triggerAnalysis(token: string, params: {
    resume_id: string;
    jd_id?: string;
    analysis_types?: string[];
  }) {
    return fetchApi<{ job_id: string; status: string; estimated_seconds: number }>(
      "/analyses",
      { method: "POST", body: JSON.stringify(params) },
      token
    );
  },

  async listAnalyses(token: string, params?: { resume_id?: string; analysis_type?: string }) {
    const qs = params ? `?${new URLSearchParams(params as Record<string, string>)}` : "";
    return fetchApi<Analysis[]>(`/analyses${qs}`, {}, token);
  },

  async getAnalysis(token: string, id: string) {
    return fetchApi<Analysis>(`/analyses/${id}`, {}, token);
  },

  // ── Applications ──────────────────────────────────────────────────────────
  async createApplication(token: string, data: Partial<Application> & {
    company_name: string;
    role_title: string;
  }) {
    return fetchApi<Application>(
      "/applications",
      { method: "POST", body: JSON.stringify(data) },
      token
    );
  },

  async listApplications(token: string, params?: {
    stage?: string;
    source?: string;
    limit?: number;
  }) {
    const qs = params ? `?${new URLSearchParams(Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
    ))}` : "";
    return fetchApi<Application[]>(`/applications${qs}`, {}, token);
  },

  async getApplication(token: string, id: string) {
    return fetchApi<{
      application: Application;
      events: ApplicationEvent[];
      interviews: unknown[];
      follow_ups: unknown[];
    }>(`/applications/${id}`, {}, token);
  },

  async updateApplication(token: string, id: string, data: Partial<Application>) {
    return fetchApi<Application>(
      `/applications/${id}`,
      { method: "PATCH", body: JSON.stringify(data) },
      token
    );
  },

  async addEvent(token: string, applicationId: string, event: {
    event_type: string;
    description?: string;
    metadata?: Record<string, unknown>;
  }) {
    return fetchApi<ApplicationEvent>(
      `/applications/${applicationId}/events`,
      { method: "POST", body: JSON.stringify(event) },
      token
    );
  },

  // ── Dashboard ─────────────────────────────────────────────────────────────
  async getDashboard(token: string) {
    return fetchApi<DashboardData>("/dashboard", {}, token);
  },

  async getPipelineDashboard(token: string) {
    return fetchApi<unknown>("/dashboard/pipeline", {}, token);
  },

  async getAnalyticsDashboard(token: string) {
    return fetchApi<unknown>("/dashboard/analytics", {}, token);
  },

  async getRecruiterDashboard(token: string) {
    return fetchApi<unknown>("/dashboard/recruiter", {}, token);
  },

  // ── Insights ──────────────────────────────────────────────────────────────
  async listInsights(token: string) {
    return fetchApi<Insight[]>("/insights", {}, token);
  },

  async dismissInsight(token: string, id: string) {
    return fetchApi<Insight>(`/insights/${id}/dismiss`, { method: "POST" }, token);
  },

  async generateInsights(token: string) {
    return fetchApi<{ status: string; message: string }>("/insights/generate", { method: "POST" }, token);
  },
};
