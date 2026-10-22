import React, { useState } from 'react';
import { PendingApproval } from '../types';

interface Props {
  approval: PendingApproval;
  onDecision: (approved: boolean, feedback?: string) => Promise<void>;
  isSubmitting: boolean;
}

export const HumanApprovalModal: React.FC<Props> = ({
  approval,
  onDecision,
  isSubmitting,
}) => {
  const [feedback, setFeedback] = useState('');

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-rose)' }}>
            ⚠️ High-Risk Action Gate
          </h3>
          <span className="badge badge-high">
            {approval.risk_level}
          </span>
        </div>

        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          The autonomous workflow has been <strong>paused</strong>. An agent requested an action that requires explicit operator sign-off before execution.
        </p>

        {/* Action Details */}
        <div style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.85rem' }}>
          <div style={{ marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-dim)' }}>Target Tool: </span>
            <code style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{approval.tool_name}</code>
          </div>
          <div style={{ marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-dim)' }}>Risk Reason: </span>
            <span style={{ color: 'var(--text-main)' }}>{approval.reason}</span>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)' }}>Arguments:</span>
            <pre style={{ marginTop: '4px', padding: '8px', background: 'var(--bg-primary)', borderRadius: '4px', fontSize: '0.75rem', overflowX: 'auto' }}>
              {JSON.stringify(approval.arguments, null, 2)}
            </pre>
          </div>
        </div>

        {/* Operator Feedback */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
            Optional Feedback / Rejection Reason:
          </label>
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="e.g., Target file is outside permissions or approved for maintenance"
            style={{
              width: '100%',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '8px 12px',
              color: 'var(--text-main)',
              fontSize: '0.85rem',
              outline: 'none',
            }}
          />
        </div>

        {/* Decision Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => onDecision(false, feedback || 'Operator rejected this high-risk action')}
            className="btn btn-danger"
          >
            {isSubmitting ? 'Processing...' : 'Reject Action'}
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => onDecision(true, feedback || 'Approved by operator')}
            className="btn btn-primary"
            style={{ background: 'var(--accent-green)' }}
          >
            {isSubmitting ? 'Processing...' : 'Approve Execution'}
          </button>
        </div>
      </div>
    </div>
  );
};
