import React from 'react';

interface MeshHeaderProps {
  onOpenNewMission: () => void;
}

export const MeshHeader: React.FC<MeshHeaderProps> = ({ onOpenNewMission }) => {
  return (
    <div style={{ marginBottom: '28px' }}>
      {/* Top Banner & Hero Section matching screenshot top */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '20px', marginBottom: '24px' }}>
        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 10px',
            borderRadius: '9999px',
            fontSize: '0.72rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            background: 'rgba(56, 189, 248, 0.12)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            marginBottom: '10px',
            textTransform: 'uppercase'
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#38bdf8' }}></span>
            AGENT OPERATING
          </div>
          <h1 style={{
            fontSize: '2.25rem',
            fontWeight: 800,
            letterSpacing: '-0.03em',
            color: '#ffffff',
            lineHeight: 1.15,
            marginBottom: '8px'
          }}>
            Orchestrate AI agents <br />
            with clarity and control.
          </h1>
          <p style={{
            color: '#94a3b8',
            fontSize: '0.95rem',
            maxWidth: '620px',
            lineHeight: 1.5,
            marginBottom: '14px'
          }}>
            MESH combines orchestration, live execution traces, human approvals, guardrails, and fleet health into one operational layer for production AI teams.
          </p>
          <button
            onClick={onOpenNewMission}
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
            }}
          >
            <span>⚡</span> Dispatch Agent Mission
          </button>
        </div>

        {/* Top-Right Floating MESH Network Mini Card (matching screenshot top-right) */}
        <div style={{
          background: '#0d1320',
          border: '1px solid #1c273e',
          borderRadius: '16px',
          padding: '14px 18px',
          minWidth: '240px',
          boxShadow: '0 12px 30px rgba(0,0,0,0.4)',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '6px',
                background: 'linear-gradient(135deg, #0284c7, #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: '0.75rem',
                fontWeight: 800
              }}>
                ⬡
              </div>
              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f1f5f9' }}>MESH</span>
            </div>
            <span style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Agent Operations</span>
          </div>

          {/* Glowing Constellation SVG */}
          <div style={{ height: '60px', width: '100%', position: 'relative' }}>
            <svg width="100%" height="60" viewBox="0 0 200 60">
              <line x1="25" y1="30" x2="70" y2="18" stroke="#06b6d4" strokeWidth="1.5" strokeOpacity="0.6" strokeDasharray="3 3" />
              <line x1="70" y1="18" x2="125" y2="40" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.6" />
              <line x1="70" y1="18" x2="165" y2="20" stroke="#38bdf8" strokeWidth="1.5" strokeOpacity="0.6" />
              <line x1="125" y1="40" x2="165" y2="20" stroke="#10b981" strokeWidth="1.5" strokeOpacity="0.6" />

              {/* Glowing Dots */}
              <circle cx="25" cy="30" r="4" fill="#38bdf8" />
              <circle cx="70" cy="18" r="5" fill="#8b5cf6" />
              <circle cx="125" cy="40" r="4" fill="#10b981" />
              <circle cx="165" cy="20" r="5" fill="#38bdf8" />
            </svg>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#64748b', marginTop: '2px' }}>
              <span>4 ACTIVE NODES</span>
              <span style={{ color: '#10b981' }}>● 100% HEALTH</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
