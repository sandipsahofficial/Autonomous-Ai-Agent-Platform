import {
  Task,
  AuditLog,
  PendingApproval,
  PendingApprovalsListResponse,
  FleetMetrics,
  AgentMetricsListResponse,
  TaskTracesResponse,
  EvaluationQualityMetrics,
  MemoryListResponse,
  AgentMemoryItem,
} from '../types';

const API_BASE = '/api/v1';

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined' && window.localStorage) {
    return localStorage.getItem('mesh_access_token');
  }
  return null;
}

export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined' && window.localStorage) {
    localStorage.setItem('mesh_access_token', token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== 'undefined' && window.localStorage) {
    localStorage.removeItem('mesh_access_token');
  }
}

export function authHeaders(headers: Record<string, string> = {}): Record<string, string> {
  const token = getAuthToken();
  const res: Record<string, string> = { ...headers };
  if (token && !res['Authorization']) {
    res['Authorization'] = `Bearer ${token}`;
  }
  return res;
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const reqHeaders = authHeaders((init.headers as Record<string, string>) || {});
  const res = await fetch(input, {
    ...init,
    headers: reqHeaders,
  });

  if (res.status === 401) {
    clearAuthToken();
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Authentication required or session expired. Please log in.');
  }

  if (res.status === 403) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Forbidden: You do not have permission for this operation.');
  }

  if (res.status === 429) {
    throw new Error('Rate limit exceeded: Please wait before retrying.');
  }

  return res;
}

export async function loginUser(username: string, password: string): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Login failed: ${res.statusText}`);
  }
  const data = await res.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

export async function logoutUser(): Promise<void> {
  clearAuthToken();
}

export async function getCurrentUser(): Promise<any> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch current user profile: ${res.statusText}`);
  return res.json();
}

export async function createTask(goal: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal }),
  });
  if (!res.ok) throw new Error(`Failed to create task: ${res.statusText}`);
  return res.json();
}

export async function listTasks(): Promise<{ total: number; tasks: Task[] }> {
  const res = await fetch(`${API_BASE}/tasks`);
  if (!res.ok) throw new Error(`Failed to list tasks: ${res.statusText}`);
  return res.json();
}

export async function getTask(taskId: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!res.ok) throw new Error(`Failed to fetch task: ${res.statusText}`);
  return res.json();
}

export async function getPendingApproval(taskId: string): Promise<{
  has_pending_approval: boolean;
  pending_approval: PendingApproval | null;
}> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/pending-approval`);
  if (!res.ok) throw new Error(`Failed to fetch approval state: ${res.statusText}`);
  return res.json();
}

export async function listPendingApprovals(): Promise<PendingApprovalsListResponse> {
  const res = await fetch(`${API_BASE}/approvals/pending`);
  if (!res.ok) throw new Error(`Failed to list pending approvals: ${res.statusText}`);
  return res.json();
}

export async function submitApproval(
  taskId: string,
  approved: boolean,
  feedback?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved, feedback }),
  });
  if (!res.ok) throw new Error(`Failed to submit approval: ${res.statusText}`);
  return res.json();
}

export async function listAuditLogs(riskLevel?: string): Promise<{ total: number; logs: AuditLog[] }> {
  const url = riskLevel
    ? `${API_BASE}/audit-logs?risk_level=${riskLevel}`
    : `${API_BASE}/audit-logs`;
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`Failed to fetch audit logs: ${res.statusText}`);
  return res.json();
}

export async function getFleetMetrics(): Promise<FleetMetrics> {
  const res = await fetch(`${API_BASE}/metrics/fleet`);
  if (!res.ok) throw new Error(`Failed to fetch fleet metrics: ${res.statusText}`);
  return res.json();
}

export async function getAgentMetrics(): Promise<AgentMetricsListResponse> {
  const res = await fetch(`${API_BASE}/metrics/agents`);
  if (!res.ok) throw new Error(`Failed to fetch agent metrics: ${res.statusText}`);
  return res.json();
}

export async function getTaskTraces(taskId: string): Promise<TaskTracesResponse> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/traces`);
  if (!res.ok) throw new Error(`Failed to fetch task traces: ${res.statusText}`);
  return res.json();
}

