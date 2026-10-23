import {
  Task,
  AuditLog,
  PendingApproval,
  PendingApprovalsListResponse,
  FleetMetrics,
  AgentMetricsListResponse,
  TaskTracesResponse,
} from '../types';

const API_BASE = '/api/v1';

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
  const res = await fetch(url);
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
