// src/lib/api/endpoints.ts — Typed API endpoint functions

import apiClient from "./client";
import type {
  ApiResponse,
  PaginatedResponse,
  AuthTokens,
  User,
  UserProfile,
  Scheme,
  Conversation,
  Message,
  GovDocument,
  EligibilityCheckResponse,
  DashboardStats,
  RAGMetrics,
} from "@/types";

// ─────────────────────────────────────────────
// Auth API
// ─────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; password_confirm: string }) =>
    apiClient.post<ApiResponse<AuthTokens>>("/auth/register/", data),

  login: (data: { email: string; password: string }) =>
    apiClient.post<ApiResponse<AuthTokens>>("/auth/login/", data),

  logout: (refresh_token: string) =>
    apiClient.post<ApiResponse>("/auth/logout/", { refresh_token }),

  refresh: (refresh_token: string) =>
    apiClient.post<ApiResponse<{ access_token: string; refresh_token: string }>>("/auth/refresh/", { refresh_token }),

  me: () => apiClient.get<ApiResponse<User>>("/auth/me/"),

  verifyEmail: (data: { email: string; otp_code: string }) =>
    apiClient.post<ApiResponse>("/auth/verify-email/", data),

  resendVerification: (email: string) =>
    apiClient.post<ApiResponse>("/auth/resend-verification/", { email }),

  forgotPassword: (email: string) =>
    apiClient.post<ApiResponse>("/auth/forgot-password/", { email }),

  resetPassword: (data: { email: string; otp_code: string; new_password: string; new_password_confirm: string }) =>
    apiClient.post<ApiResponse>("/auth/reset-password/", data),

  changePassword: (data: { current_password: string; new_password: string; new_password_confirm: string }) =>
    apiClient.post<ApiResponse>("/auth/change-password/", data),
};

// ─────────────────────────────────────────────
// User Profile API
// ─────────────────────────────────────────────
export const profileApi = {
  getMyProfile: () => apiClient.get<ApiResponse<UserProfile>>("/users/me/profile/"),

  updateMyProfile: (data: Partial<UserProfile>) =>
    apiClient.patch<ApiResponse<UserProfile>>("/users/me/profile/", data),

  listUsers: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<User>>("/users/", { params }),

  getUserDetail: (userId: string) => apiClient.get<ApiResponse<User>>(`/users/${userId}/`),

  changeUserRole: (userId: string, role: string) =>
    apiClient.patch<ApiResponse<User>>(`/users/${userId}/role/`, { role }),
};

