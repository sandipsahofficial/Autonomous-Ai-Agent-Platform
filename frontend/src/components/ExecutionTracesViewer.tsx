import React, { useEffect, useState } from 'react';
import { ExecutionEvent } from '../types';
import { getTaskTraces } from '../api/client';

interface Props {
  taskId: string;
}

export const ExecutionTracesViewer: React.FC<Props> = ({ taskId }) => {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTraces = async () => {
    try {
      const data = await getTaskTraces(taskId);
      setEvents(data.events);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch execution traces');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!taskId) return;
    setIsLoading(true);
    fetchTraces();

    const interval = setInterval(fetchTraces, 3000);
    return () => clearInterval(interval);
  }, [taskId]);

  const getEventBadgeStyle = (eventType: string) => {
    switch (eventType) {
      case 'TASK_COMPLETED':
        return { background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)' };
      case 'TASK_FAILED':
      case 'APPROVAL_REJECTED':
        return { background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: '1px solid rgba(244, 63, 94, 0.3)' };
      case 'APPROVAL_REQUIRED':
      case 'TASK_PAUSED':
        return { background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)' };
      case 'TOOL_INVOKED':
      case 'TOOL_EXECUTED':
        return { background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)' };
      default:
        return { background: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', border: '1px solid rgba(148, 163, 184, 0.3)' };
    }
  };

  return (
    <div style={{
      background: '#0d1320',
      border: '1px solid #1a253a',
      borderRadius: '14px',
      padding: '20px',
      marginTop: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h4 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f1f5f9' }}>
            Structured Execution Trace
          </h4>
          <p style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
            Chronological audit of state transitions, tool invocations, and operator decisions
          </p>
        </div>
        <button
          onClick={fetchTraces}
          style={{
            background: '#141d2e',
            border: '1px solid #222f46',
            color: '#94a3b8',
            borderRadius: '6px',
            padding: '4px 10px',
            fontSize: '0.72rem',
            cursor: 'pointer'
          }}
        >
          ↻ Refresh
        </button>
      </div>

      {isLoading && events.length === 0 ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
          Loading trace telemetry...
        </div>
      ) : error ? (
        <div style={{ padding: '16px', background: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '8px', fontSize: '0.8rem' }}>
          {error}
        </div>
      ) : events.length === 0 ? (
        <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
          No execution events recorded yet for this mission.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {events.map((event, idx) => {
            const badgeStyle = getEventBadgeStyle(event.event_type);
            return (
              <div
                key={event.id || idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  background: '#0a0e18',
                  borderRadius: '10px',
                  border: '1px solid #172134',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start', flex: 1 }}>
                  <div style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    background: '#141d2e',
                    border: '1px solid #1f2b42',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.65rem',
                    color: '#94a3b8',
                    flexShrink: 0,
                    marginTop: '2px'
                  }}>
                    {idx + 1}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                      <span style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        ...badgeStyle
                      }}>
                        {event.event_type}
                      </span>
                      {event.agent_name && (
                        <span style={{ fontSize: '0.68rem', color: '#38bdf8', fontWeight: 600 }}>
                          @{event.agent_name}
                        </span>
                      )}
                      {event.status && event.status !== 'INFO' && (
                        <span style={{
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          padding: '1px 5px',
                          borderRadius: '4px',
                          background: event.status === 'SUCCESS' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                          color: event.status === 'SUCCESS' ? '#34d399' : '#fb7185',
                        }}>
                          {event.status}
                        </span>
                      )}
                      {event.duration_ms != null && event.duration_ms > 0 && (
                        <span style={{ fontSize: '0.65rem', color: '#10b981', fontWeight: 600 }}>
                          ⏱ {event.duration_ms.toFixed(1)}ms
                        </span>
                      )}
                      {event.idempotency_key && (
                        <span style={{ fontSize: '0.62rem', color: '#64748b', fontFamily: 'monospace' }}>
                          🔑 {event.idempotency_key.slice(-8)}
                        </span>
                      )}
                      <span style={{ fontSize: '0.65rem', color: '#64748b' }}>
                        {new Date(event.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#e2e8f0' }}>
                      {event.message}
                    </div>
                    {event.details && Object.keys(event.details).length > 0 && (
                      <pre style={{
                        marginTop: '6px',
                        padding: '6px 10px',
                        background: '#05080f',
                        borderRadius: '6px',
                        border: '1px solid #121926',
                        fontSize: '0.68rem',
                        color: '#94a3b8',
                        fontFamily: 'monospace',
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap',
                      }}>
                        {JSON.stringify(event.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
