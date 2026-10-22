import React, { useState } from 'react';

interface Props {
  onSubmit: (goal: string) => Promise<void>;
  isLoading: boolean;
}

export const TaskSubmission: React.FC<Props> = ({ onSubmit, isLoading }) => {
  const [goal, setGoal] = useState('');

  const sampleGoals = [
    'Build an iterative Fibonacci solver in Python with unit tests',
    'Research Python asyncio best practices, event loops, and tasks',
    'Delete temporary old cache files from workspace',
    'Search for binary search algorithm details and implement it in Python',
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || isLoading) return;
    onSubmit(goal.trim());
    setGoal('');
  };

  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '8px' }}>
        Deploy Autonomous Multi-Agent Goal
      </h2>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '16px' }}>
        The Planner agent will decompose your goal into subtasks, routed to Researcher and Coder agents with Reviewer oversight and safety gate protection.
      </p>

      <form onSubmit={handleSubmit}>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Enter goal or prompt for the multi-agent system..."
          rows={3}
          style={{
            width: '100%',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            color: 'var(--text-main)',
            padding: '12px',
            fontSize: '0.95rem',
            resize: 'vertical',
            outline: 'none',
            marginBottom: '12px',
          }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {sampleGoals.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                onClick={() => setGoal(sample)}
              >
                {sample.slice(0, 30)}...
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={isLoading || !goal.trim()}
            className="btn btn-primary"
            style={{ opacity: isLoading || !goal.trim() ? 0.6 : 1 }}
          >
            {isLoading ? 'Deploying...' : 'Launch Agents'}
          </button>
        </div>
      </form>
    </div>
  );
};