// ─────────────────────────────────────────────
// Schemes API
// ─────────────────────────────────────────────
export const schemesApi = {
  listSchemes: (params?: {
    category?: string;
    ministry?: string;
    state?: string;
    scheme_type?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => apiClient.get<PaginatedResponse<Scheme>>("/schemes/", { params }),

  getScheme: (id: string) => apiClient.get<ApiResponse<Scheme>>(`/schemes/${id}/`),

  getSchemeBySlug: (slug: string) => apiClient.get<ApiResponse<Scheme>>(`/schemes/by-slug/${slug}/`),

  getCategories: () => apiClient.get<Array<{ id: string; name: string; slug: string; icon: string; schemes_count?: number }>>("/schemes/categories/"),

  getStates: () => apiClient.get<Array<{ id: string; code: string; name: string; is_union_territory: boolean }>>("/schemes/states/"),

  getMinistries: () => apiClient.get<Array<{ id: string; name: string; short_code: string; is_central: boolean }>>("/schemes/ministries/"),

  getStats: () => apiClient.get<ApiResponse<{ total_schemes: number; active_schemes: number; central_schemes: number; state_schemes: number; total_categories: number; total_ministries: number }>>("/schemes/stats/"),

  createScheme: (data: Record<string, any>) => apiClient.post<ApiResponse<Scheme>>("/schemes/", data),

  updateScheme: (id: string, data: Record<string, any>) => apiClient.patch<ApiResponse<Scheme>>(`/schemes/${id}/`, data),

  deleteScheme: (id: string) => apiClient.delete<ApiResponse>(`/schemes/${id}/`),

  createEligibilityRule: (data: Record<string, any>) => apiClient.post<ApiResponse>("/schemes/eligibility-rules/", data),

  deleteEligibilityRule: (ruleId: string) => apiClient.delete<ApiResponse>(`/schemes/eligibility-rules/${ruleId}/`),
};

// ─────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────
export const chatApi = {
  listConversations: () => apiClient.get<ApiResponse<Conversation[]>>("/chat/conversations/"),

  createConversation: () => apiClient.post<ApiResponse<Conversation>>("/chat/conversations/"),

  getConversation: (id: string) => apiClient.get<ApiResponse<Conversation>>(`/chat/conversations/${id}/`),

  deleteConversation: (id: string) => apiClient.delete<ApiResponse>(`/chat/conversations/${id}/`),

  sendFeedback: (messageId: string, data: { rating: number; feedback_type?: string; comment?: string }) =>
    apiClient.post<ApiResponse>(`/chat/messages/${messageId}/feedback/`, data),
};

// ─────────────────────────────────────────────
// Documents API (Admin)
// ─────────────────────────────────────────────
export const documentsApi = {
  upload: (formData: FormData) =>
    apiClient.post<ApiResponse<GovDocument>>("/documents/upload/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  listDocuments: (params?: { status?: string; category?: string; page?: number }) =>
    apiClient.get<PaginatedResponse<GovDocument>>("/documents/", { params }),

  getDocument: (id: string) => apiClient.get<ApiResponse<GovDocument>>(`/documents/${id}/`),

  getDocumentStatus: (id: string) => apiClient.get<ApiResponse>(`/documents/${id}/status/`),

  deleteDocument: (id: string) => apiClient.delete<ApiResponse>(`/documents/${id}/`),

  reprocessDocument: (id: string) => apiClient.post<ApiResponse>(`/documents/${id}/reprocess/`),

  getDocumentChunks: (id: string, params?: { page?: number; page_size?: number }) =>
    apiClient.get<ApiResponse>(`/documents/${id}/chunks/`, { params }),

  listGlobalChunks: (params?: { search?: string; document?: string; chunk_type?: string; page?: number }) =>
    apiClient.get<ApiResponse>("/documents/chunks/", { params }),
};

// ─────────────────────────────────────────────
// Eligibility API
// ─────────────────────────────────────────────
export const eligibilityApi = {
  checkEligibility: (data?: { category?: string; state?: string }) =>
    apiClient.post<ApiResponse<any>>("/eligibility/check/", data || {}),

  getResults: () => apiClient.get<ApiResponse<any>>("/eligibility/results/"),

  checkForScheme: (schemeId: string) =>
    apiClient.get<ApiResponse<any>>(`/eligibility/schemes/${schemeId}/`),

  evaluateArbitraryProfile: (payload: { profile: Record<string, any>; scheme_id?: string }) =>
    apiClient.post<ApiResponse<any>>("/eligibility/evaluate/", payload),
};

export const userApi = profileApi;

// ─────────────────────────────────────────────
// Analytics API (Admin)
// ─────────────────────────────────────────────
export const analyticsApi = {
  getDashboard: () => apiClient.get<ApiResponse<DashboardStats>>("/analytics/dashboard/"),

  getRAGMetrics: () => apiClient.get<ApiResponse<RAGMetrics>>("/analytics/rag-metrics/"),

  getQueryLogs: (params?: { search?: string; query_type?: string; failed_only?: string }) =>
    apiClient.get<ApiResponse>("/analytics/query-logs/", { params }),
};

// ─────────────────────────────────────────────
// Admin Users API
// ─────────────────────────────────────────────
export const usersAdminApi = {
  listUsers: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<ApiResponse>("/users/", { params }),

  getUser: (userId: string) => apiClient.get<ApiResponse>(`/users/${userId}/`),

  changeRole: (userId: string, role: string) =>
    apiClient.patch<ApiResponse>(`/users/${userId}/role/`, { role }),

  deactivateUser: (userId: string) =>
    apiClient.post<ApiResponse>(`/users/${userId}/deactivate/`),
};

// ─────────────────────────────────────────────
// RAG Evaluation API (Admin)
// ─────────────────────────────────────────────
export const evaluationApi = {
  // Datasets
  listDatasets: () =>
    apiClient.get<ApiResponse<any[]>>("/evaluation/datasets/"),

  getDataset: (id: string) =>
    apiClient.get<ApiResponse<any>>(`/evaluation/datasets/${id}/`),

  createDataset: (data: { name: string; description?: string; version?: string }) =>
    apiClient.post<ApiResponse<any>>("/evaluation/datasets/", data),

  listCases: (datasetId: string) =>
    apiClient.get<ApiResponse<any[]>>(`/evaluation/datasets/${datasetId}/cases/`),

  createCase: (datasetId: string, data: Record<string, any>) =>
    apiClient.post<ApiResponse<any>>(`/evaluation/datasets/${datasetId}/cases/`, data),

  deleteCase: (datasetId: string, caseId: string) =>
    apiClient.delete<ApiResponse>(`/evaluation/datasets/${datasetId}/cases/${caseId}/`),

  // Runs
  listRuns: () =>
    apiClient.get<ApiResponse<any[]>>("/evaluation/runs/"),

  getRunDetail: (runId: string) =>
    apiClient.get<ApiResponse<any>>(`/evaluation/runs/${runId}/`),

  triggerRun: (payload: {
    dataset_id: string;
    label?: string;
    embedding_model?: string;
    chunk_size?: number;
    chunk_overlap?: number;
    top_k_retrieve?: number;
    top_k_rerank?: number;
    use_reranker?: boolean;
    retrieval_strategy?: string;
  }) => apiClient.post<ApiResponse<any>>("/evaluation/runs/", payload),

  compareRuns: (runId: string, otherId: string) =>
    apiClient.get<ApiResponse<any>>(`/evaluation/runs/${runId}/compare/${otherId}/`),
};


