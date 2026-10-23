import React from 'react';
import { AgentMetricItem } from '../types';

interface MeshAgentFleetTableProps {
  agents?: AgentMetricItem[];
  isLoading?: boolean;
  onNewAgent?: () => void;
}

export const MeshAgentFleetTable: React.FC<MeshAgentFleetTableProps> = ({
  agents = [],
  isLoading = false,
  onNewAgent,
}) => {
  const getUsageColor = (assignedAgent: string) => {
    switch (assignedAgent) {
      case 'researcher':
        return 'linear-gradient(90deg, #0284c7, #38bdf8)';
      case 'coder':
        return 'linear-gradient(90deg, #10b981, #34d399)';
      case 'reviewer':
        return 'linear-gradient(90deg, #8b5cf6, #c084fc)';
      case 'planner':
      default:
        return 'linear-gradient(90deg, #f59e0b, #fbbf24)';
    }
  };

  return (
    <div style={{
      background: '#0d1320',
      border: '1px solid #1a253a',
      borderRadius: '16px',
      padding: '20px',
      marginTop: '20px'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
            Agent fleet
          </h3>
          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
            Live performance across production agents substantiated by database telemetry
          </p>
        </div>

        <button
          onClick={onNewAgent}
          style={{
            background: 'linear-gradient(135deg, #0284c7, #2563eb)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '8px',
            padding: '6px 14px',
            fontSize: '0.78rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
          }}
        >
          <span>+</span> New mission
        </button>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1a253a', color: '#64748b', fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              <th style={{ padding: '10px 14px' }}>AGENT</th>
              <th style={{ padding: '10px 14px' }}>STATUS</th>
              <th style={{ padding: '10px 14px' }}>RUNS</th>
              <th style={{ padding: '10px 14px' }}>SUCCESS</th>
              <th style={{ padding: '10px 14px' }}>CAPACITY</th>
              <th style={{ padding: '10px 14px' }}>COST / 24H</th>
              <th style={{ padding: '10px 14px' }}>LAST ACTIVE</th>
              <th style={{ padding: '10px 14px', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                  Loading agent fleet metrics...
                </td>
              </tr>
            ) : agents.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                  No agents active yet. Dispatch a mission to populate fleet telemetry.
                </td>
              </tr>
            ) : (
              agents.map((agent) => (
                <tr
                  key={agent.id}
                  style={{
                    borderBottom: '1px solid #141c2c',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = '#111828'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  {/* Agent Name & Role */}
                  <td style={{ padding: '14px' }}>
                    <div style={{ fontWeight: 700, color: '#f1f5f9' }}>{agent.name}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{agent.role}</div>
                  </td>

                  {/* Status Pill */}
                  <td style={{ padding: '14px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      background: agent.status_type === 'running' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                      color: agent.status_type === 'running' ? '#34d399' : '#94a3b8',
                      border: agent.status_type === 'running' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(100, 116, 139, 0.3)',
                    }}>
                      <span style={{
                        width: '5px',
                        height: '5px',
                        borderRadius: '50%',
                        background: agent.status_type === 'running' ? '#10b981' : '#64748b',
                      }}></span>
                      {agent.status}
                    </span>
                  </td>

                  {/* Runs */}
                  <td style={{ padding: '14px', color: '#cbd5e1', fontWeight: 600 }}>
                    {agent.runs}
                  </td>

                  {/* Success Rate */}
                  <td style={{ padding: '14px', color: agent.success_rate > 0 ? '#10b981' : '#64748b', fontWeight: 700 }}>
                    {agent.runs > 0 ? `${agent.success_rate.toFixed(1)}%` : '—'}
                  </td>

                  {/* Usage Progress Bar */}
                  <td style={{ padding: '14px', minWidth: '120px' }}>
                    <div style={{
                      width: '100%',
                      height: '5px',
                      background: '#1a2438',
                      borderRadius: '9999px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${Math.max(agent.usage_percent, 5)}%`,
                        height: '100%',
                        background: getUsageColor(agent.assigned_agent),
                        borderRadius: '9999px',
                      }}></div>
                    </div>
                  </td>

                  {/* Cost */}
                  <td style={{ padding: '14px', color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}>
                    ${agent.cost_usd.toFixed(2)}
                  </td>

                  {/* Updated */}
                  <td style={{ padding: '14px', color: '#64748b', fontSize: '0.72rem' }}>
                    {agent.last_active || 'No runs'}
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '14px', textAlign: 'right' }}>
                    <button style={{
                      background: '#141d2e',
                      border: '1px solid #222f46',
                      borderRadius: '6px',
                      color: '#94a3b8',
                      padding: '3px 8px',
                      fontSize: '0.7rem',
                      cursor: 'pointer'
                    }}>
                      ⋯
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
