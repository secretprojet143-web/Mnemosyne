const API_URL = "http://localhost:8000";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/";
    }
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `API error ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  register: (username: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  // Health
  health: () =>
    request<{ ok: boolean; app: string; llm_provider: string; llm_connected: boolean }>("/health"),

  // ─── Memory (Real AI Engine) ───────────────────────────

  getFacts: (category?: string, limit = 50) => {
    const params = new URLSearchParams();
    if (category && category !== 'all') params.set('category', category);
    params.set('limit', String(limit));
    return request<{ facts: any[]; total: number }>(`/memory/facts?${params}`);
  },

  extractFacts: (text: string) =>
    request<{ extracted: any[]; count: number }>(`/memory/extract?text=${encodeURIComponent(text)}`),

  storeFacts: (text: string, conversationId = 0) =>
    request<{ stored: any[]; count: number }>(`/memory/store?text=${encodeURIComponent(text)}&conversation_id=${conversationId}`),

  getMemoryStats: () =>
    request<{ conversations: number; messages: number; facts: number; active_facts: number }>("/memory/stats"),

  chatWithMemory: (msg: string) =>
    request<{ response: string; model: string; memories_used: number; usage: any }>(`/memory/chat?message=${encodeURIComponent(msg)}`, {
      method: "POST",
    }),

  chatWithMemoryStream: async (
    msg: string,
    onToken: (token: string) => void,
    onFilesCreated?: (files: string[]) => void,
    onIntelligence?: (meta: any) => void,
  ): Promise<void> => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_URL}/memory/chat/stream?message=${encodeURIComponent(msg)}`, {
      method: "POST",
      headers,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `API error ${res.status}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;
        const data = trimmed.slice(6);
        if (data === "[DONE]") return;

        try {
          const parsed = JSON.parse(data);
          if (parsed.token) {
            onToken(parsed.token);
          }
          if (parsed.files_created && onFilesCreated) {
            onFilesCreated(parsed.files_created);
          }
          if (parsed.intelligence && onIntelligence) {
            onIntelligence(parsed.intelligence);
          }
          if (parsed.error) {
            throw new Error(parsed.error);
          }
        } catch (e: any) {
          if (e.message && e.message !== "Unexpected token") throw e;
        }
      }
    }
  },

  submitFeedback: (planId: number, stepId: number, outcome: string, reason = "") =>
    request<{ status: string; outcome: string }>("/memory/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ plan_id: String(planId), step_id: String(stepId), outcome, reason }),
    }),

  getLearningInsights: () =>
    request<any>("/memory/learning"),

  // ─── AI Engine (Continuity, Proactive, Temporal) ───────

  getProjects: () =>
    request<{ projects: any[] }>("/ai/projects"),

  createProject: (title: string, description = "", priority = "medium") =>
    request<any>("/ai/projects", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ title, description, priority }),
    }),

  getGoals: (status = "active") =>
    request<{ goals: any[] }>(`/ai/goals?status=${status}`),

  createGoal: (goalText: string, projectId?: number, priority = "medium") =>
    request<any>("/ai/goals", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ goal_text: goalText, ...(projectId ? { project_id: String(projectId) } : {}), priority }),
    }),

  getOpenLoops: (status = "open") =>
    request<{ open_loops: any[] }>(`/ai/open-loops?status=${status}`),

  createOpenLoop: (description: string, projectId?: number, priority = "medium") =>
    request<any>("/ai/open-loops", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ description, ...(projectId ? { project_id: String(projectId) } : {}), priority }),
    }),

  getContinuitySnapshot: () =>
    request<any>("/ai/continuity/snapshot"),

  getNextActions: (limit = 8) =>
    request<{ actions: any[] }>(`/ai/continuity/next-actions?limit=${limit}`),

  getProactiveBriefing: () =>
    request<any>("/ai/proactive/briefing"),

  getTemporalHealth: () =>
    request<any>("/ai/temporal/health"),

  getTemporalChanges: () =>
    request<any>("/ai/temporal/changes"),

  getReconfirmationCandidates: (staleAfterDays = 30) =>
    request<{ candidates: any[] }>(`/ai/temporal/reconfirmation?stale_after_days=${staleAfterDays}`),

  getFullStats: () =>
    request<any>("/ai/stats"),
};

export const fetchWithAuth = (endpoint: string, options: RequestInit = {}) =>
  request<any>(endpoint, options);
