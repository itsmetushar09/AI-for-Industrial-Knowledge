import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { API_BASE, ENDPOINTS, SUPABASE_AUTH_BASE, SUPABASE_PUBLISHABLE_KEY } from "@/constants/api";
import type {
  ChatMessage,
  ComplianceItem,
  Conversation,
  DocumentItem,
  GraphEdge,
  GraphNode,
  MaintenanceTask,
  Role,
  User,
} from "@/types";

const ACCESS_TOKEN_KEY = "indus-access-token";
const REFRESH_TOKEN_KEY = "indus-refresh-token";
const RECOVERY_EMAIL_KEY = "indus-recovery-email";

interface SupabaseUser {
  id: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
}

interface SupabaseSessionResponse {
  access_token?: string;
  refresh_token?: string;
  user: SupabaseUser;
}

interface BackendDocument {
  id: string;
  name: string;
  mime_type: string;
  size_bytes: number;
  status: "queued" | "processing" | "indexed" | "failed";
  department_id: string | null;
  created_at: string;
}

interface DocumentListResponse {
  items: BackendDocument[];
  total: number;
}

interface BackendCitation {
  document: string;
  page: number;
  score: number;
}

interface BackendChatResponse {
  answer: string;
  confidence: number;
  citations: BackendCitation[];
  conversation_id: string;
}

interface BackendHistoryMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: BackendCitation[];
  created_at: string;
}

interface BackendConversation {
  id: string;
  title: string;
  updated_at: string;
  messages: BackendHistoryMessage[];
}

interface BackendAnalytics {
  total_documents: number;
  total_uploads: number;
  total_ai_questions: number;
  storage_usage_bytes: number;
  top_departments: Array<{
    department_id: string;
    department: string;
    documents: number;
    storage_bytes: number;
  }>;
  upload_trends: Array<{ date: string; uploads: number; bytes: number }>;
  ai_usage: Array<{ date: string; questions: number }>;
}

interface CurrentUserResponse {
  id: string;
  name: string;
  email: string | null;
  role: "administrator" | "plant_manager" | "maintenance_engineer" | "safety_officer" | "operator";
  department_id: string | null;
}

function browserStorage(): Storage | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

function requireSupabaseConfiguration(): void {
  if (!SUPABASE_AUTH_BASE || !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error(
      "Supabase frontend configuration is missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.",
    );
  }
}

function persistSession(session: SupabaseSessionResponse): void {
  const storage = browserStorage();
  if (!storage) return;
  if (session.access_token) storage.setItem(ACCESS_TOKEN_KEY, session.access_token);
  if (session.refresh_token) storage.setItem(REFRESH_TOKEN_KEY, session.refresh_token);
}

function clearSession(): void {
  const storage = browserStorage();
  storage?.removeItem(ACCESS_TOKEN_KEY);
  storage?.removeItem(REFRESH_TOKEN_KEY);
  storage?.removeItem("indus-user");
}

function normalizedRole(value: unknown): Role {
  const roles: Record<string, Role> = {
    administrator: "Administrator",
    "plant manager": "Plant Manager",
    plant_manager: "Plant Manager",
    "maintenance engineer": "Maintenance Engineer",
    maintenance_engineer: "Maintenance Engineer",
    "safety officer": "Safety Officer",
    safety_officer: "Safety Officer",
    operator: "Operator",
  };
  return roles[String(value ?? "operator").toLowerCase()] ?? "Operator";
}

function toUser(user: SupabaseUser): User {
  const metadata = user.user_metadata ?? {};
  return {
    id: user.id,
    name: String(metadata.full_name ?? metadata.name ?? user.email ?? "INDUS User"),
    email: user.email ?? "",
    role: normalizedRole(metadata.role),
    avatar: typeof metadata.avatar_url === "string" ? metadata.avatar_url : undefined,
    department: typeof metadata.department === "string" ? metadata.department : undefined,
  };
}

function toCurrentUser(user: CurrentUserResponse): User {
  return {
    id: user.id,
    name: user.name,
    email: user.email ?? "",
    role: normalizedRole(user.role),
    department: user.department_id ?? undefined,
  };
}

function humanFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function toDocument(document: BackendDocument): DocumentItem {
  const statuses: Record<BackendDocument["status"], DocumentItem["status"]> = {
    queued: "Uploading",
    processing: "Processing",
    indexed: "Indexed",
    failed: "Failed",
  };
  return {
    id: document.id,
    name: document.name,
    department: document.department_id ?? "Unassigned",
    type: "PDF",
    status: statuses[document.status],
    uploadedBy: "Authenticated user",
    date: document.created_at.slice(0, 10),
    size: humanFileSize(document.size_bytes),
    tags: [],
  };
}

