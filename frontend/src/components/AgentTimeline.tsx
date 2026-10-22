import React from 'react';
import { Task } from '../types';

interface Props {
  task: Task | null;
}

export const AgentTimeline: React.FC<Props> = ({ task }) => {
  if (!task) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
        <p>No active agent task selected. Submit a goal above to start.</p>
      </div>
    );
  }

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
          <h4 style={{ color: 'var(--accent-rose)', fontSize: '0.9rem', fontWeight: 700, marginBottom: '8px' }}>
            ⚠ Task Error / Safety Limit Exceeded
          </h4>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '0.85rem', color: 'var(--accent-rose)' }}>
            {task.error_message}
          </pre>
        </div>
      )}
    </div>
  );
};
