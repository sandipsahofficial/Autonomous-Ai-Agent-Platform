import React from 'react';
import { FleetMetrics } from '../types';

interface MeshStatCardsProps {
  metrics?: FleetMetrics | null;
  activeCount?: number;
  successRate?: number;
  avgCost?: number;
  pendingApprovals?: number;
  isLoading?: boolean;
}

export const MeshStatCards: React.FC<MeshStatCardsProps> = ({
  metrics,
  activeCount = 0,
  successRate = 0.0,
  avgCost = 0.0,
  pendingApprovals = 0,
  isLoading = false,
}) => {
  const displayActive = metrics ? metrics.active_tasks : activeCount;
  const displaySuccess = metrics ? metrics.completion_rate : successRate;
  const displayCost = metrics ? metrics.average_cost_usd : avgCost;
  const displayApprovals = metrics ? metrics.pending_approvals : pendingApprovals;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '14px',
      marginBottom: '20px'
    }}>
      {/* 1. ACTIVE MISSIONS / AGENTS */}
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
          ACTIVE MISSIONS
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>
              {isLoading ? '...' : displayActive}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#06b6d4', marginTop: '6px' }}>
              {metrics ? `${metrics.total_tasks} total missions` : 'Real-time telemetry'}
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
              {isLoading ? '...' : `${displaySuccess.toFixed(1)}%`}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: displaySuccess > 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                color: displaySuccess > 0 ? '#34d399' : '#94a3b8',
                border: displaySuccess > 0 ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(100, 116, 139, 0.3)'
              }}>
                {metrics ? `${metrics.completed_tasks} completed / ${metrics.failed_tasks} failed` : 'Recorded executions'}
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
              {isLoading ? '...' : `$${displayCost.toFixed(2)}`}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)'
              }}>
                {metrics ? `${metrics.total_tokens.toLocaleString()} tokens` : 'API Model Spend'}
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
              {isLoading ? '...' : displayApprovals}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '9999px',
                background: displayApprovals > 0 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                color: displayApprovals > 0 ? '#fbbf24' : '#34d399',
                border: displayApprovals > 0 ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)'
              }}>
                {displayApprovals > 0 ? 'Action needed' : 'Queue clear'}
              </span>
            </div>
          </div>
          {/* Sparkline */}
          <svg width="60" height="28" viewBox="0 0 60 28">
            <polyline
              fill="none"
              stroke={displayApprovals > 0 ? '#fbbf24' : '#10b981'}
              strokeWidth="2"
              points="0,18 12,14 24,19 36,10 48,12 60,6"
            />
          </svg>
        </div>
      </div>
    </div>
  );
};
