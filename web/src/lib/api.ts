import axios, { AxiosError, type AxiosRequestConfig } from "axios";

// Single-origin in dev (Vite proxies /api) and prod (nginx proxies /api).
const api = axios.create({ baseURL: "/api/v1", withCredentials: true });

// Access token lives in memory only. Refresh token is an httpOnly cookie.
let accessToken: string | null = null;
export function setAccessToken(token: string | null) {
  accessToken = token;
}
export function getAccessToken() {
  return accessToken;
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// On 401, try one silent refresh via the cookie, then replay the request.
let refreshing: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  try {
    const resp = await axios.post(
      "/api/v1/auth/refresh",
      {},
      { withCredentials: true }
    );
    const token = resp.data?.access_token ?? null;
    setAccessToken(token);
    return token;
  } catch {
    setAccessToken(null);
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retried?: boolean };
    const status = error.response?.status;
    const isAuthCall = original?.url?.includes("/auth/");
    if (status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      refreshing = refreshing ?? doRefresh();
      const token = await refreshing;
      refreshing = null;
      if (token) {
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>).Authorization = `Bearer ${token}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

export function apiErrorMessage(err: unknown): string {
  const e = err as AxiosError<{ error?: { message?: string }; detail?: string }>;
  return (
    e.response?.data?.error?.message ||
    e.response?.data?.detail ||
    e.message ||
    "Request failed"
  );
}

export default api;
