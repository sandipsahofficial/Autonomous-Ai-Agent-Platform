import React from 'react';

interface MeshStatCardsProps {
  activeCount?: number;
  successRate?: number;
  avgCost?: number;
  pendingApprovals?: number;
}

export const MeshStatCards: React.FC<MeshStatCardsProps> = ({
  activeCount = 12,
  successRate = 98.4,
  avgCost = 0.42,
  pendingApprovals = 3,
}) => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '14px',
      marginBottom: '20px'
    }}>
      {/* 1. ACTIVE AGENTS */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '16px 18px',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      }}>
        <div style={{
          fontSize: '0.68rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: '8px'
        }}>
          ACTIVE AGENTS
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>
              {activeCount}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#06b6d4', marginTop: '6px' }}>
              +2 this week
            </div>
          </div>
          {/* Sparkline */}
          <svg width="60" height="28" viewBox="0 0 60 28">
            <polyline
              fill="none"
              stroke="#06b6d4"
              strokeWidth="2"
              points="0,22 12,18 24,20 36,12 48,15 60,6"
            />
          </svg>
        </div>
      </div>

      {/* 2. SUCCESS RATE */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '16px 18px',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      }}>
        <div style={{
          fontSize: '0.68rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: '8px'
        }}>
          SUCCESS RATE
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>
              {successRate}%
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#34d399',
                border: '1px solid rgba(16, 185, 129, 0.3)'
              }}>
                +1.2%
              </span>
            </div>
          </div>
          {/* Sparkline */}
          <svg width="60" height="28" viewBox="0 0 60 28">
            <polyline
              fill="none"
              stroke="#10b981"
              strokeWidth="2"
              points="0,24 12,20 24,22 36,16 48,10 60,4"
            />
          </svg>
        </div>
      </div>

      {/* 3. AVG. RUN COST */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '16px 18px',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      }}>
        <div style={{
          fontSize: '0.68rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: '8px'
        }}>
          AVG. RUN COST
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>
              ${avgCost.toFixed(2)}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#34d399',
                border: '1px solid rgba(16, 185, 129, 0.3)'
              }}>
                -8.1%
              </span>
            </div>
          </div>
          {/* Sparkline */}
          <svg width="60" height="28" viewBox="0 0 60 28">
            <polyline
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2"
              points="0,10 12,14 24,12 36,18 48,16 60,22"
            />
          </svg>
        </div>
      </div>

      {/* 4. HUMAN ESCALATIONS */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '16px 18px',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      }}>
        <div style={{
          fontSize: '0.68rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: '8px'
        }}>
          HUMAN ESCALATIONS
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>
              {pendingApprovals}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: 'rgba(245, 158, 11, 0.15)',
                color: '#fbbf24',
                border: '1px solid rgba(245, 158, 11, 0.3)'
              }}>
                Action needed
              </span>
            </div>
          </div>
          {/* Sparkline */}
          <svg width="60" height="28" viewBox="0 0 60 28">
            <polyline
              fill="none"
              stroke="#fbbf24"
              strokeWidth="2"
              points="0,18 12,14 24,19 36,10 48,12 60,6"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};
