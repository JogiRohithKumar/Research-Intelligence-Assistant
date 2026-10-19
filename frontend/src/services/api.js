import axios from "axios";

export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// -------------------------------------------------------------
// TOKEN MANAGEMENT & AXIOS CLIENT
// -------------------------------------------------------------

const TOKEN_KEY = "v2_auth_token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // LocalStorage unavailable in certain sandboxes
  }
}

export function removeToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore
  }
}

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json"
  },
  timeout: 45000
});

// Automatically inject Authorization header if token exists
apiClient.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercept 401s to handle expired sessions
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      removeToken();
    }
    return Promise.reject(error);
  }
);


// -------------------------------------------------------------
// AUTHENTICATION API
// -------------------------------------------------------------

export async function loginUser(usernameOrEmail, password) {
  const response = await apiClient.post("/auth/login", {
    username_or_email: usernameOrEmail.trim(),
    password
  });
  if (response.data?.access_token) {
    setToken(response.data.access_token);
  }
  return response.data;
}

export async function registerUser(username, email, password) {
  const response = await apiClient.post("/auth/register", {
    username: username.trim(),
    email: email.trim(),
    password
  });
  if (response.data?.access_token) {
    setToken(response.data.access_token);
  }
  return response.data;
}

export async function getMe() {
  const response = await apiClient.get("/auth/me");
  return response.data;
}

export async function logoutUser() {
  try {
    await apiClient.post("/auth/logout");
  } finally {
    removeToken();
  }
}


// -------------------------------------------------------------
// SESSIONS API
// -------------------------------------------------------------

export async function listSessions() {
  const response = await apiClient.get("/sessions");
  return response.data;
}

export async function getSession(sessionId) {
  const response = await apiClient.get(`/sessions/${encodeURIComponent(sessionId)}`);
  return response.data;
}

export async function deleteSession(sessionId) {
  const response = await apiClient.delete(`/sessions/${encodeURIComponent(sessionId)}`);
  return response.data;
}


// -------------------------------------------------------------
// RESEARCH & BACKGROUND JOBS API
// -------------------------------------------------------------

export async function submitResearchJob(query, sessionId, idempotencyKey) {
  const payload = {
    query: query.trim(),
    sync: false
  };
  if (sessionId && typeof sessionId === "string" && sessionId.trim()) {
    payload.session_id = sessionId.trim();
  }
  if (idempotencyKey) {
    payload.idempotency_key = idempotencyKey;
  }

  const response = await apiClient.post("/research", payload);
  return response.data;
}

export async function getJobStatus(jobId) {
  const response = await apiClient.get(`/jobs/${encodeURIComponent(jobId)}`);
  return response.data;
}

export async function cancelResearchJob(jobId) {
  const response = await apiClient.post(`/jobs/${encodeURIComponent(jobId)}/cancel`);
  return response.data;
}

/**
 * Connects to the real-time Server-Sent Events stream for a research job.
 * Emits real events: research_started, agent_log, research_completed, research_failed, research_cancelled.
 */
export function subscribeJobStream(jobId, onEvent, onError) {
  const token = getToken();
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
  const streamUrl = `${API_URL}/jobs/${encodeURIComponent(jobId)}/stream${tokenParam}`;

  const eventSource = new EventSource(streamUrl);

  const eventTypes = [
    "ping",
    "research_started",
    "iteration_started",
    "search_started",
    "search_completed",
    "evidence_retrieval",
    "intelligence",
    "sufficiency",
    "targeted_query",
    "iteration_completed",
    "agent_log",
    "research_completed",
    "research_failed",
    "research_cancelled"
  ];

  eventTypes.forEach((type) => {
    eventSource.addEventListener(type, (e) => {
      try {
        const parsed = JSON.parse(e.data);
        onEvent({ type, data: parsed });
      } catch {
        onEvent({ type, data: e.data });
      }
    });
  });

  eventSource.onerror = (err) => {
    if (onError) onError(err);
  };

  return () => {
    eventSource.close();
  };
}

/**
 * Backward-compatible research runner.
 * Submits research and polls/resolves full result state.
 */
export async function runResearch(query, sessionId) {
  const payload = {
    query: query.trim(),
    sync: true  // Request synchronous execution when using direct runResearch
  };
  if (sessionId && typeof sessionId === "string" && sessionId.trim()) {
    payload.session_id = sessionId.trim();
  }

  const response = await apiClient.post("/research", payload, {
    timeout: 300000
  });

  return response.data;
}

export async function getStream() {
  const response = await apiClient.get("/stream", { timeout: 10000 });
  return response.data;
}