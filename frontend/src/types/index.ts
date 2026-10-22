export type TaskStatus =
  | 'PENDING'
  | 'PLANNING'
  | 'RUNNING'
  | 'WAITING_APPROVAL'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface Subtask {
  id: string;
  task_id: string;
  order_index: number;
  title: string;
  description: string;
  assigned_agent: 'researcher' | 'coder';
  status: string;
  result?: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  goal: string;
  status: TaskStatus;
  current_step: number;
  rework_count: number;
  token_usage: number;
  estimated_cost_usd: number;
  final_output?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  subtasks: Subtask[];
}

export interface AuditLog {
  id: string;
  task_id?: string | null;
  agent_name: string;
  action_type: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  payload?: Record<string, any> | null;
  created_at: string;
}

export interface PendingApproval {
  task_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  risk_level: string;
  reason: string;
}

export interface PendingApprovalItem {
  task_id: string;
  goal: string;
  tool_name: string;
  arguments: Record<string, any>;
  risk_level: string;
  reason: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface PendingApprovalsListResponse {
  total: number;
  approvals: PendingApprovalItem[];
}
