import React, { useState, useEffect } from 'react';
import { EvaluationDashboardData } from '../types';
import * as api from '../api/client';

export const EvaluationDashboard: React.FC = () => {
  const [data, setData] = useState<EvaluationDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.getEvaluationDashboard();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load evaluation metrics');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCsvExport = () => {
    window.open(api.getEvaluationCsvDownloadUrl(), '_blank');
  };

  if (isLoading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading evaluation dashboard...</div>;
  }

  if (error || !data) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#f87171' }}>{error || 'No evaluation data'}</div>;
  }

  const q = data.quality_metrics;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f1f5f9' }}>
            Evaluation & Benchmarking Dashboard
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
            Continuous quality analytics, autonomous completion rates, reviewer acceptance benchmarks, and safety verification.
          </p>
        </div>

        <button
          onClick={handleCsvExport}
          style={{
            background: '#141d2e',
            border: '1px solid #222f46',
            color: '#38bdf8',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '0.8rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>📊</span> Export Full Evaluations (CSV)
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
        
        {/* Task Completion Rate */}
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>COMPLETION RATE</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#34d399', marginTop: '4px' }}>
            {q.task_completion_rate}%
          </div>
          <span style={kpiSubStyle}>Across {data.total_evaluations} total recorded missions</span>
        </div>

        {/* Reviewer Acceptance Rate */}
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>REVIEWER ACCEPTANCE</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>
            {q.reviewer_acceptance_rate}%
          </div>
          <span style={kpiSubStyle}>Stage approval without rework</span>
        </div>

        {/* Tool Execution Success */}
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>TOOL EXECUTION SUCCESS</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#a78bfa', marginTop: '4px' }}>
            {q.tool_success_rate}%
          </div>
          <span style={kpiSubStyle}>Sandbox & whitelisted operations</span>
        </div>

        {/* Safety Score */}
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>BENCHMARK SAFETY SCORE</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#10b981', marginTop: '4px' }}>
            {data.benchmark_safety_score}%
          </div>
          <span style={kpiSubStyle}>0 unauthorized side-effects</span>
        </div>

        {/* P95 Latency */}
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>P95 DURATION</span>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fbbf24', marginTop: '4px' }}>
            {(q.p95_duration_ms / 1000).toFixed(2)}s
          </div>
          <span style={kpiSubStyle}>Average: {(q.average_duration_ms / 1000).toFixed(2)}s</span>
        </div>
      </div>

      {/* Middle Row: Workflow Breakdown (left) & Failure Analysis (right) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.8fr) minmax(0, 1.2fr)', gap: '16px' }}>
        
        {/* Workflow Performance Table */}
        <div style={{
          background: '#0d1320',
          border: '1px solid #1a253a',
          borderRadius: '14px',
          padding: '18px',
          overflowX: 'auto',
        }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#f8fafc', marginBottom: '12px' }}>
            Workflow Breakdown Analytics
          </h4>

          {data.workflow_breakdown.length === 0 ? (
            <div style={{ color: '#64748b', fontSize: '0.78rem', padding: '20px 0' }}>
              No workflow runs recorded yet. Deploy an automated workflow to track breakdown metrics.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.78rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1a253a', color: '#64748b', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '8px 10px' }}>Workflow</th>
                  <th style={{ padding: '8px 10px' }}>Runs</th>
                  <th style={{ padding: '8px 10px' }}>Success Rate</th>
                  <th style={{ padding: '8px 10px' }}>Avg Latency</th>
                  <th style={{ padding: '8px 10px' }}>Avg Cost</th>
                </tr>
              </thead>
              <tbody>
                {data.workflow_breakdown.map((wf) => (
                  <tr key={wf.workflow_id} style={{ borderBottom: '1px solid #141c2c' }}>
                    <td style={{ padding: '10px', fontWeight: 700, color: '#f8fafc' }}>{wf.name}</td>
                    <td style={{ padding: '10px', color: '#cbd5e1' }}>{wf.runs}</td>
                    <td style={{ padding: '10px', fontWeight: 700, color: wf.success_rate >= 80 ? '#34d399' : '#fbbf24' }}>
                      {wf.success_rate}%
                    </td>
                    <td style={{ padding: '10px', color: '#cbd5e1' }}>{(wf.avg_duration_ms / 1000).toFixed(2)}s</td>
                    <td style={{ padding: '10px', color: '#38bdf8', fontFamily: 'monospace' }}>
                      ${wf.avg_cost_usd.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Top Failure Reasons & LLM Health */}
        <div style={{
          background: '#0d1320',
          border: '1px solid #1a253a',
          borderRadius: '14px',
          padding: '18px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#f8fafc' }}>
            System Reliability & Failure Signals
          </h4>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
              <span>Retry Rate:</span>
              <strong style={{ color: q.retry_rate > 10 ? '#fbbf24' : '#34d399' }}>{q.retry_rate}%</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
              <span>LLM Timeout/Errors:</span>
              <strong style={{ color: q.llm_failures_count > 0 ? '#f87171' : '#34d399' }}>{q.llm_failures_count}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
              <span>Avg Approval Wait Time:</span>
              <strong style={{ color: '#cbd5e1' }}>{q.approval_wait_time_avg_s.toFixed(1)}s</strong>
            </div>
          </div>

          <div style={{ borderTop: '1px solid #1a253a', paddingTop: '12px' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 700, display: 'block', marginBottom: '8px' }}>
              TOP FAILURE CATEGORIES:
            </span>
            {q.top_failure_reasons.length === 0 ? (
              <span style={{ fontSize: '0.74rem', color: '#34d399' }}>✓ Zero failures recorded in evaluation window</span>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {q.top_failure_reasons.map((f, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', background: '#121a2b', padding: '6px 8px', borderRadius: '4px' }}>
                    <span style={{ color: '#f87171' }}>{f.reason}</span>
                    <span style={{ color: '#94a3b8', fontWeight: 700 }}>{f.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const kpiCardStyle: React.CSSProperties = {
  background: '#0d1320',
  border: '1px solid #1a253a',
  borderRadius: '12px',
  padding: '16px',
  display: 'flex',
  flexDirection: 'column',
};

const kpiLabelStyle: React.CSSProperties = {
  fontSize: '0.65rem',
  fontWeight: 700,
  letterSpacing: '0.06em',
  color: '#64748b',
};

const kpiSubStyle: React.CSSProperties = {
  fontSize: '0.68rem',
  color: '#64748b',
  marginTop: '4px',
};
