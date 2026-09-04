// src/lib/api/client.ts
// Axios instance with JWT interceptors + reusable token refresh

import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000/api/v1";

// ============================================================
// Token Storage
// ============================================================

const ACCESS_TOKEN_KEY = "govscheme_access_token";
const REFRESH_TOKEN_KEY = "govscheme_refresh_token";

export const tokenStorage = {
  getAccess: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefresh: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  set: (access: string, refresh: string): void => {
    if (typeof window === "undefined") return;

    localStorage.setItem(
      ACCESS_TOKEN_KEY,
      access
    );

    localStorage.setItem(
      REFRESH_TOKEN_KEY,
      refresh
    );
  },

  clear: (): void => {
    if (typeof window === "undefined") return;

    localStorage.removeItem(
      ACCESS_TOKEN_KEY
    );

    localStorage.removeItem(
      REFRESH_TOKEN_KEY
    );
  },
};

// ============================================================
// Axios Instance
// ============================================================

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
});

// ============================================================
// Shared Refresh State
// ============================================================

let refreshPromise: Promise<string> | null = null;

// ============================================================
// Refresh Access Token
// IMPORTANT:
// This function can be used by both Axios and native fetch()
// ============================================================

export const refreshAccessToken =
  async (): Promise<string> => {
    // If another refresh is already running,
    // wait for that same refresh.
    if (refreshPromise) {
      return refreshPromise;
    }

    const refreshToken =
      tokenStorage.getRefresh();

    if (!refreshToken) {
      tokenStorage.clear();

      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }

      throw new Error(
        "No refresh token available"
      );
    }

    refreshPromise = (async () => {
      try {
        const response =
          await axios.post(
            `${API_BASE_URL}/auth/refresh/`,
            {
              refresh_token:
                refreshToken,
            }
          );

        const data =
          response?.data?.data;

        const accessToken =
          data?.access_token;

        const newRefreshToken =
          data?.refresh_token ||
          refreshToken;

        if (!accessToken) {
          throw new Error(
            "Refresh endpoint did not return access_token"
          );
        }

        tokenStorage.set(
          accessToken,
          newRefreshToken
        );

        return accessToken;
      } catch (error) {
        console.error(
          "Token refresh failed:",
          error
        );

        tokenStorage.clear();

        if (
          typeof window !== "undefined"
        ) {
          window.location.href =
            "/login";
        }

        throw error;
      } finally {
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  };

// ============================================================
// Request Interceptor
// ============================================================

apiClient.interceptors.request.use(
  (
    config: InternalAxiosRequestConfig
  ) => {
    const token =
      tokenStorage.getAccess();

    if (
      token &&
      config.headers
    ) {
      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },
  (error) =>
    Promise.reject(error)
);

// ============================================================
// Response Interceptor
// ============================================================

apiClient.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const originalRequest =
      error.config as
        | (InternalAxiosRequestConfig & {
            _retry?: boolean;
          })
        | undefined;

    // No request config available
    if (!originalRequest) {
      return Promise.reject(error);
    }

    // Only handle 401
    if (
      error.response?.status !== 401 ||
      originalRequest._retry
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      // Get a fresh token.
      // If another request is refreshing,
      // this waits for the same Promise.
      const newAccessToken =
        await refreshAccessToken();

      if (
        originalRequest.headers
      ) {
        originalRequest.headers.Authorization =
          `Bearer ${newAccessToken}`;
      }

      return apiClient(
        originalRequest
      );
    } catch (refreshError) {
      return Promise.reject(
        refreshError
      );
    }
  }
);

export default apiClient;