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
  assigned_agent: 'researcher' | 'coder' | 'executor';
  status: string;
  stage?: string;
  dependencies?: number[];
  retry_count?: number;
  result?: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  user_id?: string;
  workspace_id?: string;
  goal: string;
  status: TaskStatus;
  current_stage?: string;
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

export interface FleetMetrics {
  total_tasks: number;
  active_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  pending_approvals: number;
  completion_rate: number;
  average_cost_usd: number;
  total_cost_usd: number;
  total_tokens: number;
}

export interface AgentMetricItem {
  id: string;
  name: string;
  role: string;
  assigned_agent: string;
  status: string;
  status_type: string;
  runs: number;
  success_rate: number;
  usage_percent: number;
  cost_usd: number;
  last_active?: string | null;
}

export interface AgentMetricsListResponse {
  total_agents: number;
  agents: AgentMetricItem[];
}

export interface ExecutionEvent {
  id: string;
  task_id: string;
  step_index: number;
  event_type: string;
  agent_name?: string | null;
  status?: string;
  duration_ms?: number | null;
  idempotency_key?: string | null;
  message: string;
  details?: Record<string, any> | null;
  created_at: string;
}

export interface TaskTracesResponse {
  task_id: string;
  total_events: number;
  events: ExecutionEvent[];
}

export interface AgentMemoryItem {
  id: string;
  user_id: string;
  workspace_id: string;
  mission_id?: string | null;
  memory_type: 'mission' | 'workspace' | 'task_history';
  key: string;
  content: string;
  metadata_?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  expires_at?: string | null;
}

export interface MemoryListResponse {
  total: number;
  memories: AgentMemoryItem[];
}

export interface FailureReasonItem {
  reason: string;
  count: number;
}

export interface EvaluationQualityMetrics {
  task_completion_rate: number;
  reviewer_acceptance_rate: number;
  tool_success_rate: number;
  retry_rate: number;
  average_duration_ms: number;
  p95_duration_ms: number;
  llm_failures_count: number;
  approval_wait_time_avg_s: number;
  top_failure_reasons: FailureReasonItem[];
}

// ==========================================
// PHASE 4: VISUAL WORKFLOW AUTOMATION TYPES
// ==========================================

export interface CustomAgent {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  role: string;
  permitted_tools: string[];
  model_provider: string;
  model_name: string;
  temperature: number;
  max_steps: number;
  system_prompt?: string | null;
  review_policy: string;
  is_enabled: boolean;
  total_runs: number;
  successful_runs: number;
  created_at: string;
  updated_at: string;
}

export type WorkflowNodeType =
  | 'start'
  | 'agent'
  | 'tool'
  | 'conditional'
  | 'approval'
  | 'parallel'
  | 'merge'
  | 'review'
  | 'end';

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  label: string;
  agent_slug?: string | null;
  tool_name?: string | null;
  config?: Record<string, any>;
  position?: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string | null;
  label?: string | null;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface Workflow {
  id: string;
  user_id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_enabled: boolean;
  version_count: number;
  active_version: number;
  total_runs: number;
  successful_runs: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends Workflow {
  definition: WorkflowDefinition;
  versions?: any[];
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  version_number: number;
  task_id?: string | null;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'WAITING_APPROVAL';
  current_node_id?: string | null;
  node_states?: Record<string, string>;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface WorkflowSchedule {
  id: string;
  user_id: string;
  workspace_id: string;
  workflow_id?: string | null;
  name: string;
  goal: string;
  schedule_type: 'one_time' | 'recurring';
  cron_expression?: string | null;
  timezone_str: string;
  is_enabled: boolean;
  allow_overlap: boolean;
  next_run_at?: string | null;
  last_run_at?: string | null;
  failure_count: number;
  last_error?: string | null;
  created_at: string;
}

export interface ScheduleExecution {
  id: string;
  schedule_id: string;
  task_id?: string | null;
  idempotency_key: string;
  status: string;
  scheduled_time: string;
  executed_time: string;
  error_message?: string | null;
}

export interface KnowledgeDocument {
  id: string;
  user_id: string;
  workspace_id: string;
  filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number;
  status: string;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  chunks?: DocumentChunk[];
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  page_number: number;
  content: string;
  token_count: number;
  metadata_?: Record<string, any>;
}

export interface DocumentCitation {
  document_id: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  matched_snippet: string;
  score: number;
}

export interface Template {
  id: string;
  slug: string;
  name: string;
  category: string;
  description: string;
  author: string;
  version: string;
  is_built_in: boolean;
  workflow_definition: WorkflowDefinition;
  default_inputs: Record<string, any>;
  tags: string[];
  downloads_count: number;
  created_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  category: 'MISSION' | 'APPROVAL' | 'SCHEDULE' | 'SECURITY';
  entity_id?: string | null;
  is_read: boolean;
  action_url?: string | null;
  created_at: string;
}

export interface ProviderStatusItem {
  provider_name: string;
  is_available: boolean;
  is_configured: boolean;
  is_local: boolean;
  supported_models: string[];
  latency_ms?: number | null;
  last_error?: string | null;
}

export interface ModelRouterStatus {
  default_provider: string;
  providers: ProviderStatusItem[];
  active_routing_policy: string;
}

export interface WorkflowBreakdownItem {
  workflow_id: string;
  name: string;
  runs: number;
  success_rate: number;
  avg_duration_ms: number;
  avg_cost_usd: number;
}

export interface EvaluationDashboardData {
  quality_metrics: EvaluationQualityMetrics;
  total_evaluations: number;
  completed_evaluations: number;
  failed_evaluations: number;
  benchmark_safety_score: number;
  workflow_breakdown: WorkflowBreakdownItem[];
}
