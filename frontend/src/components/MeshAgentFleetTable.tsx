import React from 'react';

interface MeshAgentFleetTableProps {
  onNewAgent?: () => void;
}

export const MeshAgentFleetTable: React.FC<MeshAgentFleetTableProps> = ({ onNewAgent }) => {
  const agents = [
    {
      id: 'agent-1',
      name: 'Research Scout',
      role: 'Web & knowledge retrieval',
      status: 'Running',
      statusType: 'running',
      runs: '1,264',
      success: '99.1%',
      usage: 78,
      usageColor: 'linear-gradient(90deg, #0284c7, #38bdf8)',
      cost: '$81.20',
      updated: '1m ago',
    },
    {
      id: 'agent-2',
      name: 'Finance Guard',
      role: 'Refund & billing policy',
      status: 'Review',
      statusType: 'review',
      runs: '462',
      success: '92.4%',
      usage: 45,
      usageColor: 'linear-gradient(90deg, #f59e0b, #fbbf24)',
      cost: '$43.10',
      updated: '7m ago',
    },
    {
      id: 'agent-3',
      name: 'Success Hub',
      role: 'Renewal & expansion',
      status: 'Running',
      statusType: 'running',
      runs: '896',
      success: '98.7%',
      usage: 62,
      usageColor: 'linear-gradient(90deg, #8b5cf6, #c084fc)',
      cost: '$64.14',
      updated: '2m ago',
    },
    {
      id: 'agent-4',
      name: 'Coder Sentinel',
      role: 'AST verification & sandbox',
      status: 'Running',
      statusType: 'running',
      runs: '730',
      success: '99.5%',
      usage: 84,
      usageColor: 'linear-gradient(90deg, #10b981, #34d399)',
      cost: '$52.80',
      updated: 'Just now',
    },
  ];

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
            Live performance across production agents
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
          <span>+</span> New agent
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
              <th style={{ padding: '10px 14px' }}>USAGE</th>
              <th style={{ padding: '10px 14px' }}>COST / 24H</th>
              <th style={{ padding: '10px 14px' }}>UPDATED</th>
              <th style={{ padding: '10px 14px', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
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
                    background: agent.statusType === 'running' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    color: agent.statusType === 'running' ? '#34d399' : '#fbbf24',
                    border: agent.statusType === 'running' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)',
                  }}>
                    <span style={{
                      width: '5px',
                      height: '5px',
                      borderRadius: '50%',
                      background: agent.statusType === 'running' ? '#10b981' : '#f59e0b',
                    }}></span>
                    {agent.status}
                  </span>
                </td>

                {/* Runs */}
                <td style={{ padding: '14px', color: '#cbd5e1', fontWeight: 600 }}>
                  {agent.runs}
                </td>

                {/* Success Rate */}
                <td style={{ padding: '14px', color: '#10b981', fontWeight: 700 }}>
                  {agent.success}
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
                      width: `${agent.usage}%`,
                      height: '100%',
                      background: agent.usageColor,
                      borderRadius: '9999px',
                    }}></div>
                  </div>
                </td>

                {/* Cost */}
                <td style={{ padding: '14px', color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}>
                  {agent.cost}
                </td>

                {/* Updated */}
                <td style={{ padding: '14px', color: '#64748b', fontSize: '0.72rem' }}>
                  {agent.updated}
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
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
