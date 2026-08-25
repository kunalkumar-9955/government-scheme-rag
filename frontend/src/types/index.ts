// src/types/index.ts — Global TypeScript type definitions

// ─────────────────────────────────────────────
// Auth Types
// ─────────────────────────────────────────────
export type UserRole = "CITIZEN" | "ADMIN" | "SUPER_ADMIN";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_email_verified: boolean;
  date_joined?: string;
  last_login?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  password_confirm: string;
}

// ─────────────────────────────────────────────
// User Profile Types
// ─────────────────────────────────────────────
export interface UserProfile {
  id: string;
  user_email: string;
  full_name: string;
  date_of_birth: string | null;
  gender: "MALE" | "FEMALE" | "OTHER" | "";
  age: number | null;
  state: string;
  state_display: string;
  district: string;
  pincode: string;
  is_urban: boolean | null;
  social_category: "GENERAL" | "OBC" | "SC" | "ST" | "EWS" | "";
  annual_income: number | null;
  is_bpl: boolean;
  has_ration_card: boolean;
  ration_card_type: "APL" | "BPL" | "AAY" | "";
  occupation: string;
  education_level: string;
  is_student: boolean;
  has_disability: boolean;
  disability_percentage: number | null;
  is_ex_serviceman: boolean;
  is_minority: boolean;
  is_widow: boolean;
  is_single_girl_child?: boolean;
  land_holding_acres: number | null;
  is_marginal_farmer: boolean;
  family_size: number | null;
  number_of_children: number | null;
  profile_completion_score: number;
  created_at: string;
  updated_at: string;
}

// ─────────────────────────────────────────────
// Scheme Data Management Types
// ─────────────────────────────────────────────
export interface State {
  id: string;
  code: string;
  name: string;
  is_union_territory: boolean;
  official_portal_url: string;
}

export interface Department {
  id: string;
  ministry: string;
  name: string;
  short_code: string;
  website_url: string;
}

export interface Ministry {
  id: string;
  name: string;
  short_code: string;
  website_url: string;
  is_central: boolean;
  state?: string;
  state_code?: string;
  state_name?: string;
  departments?: Department[];
}

export interface SchemeCategory {
  id: string;
  name: string;
  slug: string;
  icon: string;
  description: string;
  schemes_count?: number;
}

export interface SchemeEligibilityRule {
  id: string;
  scheme: string;
  rule_group: number;
  criterion_key: string;
  operator: string;
  operator_display?: string;
  value: string;
  min_value?: string | null;
  max_value?: string | null;
  data_type: string;
  data_type_display?: string;
  is_mandatory: boolean;
  disqualification_condition: boolean;
  rule_description: string;
  order: number;
}

export interface SchemeBenefit {
  id: string;
  scheme: string;
  benefit_type: string;
  benefit_type_display?: string;
  title: string;
  description: string;
  amount?: number | string | null;
  currency: string;
  disbursement_frequency: string;
  disbursement_frequency_display?: string;
  order: number;
}

export interface RequiredDocument {
  id: string;
  scheme: string;
  document_name: string;
  document_type: string;
  document_type_display?: string;
  is_mandatory: boolean;
  description: string;
  issuing_authority: string;
  accepted_formats: string;
  order: number;
}

export interface ApplicationProcedure {
  id: string;
  scheme: string;
  mode: string;
  mode_display?: string;
  step_number: number;
  title: string;
  description: string;
  portal_url: string;
  office_name: string;
  processing_time_days?: number | null;
  fee_inr: number | string;
}

export interface SchemeSource {
  id: string;
  scheme: string;
  source_type: string;
  source_type_display?: string;
  title: string;
  url: string;
  document_reference_number: string;
  published_date?: string | null;
  is_verified: boolean;
  retrieved_at: string;
}

export interface SchemeVersion {
  id: string;
  scheme: string;
  version_number: string;
  change_summary: string;
  effective_from: string;
  effective_to?: string | null;
  snapshot_data: Record<string, any>;
  created_by?: string | null;
  created_by_email?: string | null;
  created_at: string;
}

export interface GovernmentScheme {
  id: string;
  name: string;
  slug: string;
  short_title: string;
  description: string;
  scheme_type: string;
  scheme_type_display?: string;
  ministry?: string | null;
  ministry_name?: string;
  ministry_code?: string;
  ministry_details?: Ministry;
  department?: string | null;
  department_details?: Department;
  category?: string | null;
  category_name?: string;
  category_icon?: string;
  category_details?: SchemeCategory;
  state?: string | null;
  state_name?: string;
  state_code?: string;
  state_details?: State;
  target_beneficiaries: string;
  status: "ACTIVE" | "INACTIVE" | "UPCOMING" | "DISCONTINUED" | "MERGED";
  status_display?: string;
  version: string;
  launch_date?: string | null;
  valid_upto?: string | null;
  important_dates?: Record<string, string>;
  official_application_url: string;
  official_source_url: string;
  funding_pattern?: string;
  helpline_number?: string;
  tags: string[];
  eligibility_rules?: SchemeEligibilityRule[];
  eligibility_rules_count?: number;
  benefits?: SchemeBenefit[];
  benefits_count?: number;
  required_documents?: RequiredDocument[];
  required_documents_count?: number;
  application_steps?: ApplicationProcedure[];
  sources?: SchemeSource[];
  versions?: SchemeVersion[];
  last_updated_at?: string;
  created_at?: string;
}

// Backward-compatible alias
export type Scheme = GovernmentScheme;
export type EligibilityCriteria = SchemeEligibilityRule;

