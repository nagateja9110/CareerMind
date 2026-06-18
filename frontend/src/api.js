import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
});

export function setAccessToken(token) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

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
