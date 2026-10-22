import React, { useState } from 'react';
import { Task } from '../types';

interface MeshMissionGraphProps {
  activeTask?: Task | null;
  onSelectNode?: (nodeName: string) => void;
}

export const MeshMissionGraph: React.FC<MeshMissionGraphProps> = ({
  activeTask,
  onSelectNode,
}) => {
  const [selectedNode, setSelectedNode] = useState<string>('Planner');

  const nodes = [
    {
      id: 'Planner',
      label: 'Planner',
      meta: 'Sub-task blueprint',
      icon: '☵',
      status: 'completed',
      x: 50,
      y: 90,
      color: '#38bdf8',
      desc: 'Decomposed high-level goal into parallel research and verification streams.',
    },
    {
      id: 'Research',
      label: 'Research',
      meta: '12 sources verified',
      icon: '🔍',
      status: 'completed',
      x: 180,
      y: 90,
      color: '#818cf8',
      desc: 'Gathered documentation, security specifications, and algorithmic benchmarks.',
    },
    {
      id: 'CRM',
      label: 'CRM',
      meta: 'Data pipeline synced',
      icon: '◫',
      status: 'active',
      x: 320,
      y: 40,
      color: '#34d399',
      desc: 'Extracted account health, stakeholder metrics, and renewal contract terms.',
    },
    {
      id: 'Risk',
      label: 'Risk',
      meta: 'Guardrail check',
      icon: '🛡',
      status: 'warning',
      x: 320,
      y: 140,
      color: '#fbbf24',
      desc: 'Evaluated action parameters against policy. Intercepted 1 sensitive call for human approval.',
    },
    {
      id: 'Writer',
      label: 'Writer',
      meta: 'Final output synthesis',
      icon: '✎',
      status: 'pending',
      x: 450,
      y: 90,
      color: '#c084fc',
      desc: 'Assembles validated multi-agent outputs into final verified deliverables.',
    },
  ];

  const handleNodeClick = (node: typeof nodes[0]) => {
    setSelectedNode(node.id);
    if (onSelectNode) onSelectNode(node.id);
  };

  const activeNodeData = nodes.find((n) => n.id === selectedNode) || nodes[0];

  return (
    <div style={{
      background: '#0d1320',
      border: '1px solid #1a253a',
      borderRadius: '16px',
      padding: '20px',
      position: 'relative',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}>
      {/* Header matching screenshot */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
              Live mission graph
            </h3>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 7px',
              borderRadius: '9999px',
              fontSize: '0.65rem',
              fontWeight: 800,
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              letterSpacing: '0.04em'
            }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#10b981' }}></span>
              LIVE
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
            {activeTask?.goal ? `Mission: ${activeTask.goal.slice(0, 48)}...` : 'Customer renewal intelligence • Run #R-2841'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <button style={{
            background: '#131b2c',
            border: '1px solid #23314c',
            borderRadius: '6px',
            color: '#94a3b8',
            fontSize: '0.72rem',
            padding: '4px 8px',
            cursor: 'pointer'
          }}>
            Inspect traces ↗
          </button>
        </div>
      </div>

      {/* Interactive Visual Graph Canvas */}
      <div style={{
        position: 'relative',
        width: '100%',
        minHeight: '200px',
        background: '#090d16',
        borderRadius: '12px',
        border: '1px solid #162034',
        padding: '16px',
        overflow: 'hidden'
      }}>
        {/* SVG Connecting Flow Lines */}
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }} viewBox="0 0 540 180" preserveAspectRatio="none">
          <defs>
            <linearGradient id="flowGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#818cf8" />
            </linearGradient>
            <linearGradient id="flowGradTop" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
            <linearGradient id="flowGradBottom" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#fbbf24" />
            </linearGradient>
            <linearGradient id="flowGradConverge" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#34d399" />
              <stop offset="100%" stopColor="#c084fc" />
            </linearGradient>
          </defs>

          {/* Line 1: Planner -> Research */}
          <path d="M 85 90 L 160 90" stroke="url(#flowGrad1)" strokeWidth="2" fill="none" className="flow-line" />
          
          {/* Line 2: Research -> CRM (top branch) */}
          <path d="M 215 90 C 260 90, 260 40, 300 40" stroke="url(#flowGradTop)" strokeWidth="2" fill="none" className="flow-line" />

          {/* Line 3: Research -> Risk (bottom branch) */}
          <path d="M 215 90 C 260 90, 260 140, 300 140" stroke="url(#flowGradBottom)" strokeWidth="2" fill="none" className="flow-line" />

          {/* Line 4: CRM -> Writer */}
          <path d="M 355 40 C 395 40, 395 90, 435 90" stroke="url(#flowGradConverge)" strokeWidth="2" fill="none" className="flow-line" />

          {/* Line 5: Risk -> Writer */}
          <path d="M 355 140 C 395 140, 395 90, 435 90" stroke="#fbbf24" strokeWidth="2" fill="none" strokeOpacity="0.8" className="flow-line" />
        </svg>

        {/* Node Buttons matching exact MESH design */}
        {nodes.map((node) => {
          const isSelected = selectedNode === node.id;
          return (
            <div
              key={node.id}
              onClick={() => handleNodeClick(node)}
              style={{
                position: 'absolute',
                left: `${(node.x / 540) * 88}%`,
                top: `${(node.y / 180) * 72}%`,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                zIndex: 10,
              }}
            >
              <div style={{
                background: isSelected ? '#1c2842' : '#111728',
                border: `1.5px solid ${isSelected ? node.color : '#23314c'}`,
                borderRadius: '10px',
                padding: '7px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: isSelected ? `0 0 16px ${node.color}55` : '0 4px 10px rgba(0,0,0,0.3)',
                transform: isSelected ? 'scale(1.05)' : 'scale(1)',
              }}>
                <span style={{
                  fontSize: '0.85rem',
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  background: `${node.color}22`,
                  color: node.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800
                }}>
                  {node.icon}
                </span>
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9', lineHeight: 1.1 }}>
                    {node.label}
                  </div>
                  <div style={{ fontSize: '0.62rem', color: '#64748b', marginTop: '2px' }}>
                    {node.meta}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Node Details Drawer */}
      <div style={{
        marginTop: '12px',
        padding: '10px 14px',
        background: '#0a0f1b',
        borderRadius: '8px',
        border: '1px solid #182236',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: activeNodeData.color, fontWeight: 700 }}>● {activeNodeData.label}:</span>
          <span style={{ color: '#94a3b8' }}>{activeNodeData.desc}</span>
        </div>
        <span style={{ fontSize: '0.68rem', color: '#64748b' }}>Status: {activeNodeData.status.toUpperCase()}</span>
      </div>
    </div>
  );
};
