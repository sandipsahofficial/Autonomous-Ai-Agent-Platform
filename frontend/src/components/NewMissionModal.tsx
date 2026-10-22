import React, { useState } from 'react';

interface NewMissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (goal: string) => void;
  isDeploying: boolean;
}

export const NewMissionModal: React.FC<NewMissionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isDeploying,
}) => {
  const [goal, setGoal] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    onSubmit(goal.trim());
    setGoal('');
  };

  const sampleGoals = [
    'Research Python asyncio event loops, coroutines, and TaskGroup semantics',
    'Design and implement a robust, thread-safe LRU Cache with capacity eviction',
    'Audit workspace security posture and verify parameterized SQL defenses',
  ];

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(5, 7, 12, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '16px'
    }}>
      <div style={{
        background: '#0d1320',
        border: '1px solid #23314c',
        borderRadius: '20px',
        width: '100%',
        maxWidth: '560px',
        padding: '24px',
        boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc' }}>
              Dispatch New Agent Mission
            </h3>
            <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
              Planner will decompose the goal and coordinate Researcher, Coder, and Reviewer.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              fontSize: '1.2rem',
              cursor: 'pointer'
            }}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '6px' }}>
              MISSION GOAL & SPECIFICATION
            </label>
            <textarea
              rows={4}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="E.g., Implement a thread-safe LRU Cache and verify against edge cases..."
              style={{
                width: '100%',
                background: '#090d16',
                border: '1px solid #1a253a',
                borderRadius: '10px',
                padding: '12px',
                color: '#f8fafc',
                fontSize: '0.85rem',
                fontFamily: 'inherit',
                outline: 'none',
                resize: 'none'
              }}
            />
          </div>

          {/* Quick preset suggestions */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '0.68rem', color: '#64748b', marginBottom: '6px' }}>Quick Presets:</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {sampleGoals.map((g, i) => (
                <button
                  type="button"
                  key={i}
                  onClick={() => setGoal(g)}
                  style={{
                    background: '#111827',
                    border: '1px solid #1f2937',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    fontSize: '0.72rem',
                    color: '#94a3b8',
                    textAlign: 'left',
                    cursor: 'pointer'
                  }}
                >
                  ⚡ {g}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: '#141c2c',
                border: '1px solid #23314c',
                borderRadius: '8px',
                padding: '8px 16px',
                fontSize: '0.82rem',
                color: '#94a3b8',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isDeploying || !goal.trim()}
              style={{
                background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 18px',
                fontSize: '0.82rem',
                fontWeight: 700,
                cursor: 'pointer',
                opacity: isDeploying || !goal.trim() ? 0.6 : 1,
              }}
            >
              {isDeploying ? 'Dispatching...' : 'Dispatch Mission →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