export async function getQualityMetrics(): Promise<EvaluationQualityMetrics> {
  const res = await fetch(`${API_BASE}/metrics/quality`);
  if (!res.ok) throw new Error(`Failed to fetch quality metrics: ${res.statusText}`);
  return res.json();
}

export async function listMemories(params?: {
  user_id?: string;
  workspace_id?: string;
  memory_type?: string;
  query?: string;
}): Promise<MemoryListResponse> {
  const q = new URLSearchParams();
  if (params?.user_id) q.set('user_id', params.user_id);
  if (params?.workspace_id) q.set('workspace_id', params.workspace_id);
  if (params?.memory_type) q.set('memory_type', params.memory_type);
  if (params?.query) q.set('query', params.query);
  const qs = q.toString() ? `?${q.toString()}` : '';
  const res = await fetch(`${API_BASE}/memories${qs}`);
  if (!res.ok) throw new Error(`Failed to fetch memories: ${res.statusText}`);
  return res.json();
}

export async function createMemory(payload: {
  key: string;
  content: string;
  memory_type?: string;
  workspace_id?: string;
  mission_id?: string;
  ttl_seconds?: number;
}): Promise<AgentMemoryItem> {
  const res = await fetch(`${API_BASE}/memories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to create memory: ${res.statusText}`);
  return res.json();
}

export async function deleteMemory(memoryId: string, userId?: string): Promise<void> {
  const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
  const res = await fetch(`${API_BASE}/memories/${memoryId}${qs}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete memory: ${res.statusText}`);
  }
}

export async function retryTask(taskId: string): Promise<{ success: boolean; message: string; task_id: string }> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/retry`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to retry task: ${res.statusText}`);
  return res.json();
}

// ==========================================
// PHASE 4: AGENTS API
// ==========================================

export async function listCustomAgents(): Promise<{ total: number; agents: any[] }> {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) throw new Error(`Failed to list agents: ${res.statusText}`);
  return res.json();
}

export async function createCustomAgent(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create agent: ${res.statusText}`);
  }
  return res.json();
}

export async function updateCustomAgent(agentId: string, payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/${agentId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to update agent: ${res.statusText}`);
  return res.json();
}

export async function duplicateCustomAgent(agentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/${agentId}/duplicate`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to duplicate agent: ${res.statusText}`);
  return res.json();
}

export async function deleteCustomAgent(agentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/agents/${agentId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to delete agent: ${res.statusText}`);
  }
}

// ==========================================
// PHASE 4: WORKFLOWS API
// ==========================================

export async function listWorkflows(): Promise<{ total: number; workflows: any[] }> {
  const res = await fetch(`${API_BASE}/workflows`);
  if (!res.ok) throw new Error(`Failed to list workflows: ${res.statusText}`);
  return res.json();
}

export async function getWorkflow(workflowId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/workflows/${workflowId}`);
  if (!res.ok) throw new Error(`Failed to fetch workflow: ${res.statusText}`);
  return res.json();
}

export async function createWorkflow(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create workflow: ${res.statusText}`);
  }
  return res.json();
}

export async function updateWorkflow(workflowId: string, payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/workflows/${workflowId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to update workflow: ${res.statusText}`);
  return res.json();
}

export async function validateWorkflow(definition: any): Promise<{ is_valid: boolean; errors: string[]; warnings: string[] }> {
  const res = await fetch(`${API_BASE}/workflows/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ definition }),
  });
  if (!res.ok) throw new Error(`Validation failed: ${res.statusText}`);
  return res.json();
}

export async function executeWorkflow(workflowId: string, inputs?: Record<string, any>, goal?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/workflows/${workflowId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inputs: inputs || {}, goal_override: goal }),
  });
  if (!res.ok) throw new Error(`Execution failed: ${res.statusText}`);
  return res.json();
}

export async function getWorkflowRun(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/workflows/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch workflow run: ${res.statusText}`);
  return res.json();
}

