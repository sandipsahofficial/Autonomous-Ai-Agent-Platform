import React from 'react';

export const MeshMobileShowcase: React.FC = () => {
  return (
    <div style={{ marginTop: '48px', marginBottom: '32px' }}>
      {/* Section Header matching screenshot */}
      <div style={{ textAlign: 'center', marginBottom: '28px' }}>
        <div style={{
          fontSize: '0.68rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: '6px'
        }}>
          MOBILE CONTROL SURFACES
        </div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc', marginBottom: '6px' }}>
          Built for supervision, approvals, and intervention.
        </h2>
        <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: '580px', margin: '0 auto' }}>
          Each screen is composed around a state-specific operational task — not a scaled-down desktop dashboard.
        </p>
      </div>

      {/* 3 Mobile Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '20px',
        maxWidth: '1000px',
        margin: '0 auto'
      }}>
        {/* Mobile Screen 1: Approvals */}
        <div style={{
          background: '#090d16',
          border: '1px solid #1c273e',
          borderRadius: '24px',
          padding: '16px',
          boxShadow: '0 16px 36px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '440px'
        }}>
          <div>
            {/* Top Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f1f5f9' }}>
                Approvals
              </div>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '9999px',
                background: 'rgba(245, 158, 11, 0.2)',
                color: '#fbbf24',
              }}>
                3 PENDING
              </span>
            </div>
            <div style={{ fontSize: '0.68rem', color: '#64748b', marginBottom: '12px' }}>
              Human review for sensitive agent actions
            </div>

            {/* Approvals Items */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ background: '#0e1422', border: '1px solid #1e2a42', borderRadius: '10px', padding: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f1f5f9' }}>Finance Agent</span>
                  <span style={{ fontSize: '0.58rem', fontWeight: 800, color: '#f43f5e', background: 'rgba(244,63,94,0.15)', padding: '1px 4px', borderRadius: '4px' }}>HIGH RISK</span>
                </div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>Issue refund • $2,450</div>
                <div style={{ fontSize: '0.62rem', color: '#64748b', marginBottom: '6px' }}>Customer: Yamada • 11m ago</div>
                <button style={{ width: '100%', background: '#0284c7', color: '#fff', border: 'none', borderRadius: '6px', padding: '4px', fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer' }}>
                  Review
                </button>
              </div>

              <div style={{ background: '#0e1422', border: '1px solid #1e2a42', borderRadius: '10px', padding: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f1f5f9' }}>Success Agent</span>
                  <span style={{ fontSize: '0.58rem', fontWeight: 800, color: '#f59e0b', background: 'rgba(245,158,11,0.15)', padding: '1px 4px', borderRadius: '4px' }}>MEDIUM</span>
                </div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>Send renewal proposal</div>
                <button style={{ width: '100%', marginTop: '6px', background: '#172134', color: '#94a3b8', border: '1px solid #23314c', borderRadius: '6px', padding: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>
                  Review
                </button>
              </div>
            </div>
          </div>

          {/* Bottom Mobile Tab Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-around', paddingTop: '10px', borderTop: '1px solid #151e30', color: '#64748b', fontSize: '0.85rem' }}>
            <span style={{ color: '#38bdf8' }}>☵</span>
            <span>✓</span>
            <span>📈</span>
            <span>⚙</span>
          </div>
        </div>

        {/* Mobile Screen 2: Run #R-2841 (Execution Trace) */}
        <div style={{
          background: '#090d16',
          border: '1px solid #1c273e',
          borderRadius: '24px',
          padding: '16px',
          boxShadow: '0 16px 36px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '440px'
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f1f5f9' }}>
                Run #R-2841
              </div>
              <span style={{
                fontSize: '0.62rem',
                fontWeight: 800,
                padding: '2px 6px',
                borderRadius: '9999px',
                background: 'rgba(16, 185, 129, 0.2)',
                color: '#34d399',
              }}>
                LIVE
              </span>
            </div>

            {/* Run Target */}
            <div style={{ background: '#0e1422', border: '1px solid #1a253a', borderRadius: '8px', padding: '8px 10px', marginBottom: '12px' }}>
              <div style={{ fontSize: '0.62rem', color: '#64748b' }}>MISSION GOAL</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f1f5f9' }}>Protect renewal at Helio Labs</div>
              <div style={{ width: '100%', height: '4px', background: '#1c263c', borderRadius: '9999px', marginTop: '6px' }}>
                <div style={{ width: '70%', height: '100%', background: '#0284c7', borderRadius: '9999px' }}></div>
              </div>
            </div>

            {/* Execution Trace Steps */}
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748b', marginBottom: '6px' }}>
              EXECUTION TRACE
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              {[
                { name: 'Planner', latency: '0.8s', color: '#38bdf8' },
                { name: 'Research Scout', latency: '4.5s', color: '#818cf8' },
                { name: 'CRM Connector', latency: '2.1s', color: '#34d399' },
                { name: 'Risk Guard', latency: '1.1s', color: '#fbbf24' },
                { name: 'Status Agent', latency: '3.2s', color: '#c084fc' },
              ].map((step, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0c121e', padding: '6px 8px', borderRadius: '6px', fontSize: '0.7rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: step.color }}></span>
                    <span style={{ color: '#e2e8f0' }}>{step.name}</span>
                  </div>
                  <span style={{ color: '#64748b', fontFamily: 'JetBrains Mono, monospace' }}>{step.latency}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom Run Summary */}
          <div style={{ background: '#0b101c', border: '1px solid #172134', borderRadius: '8px', padding: '8px 10px', display: 'flex', justifyContent: 'space-around', textAlign: 'center', fontSize: '0.68rem' }}>
            <div>
              <div style={{ color: '#64748b' }}>LATENCY</div>
              <div style={{ fontWeight: 800, color: '#f1f5f9' }}>14.2s</div>
            </div>
            <div>
              <div style={{ color: '#64748b' }}>TOKENS</div>
              <div style={{ fontWeight: 800, color: '#38bdf8' }}>11k</div>
            </div>
            <div>
              <div style={{ color: '#64748b' }}>COST</div>
              <div style={{ fontWeight: 800, color: '#10b981' }}>$1.54</div>
            </div>
          </div>
        </div>

        {/* Mobile Screen 3: Fleet Health */}
        <div style={{
          background: '#090d16',
          border: '1px solid #1c273e',
          borderRadius: '24px',
          padding: '16px',
          boxShadow: '0 16px 36px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '440px'
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f1f5f9' }}>
                Fleet health
              </div>
              <span style={{ fontSize: '0.68rem', color: '#0284c7', fontWeight: 700 }}>
                + New agent
              </span>
            </div>

            {/* Health Stat */}
            <div style={{ background: '#0e1422', border: '1px solid #1a253a', borderRadius: '10px', padding: '10px', marginBottom: '12px' }}>
              <div style={{ fontSize: '0.62rem', color: '#64748b' }}>NETWORK HEALTH</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '2px' }}>
                <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#10b981' }}>98.4%</span>
                <span style={{ fontSize: '0.65rem', color: '#34d399', fontWeight: 700 }}>+1.2%</span>
              </div>
              {/* Mini vertical bar indicator */}
              <div style={{ display: 'flex', gap: '3px', marginTop: '6px', height: '14px', alignItems: 'flex-end' }}>
                {[6, 8, 12, 10, 14, 11, 14, 13, 14].map((h, idx) => (
                  <div key={idx} style={{ flex: 1, height: `${h}px`, background: '#10b981', borderRadius: '1px', opacity: 0.8 }}></div>
                ))}
              </div>
            </div>

            {/* Agent Health List */}
            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748b', marginBottom: '6px' }}>
              AGENTS
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              {[
                { name: 'Research Scout', rate: '96.1%' },
                { name: 'Finance Guard', rate: '92.4%' },
                { name: 'Success Hub', rate: '98.7%' },
                { name: 'Ops Sentinel', rate: '99.1%' },
              ].map((ag, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0c121e', padding: '6px 8px', borderRadius: '6px', fontSize: '0.7rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: '#10b981' }}></span>
                    <span style={{ color: '#e2e8f0' }}>{ag.name}</span>
                  </div>
                  <span style={{ color: '#10b981', fontWeight: 700 }}>{ag.rate}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Cost efficiency badge */}
          <div style={{ background: '#0b101c', border: '1px solid #1a2438', borderRadius: '8px', padding: '8px 10px', fontSize: '0.68rem', color: '#38bdf8', textAlign: 'center' }}>
            ⚡ Cost efficiency improved 12%
          </div>
        </div>
      </div>
    </div>
  );
};