// ─────────────────────────────────────────────
// Chat Types
// ─────────────────────────────────────────────
export interface Citation {
  citation_number: number;
  scheme_name: string;
  document_name: string;
  page_number: number | null;
  section: string;
  source_url: string;
  document_version: string;
  ministry?: string;
  department?: string;
  state?: string;
  category?: string;
  snippet?: string;
  relevance_score?: number;
  chunk_id?: string;
  document_id?: string;
  document_title?: string;
  chunk_type?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  cited_sources: Citation[];
  query_type: string;
  confidence_score: number | null;
  latency_ms: number | null;
  feedback_rating: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  message_count: number;
  last_message_at: string | null;
  last_message_preview?: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

// ─────────────────────────────────────────────
// Document Types (Admin)
// ─────────────────────────────────────────────
export type DocumentStatus =
  | "PENDING"
  | "PROCESSING"
  | "CHUNKING"
  | "EMBEDDING"
  | "EXTRACTING"
  | "COMPLETED"
  | "FAILED";

export interface GovDocument {
  id: string;
  title: string;
  ministry: string;
  department: string;
  category: string;
  category_display: string;
  status: DocumentStatus;
  status_display: string;
  total_chunks: number;
  file_name: string;
  file_size_bytes: number;
  uploaded_at: string;
  processed_at: string | null;
  processing_error: string;
  is_processed: boolean;
  can_reprocess: boolean;
  uploaded_by_email: string;
}

// ─────────────────────────────────────────────
// Eligibility Types
// ─────────────────────────────────────────────
export type EligibilityVerdict =
  | "ELIGIBLE"
  | "LIKELY_ELIGIBLE"
  | "LIKELY_INELIGIBLE"
  | "INELIGIBLE"
  | "CANNOT_DETERMINE";

export interface EligibilityResult {
  scheme_id: string;
  scheme_name: string;
  ministry: string;
  category: string;
  verdict: EligibilityVerdict;
  is_eligible: boolean | null;
  confidence: number;
  matched_criteria: Array<{ key: string; required: string; user_value: string }>;
  unmatched_criteria: Array<{ key: string; required: string; user_value: string; is_mandatory: boolean }>;
  missing_info: string[];
  explanation: string;
}

export interface EligibilityCheckResponse {
  total_schemes_checked: number;
  eligible_count: number;
  profile_completion: number;
  results: EligibilityResult[];
}

// ─────────────────────────────────────────────
// Analytics Types (Admin)
// ─────────────────────────────────────────────
export interface DashboardStats {
  total_users: number;
  total_conversations: number;
  total_messages: number;
  total_documents: number;
  total_documents_indexed: number;
  total_schemes: number;
  avg_confidence_score: number | null;
  avg_latency_ms: number | null;
  failed_queries: number;
  positive_feedback: number;
  negative_feedback: number;
}

export interface RAGMetrics {
  avg_faithfulness: number | null;
  avg_answer_relevancy: number | null;
  avg_context_precision: number | null;
  avg_context_recall: number | null;
  total_evaluated: number;
}

// ─────────────────────────────────────────────
// API Response Wrappers
// ─────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, string[]>;
  };
}

export interface PaginatedResponse<T> {
  success: boolean;
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ─────────────────────────────────────────────
// SSE Event Types
// ─────────────────────────────────────────────
export interface SSEStatusEvent {
  stage: "retrieving" | "generating" | "no_context";
  message?: string;
}

export interface SSETokenEvent {
  text: string;
}

export interface SSECitationsEvent {
  citations: Citation[];
}

export interface SSEDoneEvent {
  citations: Citation[];
  confidence_score: number;
  latency_ms: number;
  query_type: string;
  full_answer: string;
}

// ─────────────────────────────────────────────
// Evaluation System Types (Admin)
// ─────────────────────────────────────────────
export interface EvaluationDataset {
  id: string;
  name: string;
  description: string;
  version: string;
  is_active: boolean;
  total_cases: number;
  total_runs: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluationCase {
  id: string;
  dataset: string;
  question: string;
  expected_document_ids: string[];
  expected_evidence: string;
  expected_answer_keywords: string[];
  scheme_id?: string | null;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  category: string;
  notes: string;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  dataset: string;
  dataset_name?: string;
  label: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  embedding_model: string;
  chunk_size: number;
  top_k_retrieve: number;
  top_k_rerank: number;
  use_reranker: boolean;
  retrieval_strategy: string;
  total_cases: number;
  completed_cases: number;
  avg_retrieval_relevance: number | null;
  avg_context_relevance: number | null;
  avg_answer_relevance: number | null;
  avg_faithfulness: number | null;
  avg_citation_correctness: number | null;
  avg_hallucination_score: number | null;
  duration_seconds: number | null;
  pass_rate: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface EvaluationCaseResult {
  id: string;
  case: string;
  question: string;
  difficulty: string;
  category: string;
  retrieval_relevance: number | null;
  context_relevance: number | null;
  answer_relevance: number | null;
  faithfulness: number | null;
  citation_correctness: number | null;
  hallucination_score: number | null;
  retrieved_chunk_ids: string[];
  retrieved_document_ids: string[];
  num_chunks_retrieved: number;
  actual_answer: string;
  actual_citations: any[];
  faithfulness_breakdown: Array<{ sentence: string; supported: boolean; best_overlap: number }>;
  error_message: string;
  latency_ms: number | null;
  created_at: string;
}

export interface EvaluationRunDetail extends EvaluationRun {
  case_results: EvaluationCaseResult[];
  config_snapshot: Record<string, any>;
  error_message: string;
}

export interface EvaluationComparison {
  run_a: EvaluationRun;
  run_b: EvaluationRun;
  deltas: Record<string, number | null>;
  winner: Record<string, string>;
}

export interface SSEErrorEvent {
  error: string;
}