// ==========================================
// PHASE 4: SCHEDULES API
// ==========================================

export async function listSchedules(): Promise<{ total: number; schedules: any[] }> {
  const res = await fetch(`${API_BASE}/schedules`);
  if (!res.ok) throw new Error(`Failed to list schedules: ${res.statusText}`);
  return res.json();
}

export async function createSchedule(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/schedules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create schedule: ${res.statusText}`);
  }
  return res.json();
}

export async function updateSchedule(scheduleId: string, payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to update schedule: ${res.statusText}`);
  return res.json();
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete schedule: ${res.statusText}`);
}

export async function triggerScheduleManual(scheduleId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}/trigger`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to trigger schedule: ${res.statusText}`);
  return res.json();
}

export async function listScheduleExecutions(scheduleId: string): Promise<{ total: number; executions: any[] }> {
  const res = await fetch(`${API_BASE}/schedules/${scheduleId}/executions`);
  if (!res.ok) throw new Error(`Failed to list executions: ${res.statusText}`);
  return res.json();
}

// ==========================================
// PHASE 4: DOCUMENTS & RETRIEVAL API
// ==========================================

export async function listDocuments(): Promise<{ total: number; documents: any[] }> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error(`Failed to list documents: ${res.statusText}`);
  return res.json();
}

export async function uploadDocumentFile(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `File upload failed: ${res.statusText}`);
  }
  return res.json();
}

export async function createDocumentText(filename: string, content: string): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create text document: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete document: ${res.statusText}`);
}

export async function queryDocumentCitations(query: string, topK: number = 3): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

// ==========================================
// PHASE 4: TEMPLATES API
// ==========================================

export async function listTemplates(category?: string): Promise<{ total: number; templates: any[] }> {
  const url = category ? `${API_BASE}/templates?category=${encodeURIComponent(category)}` : `${API_BASE}/templates`;
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`Failed to list templates: ${res.statusText}`);
  return res.json();
}

export async function cloneTemplate(templateId: string, customName?: string): Promise<any> {
  const qs = customName ? `?custom_name=${encodeURIComponent(customName)}` : '';
  const res = await fetch(`${API_BASE}/templates/${templateId}/clone${qs}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to clone template: ${res.statusText}`);
  return res.json();
}

export async function exportTemplateJson(templateId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/templates/${templateId}/export`);
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.json();
}

export async function importTemplateJson(templateData: any): Promise<any> {
  const res = await fetch(`${API_BASE}/templates/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(templateData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Import failed: ${res.statusText}`);
  }
  return res.json();
}

// ==========================================
// PHASE 4: NOTIFICATIONS API
// ==========================================

export async function listNotifications(unreadOnly: boolean = false): Promise<{ total: number; unread_count: number; notifications: any[] }> {
  const res = await fetch(`${API_BASE}/notifications?unread_only=${unreadOnly}`);
  if (!res.ok) throw new Error(`Failed to list notifications: ${res.statusText}`);
  return res.json();
}

export async function markNotificationRead(notifId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/notifications/${notifId}/read`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to mark read: ${res.statusText}`);
  return res.json();
}

export async function markAllNotificationsRead(): Promise<any> {
  const res = await fetch(`${API_BASE}/notifications/read-all`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to mark all read: ${res.statusText}`);
  return res.json();
}

// ==========================================
// PHASE 4: MODEL ROUTER & EVALUATION API
// ==========================================

export async function getModelRouterStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/model-router/status`);
  if (!res.ok) throw new Error(`Failed to fetch model router status: ${res.statusText}`);
  return res.json();
}

export async function getEvaluationDashboard(): Promise<any> {
  const res = await fetch(`${API_BASE}/evaluations/dashboard`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation dashboard: ${res.statusText}`);
  return res.json();
}

export function getEvaluationCsvDownloadUrl(): string {
  return `${API_BASE}/evaluations/export/csv`;
}
