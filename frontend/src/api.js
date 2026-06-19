import axios from "axios";

const ACCESS_TOKEN_KEY = "careermind_access_token";
const REFRESH_TOKEN_KEY = "careermind_refresh_token";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
});

let onAuthFailure = null;
let refreshPromise = null;

function applyAuthHeader(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export function setOnAuthFailure(callback) {
  onAuthFailure = callback;
}

export function getStoredAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY) ?? "";
}

export function setSession(tokens) {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  applyAuthHeader(tokens.access_token);
}

export function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  applyAuthHeader("");
}

// Apply whatever was persisted from a previous session before the first request goes out.
applyAuthHeader(getStoredAccessToken());

// A 401 on any authenticated request triggers a single refresh attempt (de-duplicated
// across concurrent requests) before falling back to a forced logout, so an expired
// 60-minute access token doesn't kick the user out while their refresh token is still valid.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const isAuthEndpoint = ["/auth/login", "/auth/register", "/auth/refresh"].some((path) =>
      config?.url?.includes(path),
    );

    if (!config || response?.status !== 401 || isAuthEndpoint || config._retriedAfterRefresh) {
      throw error;
    }

    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      onAuthFailure?.();
      throw error;
    }

    config._retriedAfterRefresh = true;

    try {
      if (!refreshPromise) {
        refreshPromise = api
          .post("/auth/refresh", { refresh_token: refreshToken })
          .then((res) => res.data)
          .finally(() => {
            refreshPromise = null;
          });
      }
      const authResponse = await refreshPromise;
      setSession(authResponse.tokens);
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${authResponse.tokens.access_token}`;
      return api(config);
    } catch {
      clearSession();
      onAuthFailure?.();
      throw error;
    }
  },
);

export async function register(payload) {
  const response = await api.post("/auth/register", payload);
  return response.data;
}

export async function login(payload) {
  const response = await api.post("/auth/login", payload);
  return response.data;
}

export async function fetchProfile() {
  const response = await api.get("/auth/me");
  return response.data;
}

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/resume/upload", formData);
  return response.data;
}

export async function fetchResume() {
  const response = await api.get("/resume");
  return response.data;
}

export async function fetchChatHistory() {
  const response = await api.get("/chat/history");
  return response.data;
}

export async function fetchChatThread(chatId) {
  const response = await api.get(`/chat/${chatId}`);
  return response.data;
}

export async function sendChatMessage(payload) {
  const response = await api.post("/chat", payload);
  return response.data;
}

export async function searchJobs({ role, location, skills }) {
  const params = new URLSearchParams();
  if (role) {
    params.set("role", role);
  }
  if (location) {
    params.set("location", location);
  }
  skills.filter(Boolean).forEach((skill) => {
    params.append("skills", skill);
  });

  const response = await api.get(`/jobs/search?${params.toString()}`);
  return response.data;
}
