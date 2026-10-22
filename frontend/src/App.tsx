import React, { useState, useEffect } from 'react';
import { Task, AuditLog, PendingApproval } from './types';
import * as api from './api/client';
import { TaskSubmission } from './components/TaskSubmission';
import { AgentTimeline } from './components/AgentTimeline';
import { HumanApprovalModal } from './components/HumanApprovalModal';
import { AuditLogViewer } from './components/AuditLogViewer';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'workspace' | 'audit'>('workspace');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditFilter, setAuditFilter] = useState<string | undefined>(undefined);
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);

  // Poll state every 2 seconds (per agreed architecture requirement)
  useEffect(() => {
    const poll = async () => {
      try {
        // 1. Fetch recent tasks
        const taskData = await api.listTasks();
        setTasks(taskData.tasks);

        // If no active task is selected, default to the latest one
        const currentId = activeTaskId || (taskData.tasks.length > 0 ? taskData.tasks[0].id : null);
        if (currentId) {
          if (!activeTaskId) setActiveTaskId(currentId);
          const taskDetail = await api.getTask(currentId);
          setActiveTask(taskDetail);

          // 2. Check for human-in-the-loop pending approval
          const approvalData = await api.getPendingApproval(currentId);
          if (approvalData.has_pending_approval && approvalData.pending_approval) {
            setPendingApproval(approvalData.pending_approval);
          } else {
            setPendingApproval(null);
          }
        }

        // 3. Fetch audit logs
        const auditData = await api.listAuditLogs(auditFilter);
        setAuditLogs(auditData.logs);
      } catch (err) {
        // Backend might be reloading or starting up
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [activeTaskId, auditFilter]);

  const handleCreateTask = async (goal: string) => {
    setIsDeploying(true);
    try {
      const newTask = await api.createTask(goal);
      setActiveTaskId(newTask.id);
      setActiveTask(newTask);
    } catch (err) {
      alert(`Error creating task: ${err}`);
    } finally {
      setIsDeploying(false);
    }
  };

  const handleApprovalDecision = async (approved: boolean, feedback?: string) => {
    if (!activeTaskId) return;
    setIsSubmittingApproval(true);
    try {
      await api.submitApproval(activeTaskId, approved, feedback);
      setPendingApproval(null);
      // Immediately refresh task
      const updated = await api.getTask(activeTaskId);
      setActiveTask(updated);
    } catch (err) {
      alert(`Error submitting decision: ${err}`);
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 16px' }}>
      {/* Platform Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--accent-cyan)' }}>◈</span> Autonomous AI Agent Platform
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            LangGraph Multi-Agent Team • Safety Guardrails • Human-in-the-Loop Gate
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border)' }}>
          <button
            className="btn"
            style={{
              background: activeTab === 'workspace' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'workspace' ? '#ffffff' : 'var(--text-muted)',
              padding: '6px 14px',
              fontSize: '0.85rem',
            }}
            onClick={() => setActiveTab('workspace')}
          >
            Agent Workspace & Timeline
          </button>
          <button
            className="btn"
            style={{
              background: activeTab === 'audit' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'audit' ? '#ffffff' : 'var(--text-muted)',
              padding: '6px 14px',
              fontSize: '0.85rem',
            }}
            onClick={() => setActiveTab('audit')}
          >
            Safety Audit Logs
          </button>
        </div>
      </header>

      {/* Main Tab Content */}
      {activeTab === 'workspace' ? (
        <main>
          <TaskSubmission onSubmit={handleCreateTask} isLoading={isDeploying} />

          {/* Task selector if multiple tasks exist */}
          {tasks.length > 1 && (
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '16px' }}>
              {tasks.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTaskId(t.id)}
                  className="btn btn-secondary"
                  style={{
                    fontSize: '0.75rem',
                    borderColor: activeTaskId === t.id ? 'var(--accent-cyan)' : 'var(--border)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {t.goal.slice(0, 25)}... ({t.status})
                </button>
              ))}
            </div>
          )}

          <AgentTimeline task={activeTask} />
        </main>
      ) : (
        <main>
          <AuditLogViewer
            logs={auditLogs}
            selectedFilter={auditFilter}
            onFilterChange={(filter) => setAuditFilter(filter)}
          />
        </main>
      )}

      {/* Human Approval Modal (Pops up automatically when a task is waiting for approval) */}
      {pendingApproval && (
        <HumanApprovalModal
          approval={pendingApproval}
          onDecision={handleApprovalDecision}
          isSubmitting={isSubmittingApproval}
        />
      )}
    </div>
  );
};