function toChatMessage(message: BackendHistoryMessage): ChatMessage | null {
  if (message.role === "system") return null;
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations.map((citation) => ({
      doc: citation.document,
      page: citation.page,
    })),
    createdAt: message.created_at,
  };
}

const supabaseClient = axios.create({
  baseURL: SUPABASE_AUTH_BASE || undefined,
  headers: SUPABASE_PUBLISHABLE_KEY ? { apikey: SUPABASE_PUBLISHABLE_KEY } : undefined,
});

export const apiClient = axios.create({ baseURL: API_BASE });

apiClient.interceptors.request.use((config) => {
  const token = browserStorage()?.getItem(ACCESS_TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshRequest: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshRequest) return refreshRequest;
  refreshRequest = (async () => {
    requireSupabaseConfiguration();
    const refreshToken = browserStorage()?.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) throw new Error("Your session has expired. Please sign in again.");
    const { data } = await supabaseClient.post<SupabaseSessionResponse>(
      "/token?grant_type=refresh_token",
      { refresh_token: refreshToken },
    );
    persistSession(data);
    if (!data.access_token) throw new Error("Supabase did not return an access token.");
    return data.access_token;
  })().finally(() => {
    refreshRequest = null;
  });
  return refreshRequest;
}

apiClient.interceptors.response.use(undefined, async (error: AxiosError) => {
  const request = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
  if (error.response?.status !== 401 || !request || request._retry) throw error;
  request._retry = true;
  request.headers.Authorization = `Bearer ${await refreshAccessToken()}`;
  return apiClient.request(request);
});

async function fetchDocuments(): Promise<DocumentListResponse> {
  const { data } = await apiClient.get<DocumentListResponse>(ENDPOINTS.documents, {
    params: { page: 1, page_size: 100 },
  });
  return data;
}

async function fetchAnalytics(): Promise<BackendAnalytics> {
  const { data } = await apiClient.get<BackendAnalytics>(ENDPOINTS.analytics);
  return data;
}

