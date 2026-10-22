import React, { useState } from 'react';
import { AuditLog } from '../types';

interface Props {
  logs: AuditLog[];
  onFilterChange: (riskLevel?: string) => void;
  selectedFilter?: string;
}

export const AuditLogViewer: React.FC<Props> = ({
  logs,
  onFilterChange,
  selectedFilter,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const getBadgeClass = (level: string) => {
    switch (level) {
      case 'HIGH':
        return 'badge-high';
      case 'MEDIUM':
        return 'badge-medium';
      default:
        return 'badge-low';
    }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
            System Safety & Action Audit Trail
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Immutable record of every agent action, risk score evaluation, and operator decision.
          </p>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '8px' }}>
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((filter) => {
            const isSelected = (filter === 'ALL' && !selectedFilter) || selectedFilter === filter;
            return (
              <button
                key={filter}
                className="btn btn-secondary"
                style={{
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                  borderColor: isSelected ? 'var(--accent-blue)' : 'var(--border)',
                  color: isSelected ? 'var(--accent-blue)' : 'var(--text-main)',
                }}
                onClick={() => onFilterChange(filter === 'ALL' ? undefined : filter)}
              >
                {filter}
              </button>
            );
          })}
        </div>
      </div>

      {logs.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          No audit log events recorded yet.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-dim)' }}>
                <th style={{ padding: '8px 12px' }}>Timestamp</th>
                <th style={{ padding: '8px 12px' }}>Agent</th>
                <th style={{ padding: '8px 12px' }}>Action</th>
                <th style={{ padding: '8px 12px' }}>Risk</th>
                <th style={{ padding: '8px 12px' }}>Payload Preview</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <React.Fragment key={log.id}>
                  <tr
                    onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      cursor: 'pointer',
                      background: expandedId === log.id ? 'var(--bg-tertiary)' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '10px 12px', whiteSpace: 'nowrap', color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>
                      {log.agent_name}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>
                      {log.action_type}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className={`badge ${getBadgeClass(log.risk_level)}`}>
                        {log.risk_level}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {JSON.stringify(log.payload || {})}
                    </td>
                  </tr>

                  {expandedId === log.id && (
                    <tr style={{ background: 'var(--bg-primary)' }}>
                      <td colSpan={5} style={{ padding: '12px', borderBottom: '1px solid var(--border)' }}>
                        <pre style={{ fontSize: '0.75rem', padding: '10px', background: 'var(--bg-secondary)', borderRadius: '6px', overflowX: 'auto' }}>
                          {JSON.stringify(log.payload, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
