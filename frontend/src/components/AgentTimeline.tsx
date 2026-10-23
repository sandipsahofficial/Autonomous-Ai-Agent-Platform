import React, { useState } from 'react';
import { Task } from '../types';
import { retryTask } from '../api/client';

interface Props {
  task: Task | null;
  onRefresh?: () => void;
}

const STAGES = ['planner', 'researcher', 'executor', 'reviewer', 'finalizer'];

export const AgentTimeline: React.FC<Props> = ({ task, onRefresh }) => {
  const [retrying, setRetrying] = useState(false);
  const [retryMsg, setRetryMsg] = useState<string | null>(null);

  if (!task) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
        <p>No active agent task selected. Submit a goal above to start.</p>
      </div>
    );
  }

  const handleRetry = async () => {
    if (!task) return;
    try {
      setRetrying(true);
      setRetryMsg(null);
      const res = await retryTask(task.id);
      setRetryMsg(res.message);
      if (onRefresh) onRefresh();
    } catch (err: any) {
      setRetryMsg(`Retry failed: ${err.message}`);
    } finally {
      setRetrying(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'badge-low';
      case 'WAITING_APPROVAL':
        return 'badge-high';
      case 'FAILED':
        return 'badge-high';
      default:
        return 'badge-medium';
    }
  };

  const currentStage = (task.current_stage || 'planner').toLowerCase();
  const currentStageIndex = STAGES.indexOf(currentStage) !== -1 ? STAGES.indexOf(currentStage) : 0;

  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      {/* Header telemetry metrics */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Task ID: {task.id.slice(0, 8)}...
          </span>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '4px' }}>
            {task.goal}
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span className={`badge ${getStatusBadgeClass(task.status)}`}>
            {task.status}
          </span>
          <div style={{ textAlign: 'right', fontSize: '0.85rem' }}>
            <div>Steps: <strong style={{ color: 'var(--accent-cyan)' }}>{task.current_step}</strong></div>
            <div>Tokens: <strong>{task.token_usage}</strong></div>
            <div>Cost: <strong style={{ color: 'var(--accent-green)' }}>${task.estimated_cost_usd.toFixed(4)}</strong></div>
          </div>
        </div>
      </div>

      {/* Multi-Agent 5-Stage Orchestration Pipeline Indicator */}
      <div style={{ marginBottom: '20px', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: '10px', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
            Active Stage Pipeline
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontFamily: 'monospace' }}>
            Current: {task.current_stage?.toUpperCase() || 'PLANNER'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
          {STAGES.map((stg, i) => {
            const isCurrent = currentStage === stg;
            const isPast = task.status === 'COMPLETED' || currentStageIndex > i;
            return (
              <React.Fragment key={stg}>
                <div style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  textTransform: 'capitalize',
                  background: isCurrent ? 'rgba(56, 189, 248, 0.2)' : isPast ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-secondary)',
                  color: isCurrent ? '#38bdf8' : isPast ? '#34d399' : 'var(--text-muted)',
                  border: isCurrent ? '1px solid #38bdf8' : isPast ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  <span>{isPast ? '✓' : i + 1}</span>
                  <span>{stg}</span>
                </div>
                {i < STAGES.length - 1 && (
                  <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>→</span>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Subtasks Execution Trace */}
      <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px' }}>
        Ordered Subtask Progression
      </h4>

      {task.subtasks.length === 0 ? (
        <div style={{ padding: '16px', background: 'var(--bg-tertiary)', borderRadius: '8px', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Planner agent analyzing goal and generating subtasks...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {task.subtasks.map((sub, idx) => (
            <div
              key={sub.id || idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                padding: '12px 16px',
                background: 'var(--bg-tertiary)',
                borderRadius: '8px',
                border: '1px solid var(--border)',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                    #{sub.order_index + 1}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                    {sub.title}
                  </span>
                  <span className="badge badge-low" style={{ fontSize: '0.65rem' }}>
                    {sub.assigned_agent}
                  </span>
                  {sub.dependencies && sub.dependencies.length > 0 && (
                    <span style={{ fontSize: '0.62rem', color: '#94a3b8', background: 'rgba(148, 163, 184, 0.1)', padding: '2px 5px', borderRadius: '4px' }}>
                      deps: {sub.dependencies.map(d => `#${d + 1}`).join(', ')}
                    </span>
                  )}
                  {sub.retry_count != null && sub.retry_count > 0 && (
                    <span style={{ fontSize: '0.62rem', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.15)', padding: '2px 5px', borderRadius: '4px' }}>
                      retries: {sub.retry_count}
                    </span>
                  )}
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  {sub.description}
                </p>
                {sub.result && (
                  <div style={{ marginTop: '8px', padding: '8px', background: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                    {sub.result.slice(0, 150)}...
                  </div>
                )}
              </div>

              <span className={`badge ${sub.status === 'COMPLETED' ? 'badge-low' : 'badge-medium'}`}>
                {sub.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Final Result Display */}
      {task.final_output && (
        <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px' }}>
          <h4 style={{ color: 'var(--accent-green)', fontSize: '0.9rem', fontWeight: 700, marginBottom: '8px' }}>
            ✓ Verified Final Output
          </h4>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.85rem', color: 'var(--text-main)' }}>
            {task.final_output}
          </pre>
        </div>
      )}

      {task.error_message && (
        <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(244, 63, 94, 0.05)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h4 style={{ color: 'var(--accent-rose)', fontSize: '0.9rem', fontWeight: 700 }}>
              ⚠ Task Error / Safety Limit Exceeded
            </h4>
            <button
              onClick={handleRetry}
              disabled={retrying}
              style={{
                background: '#f43f5e',
                color: '#fff',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: retrying ? 'not-allowed' : 'pointer',
              }}
            >
              {retrying ? 'Retrying Mission...' : '↺ Retry Mission'}
            </button>
          </div>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.85rem', color: 'var(--accent-rose)' }}>
            {task.error_message}
          </pre>
          {retryMsg && (
            <div style={{ marginTop: '8px', fontSize: '0.75rem', color: '#38bdf8' }}>
              {retryMsg}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