export const api = {
  login: async (email: string, password: string) => {
    requireSupabaseConfiguration();
    const { data } = await supabaseClient.post<SupabaseSessionResponse>(
      "/token?grant_type=password",
      { email, password },
    );
    persistSession(data);
    const { data: profile } = await apiClient.get<CurrentUserResponse>(ENDPOINTS.me);
    return { token: data.access_token ?? "", user: toCurrentUser(profile) };
  },

  register: async (name: string, email: string, password: string) => {
    requireSupabaseConfiguration();
    const { data } = await supabaseClient.post<SupabaseSessionResponse>("/signup", {
      email,
      password,
      data: { full_name: name },
    });
    persistSession(data);
    const requiresConfirmation = !data.access_token;
    const user = requiresConfirmation
      ? toUser(data.user ?? { id: email, email, user_metadata: { full_name: name } })
      : toCurrentUser((await apiClient.get<CurrentUserResponse>(ENDPOINTS.me)).data);
    return { token: data.access_token ?? "", user, requiresConfirmation };
  },

  restoreUser: async (): Promise<User | null> => {
    if (!browserStorage()?.getItem(ACCESS_TOKEN_KEY)) return null;
    try {
      return toCurrentUser((await apiClient.get<CurrentUserResponse>(ENDPOINTS.me)).data);
    } catch {
      clearSession();
      return null;
    }
  },

  logout: async (): Promise<void> => {
    const token = browserStorage()?.getItem(ACCESS_TOKEN_KEY);
    try {
      if (token && SUPABASE_AUTH_BASE && SUPABASE_PUBLISHABLE_KEY) {
        await supabaseClient.post("/logout", undefined, {
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } finally {
      clearSession();
    }
  },

  forgot: async (email: string) => {
    requireSupabaseConfiguration();
    await supabaseClient.post("/recover", { email });
    browserStorage()?.setItem(RECOVERY_EMAIL_KEY, email);
    return { ok: true, email };
  },

  verifyOtp: async (code: string) => {
    requireSupabaseConfiguration();
    const email = browserStorage()?.getItem(RECOVERY_EMAIL_KEY);
    if (!email) throw new Error("The recovery email is missing. Request a new code.");
    const { data } = await supabaseClient.post<SupabaseSessionResponse>("/verify", {
      email,
      token: code,
      type: "recovery",
    });
    persistSession(data);
    return { ok: true };
  },

  reset: async (password: string) => {
    requireSupabaseConfiguration();
    const token = browserStorage()?.getItem(ACCESS_TOKEN_KEY);
    if (!token) throw new Error("A verified recovery session is required.");
    await supabaseClient.put(
      "/user",
      { password },
      { headers: { Authorization: `Bearer ${token}` } },
    );
    return { ok: true };
  },

  dashboard: async () => {
    const [analytics, documentPage] = await Promise.all([fetchAnalytics(), fetchDocuments()]);
    const documents = documentPage.items.map(toDocument);
    const today = new Date().toISOString().slice(0, 10);
    const queriesToday = analytics.ai_usage.find((point) => point.date === today)?.questions ?? 0;
    const statusCounts = documents.reduce<Record<string, number>>((counts, document) => {
      counts[document.status] = (counts[document.status] ?? 0) + 1;
      return counts;
    }, {});
    return {
      stats: {
        totalDocuments: analytics.total_documents,
        departments: analytics.top_departments.length,
        graphNodes: 0,
        queriesToday,
        pendingCompliance: 0,
        openMaintenance: 0,
        avgResponseMs: 0,
      },
      docsByDepartment: analytics.top_departments.map((department) => ({
        name: department.department,
        value: department.documents,
      })),
      aiUsage: analytics.ai_usage.map((point) => ({
        month: point.date.slice(5),
        queries: point.questions,
        responses: point.questions,
      })),
      uploadTrend: analytics.upload_trends.map((point) => ({
        month: point.date.slice(5),
        uploads: point.uploads,
      })),
      knowledgeCategories: Object.entries(statusCounts).map(([name, value]) => ({ name, value })),
      recentActivity: documents.slice(0, 5).map((document) => ({
        id: document.id,
        who: document.uploadedBy,
        what: `uploaded ${document.name}`,
        when: document.date,
      })),
    };
  },

  documents: async () => (await fetchDocuments()).items.map(toDocument),

  upload: async (files: File[]) => {
    const responses = await Promise.all(
      files.map((file) => {
        const form = new FormData();
        form.append("file", file);
        return apiClient.post(ENDPOINTS.upload, form);
      }),
    );
    return { ok: true, queued: responses.length };
  },

  chatHistory: async (): Promise<Conversation[]> => {
    const { data } = await apiClient.get<BackendConversation[]>(ENDPOINTS.chatHistory);
    return data.map((conversation) => ({
      id: conversation.id,
      title: conversation.title,
      updatedAt: conversation.updated_at,
      messages: conversation.messages
        .map(toChatMessage)
        .filter((message): message is ChatMessage => message !== null),
    }));
  },

  chat: async (question: string, conversationId?: string | null): Promise<ChatMessage> => {
    const { data } = await apiClient.post<BackendChatResponse>(ENDPOINTS.chat, {
      question,
      conversation_id: conversationId || undefined,
    });
    return {
      id: `assistant-${data.conversation_id}-${Date.now()}`,
      role: "assistant",
      content: data.answer,
      citations: data.citations.map((citation) => ({
        doc: citation.document,
        page: citation.page,
      })),
      createdAt: new Date().toISOString(),
      conversationId: data.conversation_id,
    };
  },

  analytics: async () => {
    const [analytics, documentPage] = await Promise.all([fetchAnalytics(), fetchDocuments()]);
    const indexed = documentPage.items.filter((document) => document.status === "indexed").length;
    return {
      topDocs: documentPage.items.slice(0, 5).map((document) => ({
        name: document.name,
        views: 0,
      })),
      topQuestions: [] as Array<{ q: string; count: number }>,
      machineUsage: analytics.top_departments.map((department) => ({
        name: department.department,
        value: department.documents,
      })),
      departmentUsage: analytics.top_departments.map((department) => ({
        name: department.department,
        value: department.documents,
      })),
      dailyRequests: analytics.ai_usage.map((point) => ({
        day: point.date.slice(5),
        value: point.questions,
      })),
      coverage: documentPage.total ? Math.round((indexed / documentPage.total) * 100) : 0,
    };
  },

  compliance: async (): Promise<ComplianceItem[]> =>
    (await apiClient.get<ComplianceItem[]>(ENDPOINTS.compliance)).data,

  maintenance: async (): Promise<MaintenanceTask[]> =>
    (await apiClient.get<MaintenanceTask[]>(ENDPOINTS.maintenance)).data,

  graph: async (): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> =>
    (await apiClient.get<{ nodes: GraphNode[]; edges: GraphEdge[] }>(ENDPOINTS.graph)).data,
};

export const ENDPOINT_MAP = ENDPOINTS;
