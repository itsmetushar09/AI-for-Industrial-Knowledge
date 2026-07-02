export const API_BASE = import.meta.env.VITE_API_BASE || "/api";
export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "";
export const SUPABASE_PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";
export const SUPABASE_AUTH_BASE = SUPABASE_URL ? `${SUPABASE_URL.replace(/\/$/, "")}/auth/v1` : "";

export const ENDPOINTS = {
  login: "/auth/login",
  register: "/auth/register",
  forgot: "/auth/forgot",
  otp: "/auth/otp",
  reset: "/auth/reset",
  me: "/auth/me",
  dashboard: "/dashboard",
  documents: "/documents",
  upload: "/upload",
  chatHistory: "/chat/history",
  chat: "/chat",
  analytics: "/analytics",
  compliance: "/compliance",
  maintenance: "/maintenance",
  graph: "/graph",
  users: "/users",
} as const;

export const APP_NAME = "INDUS AI";
export const APP_TAGLINE = "Industrial Knowledge Intelligence Platform";
