import React from 'react';

interface MeshSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  pendingApprovalsCount: number;
}

export const MeshSidebar: React.FC<MeshSidebarProps> = ({
  activeTab,
  onTabChange,
  pendingApprovalsCount,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: '▦' },
    { id: 'workflows', label: 'Workflows', icon: '☍' },
    { id: 'fleet', label: 'Agent fleet', icon: '☵' },
    { id: 'runs', label: 'Runs & traces', icon: '◰' },
    { id: 'knowledge', label: 'Knowledge & Docs', icon: '◫' },
    { id: 'schedules', label: 'Schedules', icon: '⏱' },
    { id: 'templates', label: 'Templates', icon: '📑' },
    { id: 'evaluations', label: 'Evaluations', icon: '📊' },
    { id: 'guardrails', label: 'Guardrails', icon: '🛡' },
    { id: 'audit', label: 'Audit Log', icon: '📜' },
  ];

  return (
    <div style={{
      width: '240px',
      background: '#090d16',
      borderRight: '1px solid #172033',
      padding: '24px 16px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      minHeight: '100%',
    }}>
      <div>
        {/* Brand Logo & Agent OS tag */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px', paddingLeft: '8px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 800,
            fontSize: '1rem',
            boxShadow: '0 4px 14px rgba(2, 132, 199, 0.4)'
          }}>
            ⬡
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff' }}>
                MESH
              </span>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                letterSpacing: '0.04em'
              }}>
                AGENT OS
              </span>
            </div>
          </div>
        </div>

        {/* WORKSPACE Navigation */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            color: '#475569',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '10px',
            paddingLeft: '10px'
          }}>
            WORKSPACE
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    fontSize: '0.82rem',
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? '#ffffff' : '#94a3b8',
                    background: isActive ? 'linear-gradient(90deg, #1e293b, #172033)' : 'transparent',
                    border: isActive ? '1px solid #334155' : '1px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    textAlign: 'left',
                    width: '100%'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = '#0e1422';
                      e.currentTarget.style.color = '#cbd5e1';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#94a3b8';
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '0.9rem', color: isActive ? '#38bdf8' : '#64748b' }}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </div>
                  {item.id === 'guardrails' && pendingApprovalsCount > 0 && (
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '9999px',
                      background: 'rgba(245, 158, 11, 0.2)',
                      color: '#fbbf24',
                      border: '1px solid rgba(245, 158, 11, 0.4)'
                    }}>
                      {pendingApprovalsCount}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* TEAM Navigation */}
        <div>
          <div style={{
            fontSize: '0.65rem',
            fontWeight: 700,
            color: '#475569',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: '10px',
            paddingLeft: '10px'
          }}>
            TEAM
          </div>
          <button
            onClick={() => onTabChange('settings')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '9px 12px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 500,
              color: '#94a3b8',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              width: '100%',
              textAlign: 'left'
            }}
          >
            <span style={{ fontSize: '0.9rem', color: '#64748b' }}>⚙</span>
            <span>Settings</span>
          </button>
        </div>
      </div>

      {/* Bottom Token Budget Card (matching screenshot bottom left) */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '12px',
        padding: '14px',
        marginTop: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{
            fontSize: '0.62rem',
            fontWeight: 700,
            padding: '1px 6px',
            borderRadius: '4px',
            background: 'rgba(37, 99, 235, 0.2)',
            color: '#60a5fa',
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}>
            PRODUCTION
          </span>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Active Fleet</span>
        </div>
        <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f1f5f9', marginBottom: '4px' }}>
          1.8M tokens
        </div>
        <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '8px' }}>
          38% of monthly budget
        </div>
        {/* Progress bar */}
        <div style={{
          width: '100%',
          height: '6px',
          background: '#1a2336',
          borderRadius: '9999px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: '38%',
            height: '100%',
            background: 'linear-gradient(90deg, #0284c7, #38bdf8)',
            borderRadius: '9999px'
          }}></div>
        </div>
      </div>
    </div>
  );
};
