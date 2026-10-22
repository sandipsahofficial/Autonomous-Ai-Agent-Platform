import React, { useState } from 'react';
import { PendingApprovalItem } from '../types';

interface MeshApprovalQueueProps {
  approvals: PendingApprovalItem[];
  isLoading?: boolean;
  error?: string | null;
  onApprove: (taskId: string, feedback?: string) => void;
  onReject: (taskId: string, feedback?: string) => void;
  isSubmitting?: boolean;
}

export const MeshApprovalQueue: React.FC<MeshApprovalQueueProps> = ({
  approvals,
  isLoading = false,
  error = null,
  onApprove,
  onReject,
  isSubmitting = false,
}) => {
  const [inspectingTaskId, setInspectingTaskId] = useState<string | null>(null);
  const [operatorFeedback, setOperatorFeedback] = useState<string>('');
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const totalPending = approvals.length;

  const handleQuickApprove = (taskId: string) => {
    onApprove(taskId, 'Approved via MESH Dashboard');
    setActionSuccessMsg(`Action authorized for task ${taskId.slice(0, 8)}...`);
    setTimeout(() => setActionSuccessMsg(null), 3500);
  };

  const handleQuickReject = (taskId: string) => {
    onReject(taskId, 'Rejected by operator');
    setActionSuccessMsg(`Action rejected for task ${taskId.slice(0, 8)}...`);
    setTimeout(() => setActionSuccessMsg(null), 3500);
  };

  const handleDetailedDecision = (taskId: string, approved: boolean) => {
    if (approved) {
      onApprove(taskId, operatorFeedback || 'Approved via MESH Review Panel');
    } else {
      onReject(taskId, operatorFeedback || 'Rejected via MESH Review Panel');
    }
    setInspectingTaskId(null);
    setOperatorFeedback('');
    setActionSuccessMsg(`${approved ? 'Authorized' : 'Rejected'} task ${taskId.slice(0, 8)}...`);
    setTimeout(() => setActionSuccessMsg(null), 3500);
  };

  return (
    <div style={{
      background: '#0d1320',
      border: '1px solid #1a253a',
      borderRadius: '16px',
      padding: '20px',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
              Approval queue
            </h3>
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 800,
              padding: '2px 8px',
              borderRadius: '9999px',
              background: totalPending > 0 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
              color: totalPending > 0 ? '#fbbf24' : '#34d399',
              border: totalPending > 0 ? '1px solid rgba(245, 158, 11, 0.35)' : '1px solid rgba(16, 185, 129, 0.35)',
              letterSpacing: '0.04em'
            }}>
              {totalPending} PENDING
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
            Sensitive actions paused for human review
          </p>
        </div>
      </div>

      {/* Success Notification Banner */}
      {actionSuccessMsg && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.74rem',
          color: '#34d399',
          marginBottom: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span>✓</span> {actionSuccessMsg}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.12)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.74rem',
          color: '#fb7185',
          marginBottom: '10px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && approvals.length === 0 && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          flex: 1,
          padding: '30px 10px',
          color: '#64748b',
          fontSize: '0.78rem'
        }}>
          <div style={{ width: '20px', height: '20px', border: '2px solid #23314c', borderTopColor: '#38bdf8', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '8px' }}></div>
          Syncing approval queue...
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && approvals.length === 0 && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          flex: 1,
          padding: '36px 16px',
          textAlign: 'center',
          background: '#090d16',
          borderRadius: '12px',
          border: '1px solid #151e30'
        }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '50%',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#10b981',
            fontSize: '1.25rem',
            marginBottom: '10px'
          }}>
            🛡️
          </div>
          <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '4px' }}>
            No Pending Escalations
          </div>
          <p style={{ fontSize: '0.72rem', color: '#64748b', maxWidth: '280px', lineHeight: 1.4, marginBottom: '12px' }}>
            All agents are executing within autonomous safety policy limits. High-risk operations will pause here.
          </p>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.65rem',
            fontWeight: 700,
            color: '#34d399',
            background: 'rgba(16, 185, 129, 0.1)',
            padding: '3px 10px',
            borderRadius: '9999px',
            border: '1px solid rgba(16, 185, 129, 0.25)'
          }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#10b981' }}></span>
            Policy Gate Active
          </div>
        </div>
      )}

      {/* Populated Approvals List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', flex: 1 }}>
        {approvals.map((item) => {
          const isInspecting = inspectingTaskId === item.task_id;
          const isHighRisk = item.risk_level.toUpperCase() === 'HIGH';
          const riskColor = isHighRisk ? '#f43f5e' : '#f59e0b';

          return (
            <div
              key={item.task_id}
              style={{
                background: '#090d16',
                border: `1px solid ${isInspecting ? '#38bdf8' : '#1a253a'}`,
                borderRadius: '12px',
                padding: '12px 14px',
                transition: 'all 0.15s ease',
              }}
            >
              {/* Header: Tool & Risk Badge */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: riskColor,
                  }}></span>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9' }}>
                    {item.tool_name}
                  </span>
                </div>
                <span style={{
                  fontSize: '0.62rem',
                  fontWeight: 800,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: `${riskColor}22`,
                  color: riskColor,
                  border: `1px solid ${riskColor}44`,
                }}>
                  {item.risk_level}
                </span>
              </div>

              {/* Goal & Reason */}
              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '2px' }}>
                {item.reason}
              </div>
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '10px' }}>
                Task: {item.goal.slice(0, 48)}{item.goal.length > 48 ? '...' : ''}
              </div>

              {/* Inspect Details Drawer */}
              {isInspecting && (
                <div style={{
                  background: '#0d1320',
                  border: '1px solid #23314c',
                  borderRadius: '8px',
                  padding: '10px',
                  marginBottom: '10px',
                  fontSize: '0.72rem'
                }}>
                  <div style={{ fontWeight: 700, color: '#94a3b8', marginBottom: '4px' }}>
                    PROPOSED ARGUMENTS:
                  </div>
                  <pre style={{
                    background: '#060910',
                    padding: '8px',
                    borderRadius: '6px',
                    fontSize: '0.68rem',
                    color: '#38bdf8',
                    overflowX: 'auto',
                    marginBottom: '8px'
                  }}>
                    {JSON.stringify(item.arguments, null, 2)}
                  </pre>

                  <div style={{ marginBottom: '8px' }}>
                    <label style={{ display: 'block', fontSize: '0.68rem', color: '#64748b', marginBottom: '4px' }}>
                      Audit Justification / Feedback Note:
                    </label>
                    <input
                      type="text"
                      placeholder="E.g., Authorized for maintenance window..."
                      value={operatorFeedback}
                      onChange={(e) => setOperatorFeedback(e.target.value)}
                      style={{
                        width: '100%',
                        background: '#060910',
                        border: '1px solid #1a2438',
                        borderRadius: '6px',
                        padding: '6px 8px',
                        color: '#f1f5f9',
                        fontSize: '0.72rem',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      disabled={isSubmitting}
                      onClick={() => handleDetailedDecision(item.task_id, true)}
                      style={{
                        flex: 1,
                        background: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '5px 10px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        opacity: isSubmitting ? 0.6 : 1
                      }}
                    >
                      {isSubmitting ? 'Resuming...' : 'Confirm Approval'}
                    </button>
                    <button
                      disabled={isSubmitting}
                      onClick={() => handleDetailedDecision(item.task_id, false)}
                      style={{
                        flex: 1,
                        background: 'rgba(244, 63, 94, 0.2)',
                        color: '#fb7185',
                        border: '1px solid rgba(244, 63, 94, 0.4)',
                        borderRadius: '6px',
                        padding: '5px 10px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        opacity: isSubmitting ? 0.6 : 1
                      }}
                    >
                      Confirm Rejection
                    </button>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  disabled={isSubmitting}
                  onClick={() => handleQuickApprove(item.task_id)}
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '5px 12px',
                    fontSize: '0.74rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    opacity: isSubmitting ? 0.6 : 1
                  }}
                >
                  {isSubmitting ? '...' : 'Approve'}
                </button>
                <button
                  disabled={isSubmitting}
                  onClick={() => handleQuickReject(item.task_id)}
                  style={{
                    background: '#141d2e',
                    color: '#fb7185',
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                    borderRadius: '6px',
                    padding: '5px 10px',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Reject
                </button>
                <button
                  onClick={() => setInspectingTaskId(isInspecting ? null : item.task_id)}
                  style={{
                    background: isInspecting ? '#1f2b42' : '#131b2c',
                    color: isInspecting ? '#38bdf8' : '#94a3b8',
                    border: `1px solid ${isInspecting ? '#38bdf8' : '#23314c'}`,
                    borderRadius: '6px',
                    padding: '5px 10px',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {isInspecting ? 'Close' : 'Review'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
