import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("tdrive_csrf_token");
    if (token) {
      config.headers["X-CSRF-Token"] = token;
    }
    
    const sessionToken = localStorage.getItem("tdrive_session_token");
    if (sessionToken) {
      config.headers["Authorization"] = `Bearer ${sessionToken}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        if (window.location.pathname !== "/login") {
           console.warn("Session invalid, clearing state and redirecting to login");
           localStorage.removeItem("tdrive_session_token");
           localStorage.removeItem("tdrive_csrf_token");
           window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);
