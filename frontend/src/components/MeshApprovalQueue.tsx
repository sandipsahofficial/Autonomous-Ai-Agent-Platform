import React from 'react';
import { PendingApproval } from '../types';

interface MeshApprovalQueueProps {
  realPendingApproval?: PendingApproval | null;
  onApproveReal?: (approved: boolean, comment?: string) => void;
  isSubmitting?: boolean;
}

export const MeshApprovalQueue: React.FC<MeshApprovalQueueProps> = ({
  realPendingApproval,
  onApproveReal,
  isSubmitting,
}) => {
  // Mock items matching the user's screenshot
  const staticItems = [
    {
      id: 'appr-1',
      agent: 'Finance Agent',
      risk: 'HIGH',
      riskColor: '#f43f5e',
      action: 'Issue refund • $2,450',
      meta: 'Customer: Yamada • 11m ago',
    },
    {
      id: 'appr-2',
      agent: 'Success Agent',
      risk: 'MED',
      riskColor: '#f59e0b',
      action: 'Send renewal proposal',
      meta: 'Contract terms + pricing • 34m ago',
    },
    {
      id: 'appr-3',
      agent: 'Ops Agent',
      risk: 'HIGH',
      riskColor: '#f43f5e',
      action: 'Update production config',
      meta: 'Workspace root .env • 1m ago',
    },
  ];

  const totalPending = (realPendingApproval ? 1 : 0) + staticItems.length;

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
      {/* Header matching screenshot */}
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
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#fbbf24',
              border: '1px solid rgba(245, 158, 11, 0.35)',
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

      {/* Approvals List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto' }}>
        
        {/* Real Live Backend Approval if one is currently paused in LangGraph */}
        {realPendingApproval && (
          <div style={{
            background: 'rgba(244, 63, 94, 0.08)',
            border: '1px solid rgba(244, 63, 94, 0.5)',
            borderRadius: '12px',
            padding: '12px 14px',
            boxShadow: '0 0 16px rgba(244, 63, 94, 0.2)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#fb7185' }}>
                LIVE RUN ESCALATION
              </span>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'rgba(244, 63, 94, 0.2)',
                color: '#f43f5e',
              }}>
                {realPendingApproval.risk_level}
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff', marginBottom: '2px' }}>
              Tool: {realPendingApproval.tool_name}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '8px' }}>
              {realPendingApproval.reason || JSON.stringify(realPendingApproval.arguments)}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                disabled={isSubmitting}
                onClick={() => onApproveReal && onApproveReal(true, 'Approved via MESH Dashboard')}
                style={{
                  flex: 1,
                  background: '#10b981',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {isSubmitting ? 'Resuming...' : 'Approve'}
              </button>
              <button
                disabled={isSubmitting}
                onClick={() => onApproveReal && onApproveReal(false, 'Rejected via MESH Dashboard')}
                style={{
                  background: '#1e293b',
                  color: '#fb7185',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Reject
              </button>
            </div>
          </div>
        )}

        {/* Static Approvals matching screenshot */}
        {staticItems.map((item, idx) => (
          <div
            key={item.id}
            style={{
              background: '#090d16',
              border: '1px solid #1a253a',
              borderRadius: '12px',
              padding: '12px 14px',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: item.riskColor,
                }}></span>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9' }}>
                  {item.agent}
                </span>
              </div>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '4px',
                background: `${item.riskColor}22`,
                color: item.riskColor,
                border: `1px solid ${item.riskColor}44`,
              }}>
                {item.risk}
              </span>
            </div>

            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '2px' }}>
              {item.action}
            </div>
            <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '10px' }}>
              {item.meta}
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              {idx === 0 ? (
                <>
                  <button
                    onClick={() => alert(`Approved ${item.action}`)}
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
                    }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => alert(`Reviewing arguments for ${item.action}`)}
                    style={{
                      background: '#131b2c',
                      color: '#94a3b8',
                      border: '1px solid #23314c',
                      borderRadius: '6px',
                      padding: '5px 10px',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Review
                  </button>
                </>
              ) : (
                <button
                  onClick={() => alert(`Reviewing arguments for ${item.action}`)}
                  style={{
                    width: '100%',
                    background: '#131b2c',
                    color: '#94a3b8',
                    border: '1px solid #23314c',
                    borderRadius: '6px',
                    padding: '5px 10px',
                    fontSize: '0.74rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Review
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
