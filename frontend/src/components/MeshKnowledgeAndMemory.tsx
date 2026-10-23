import React, { useState, useEffect } from 'react';
import { AgentMemoryItem, EvaluationQualityMetrics } from '../types';
import * as api from '../api/client';

export const MeshKnowledgeAndMemory: React.FC = () => {
  const [subTab, setSubTab] = useState<'memory' | 'tools' | 'quality'>('memory');
  const [memories, setMemories] = useState<AgentMemoryItem[]>([]);
  const [quality, setQuality] = useState<EvaluationQualityMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [searchKey, setSearchKey] = useState('');
  const [newKey, setNewKey] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState<'workspace' | 'mission' | 'task_history'>('workspace');
  const [isAdding, setIsAdding] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchMemories = async () => {
    try {
      setIsLoading(true);
      const res = await api.listMemories({ query: searchKey || undefined });
      setMemories(res.memories || []);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch memories');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchQuality = async () => {
    try {
      const q = await api.getQualityMetrics();
      setQuality(q);
    } catch (err) {
      // transient
    }
  };

  useEffect(() => {
    fetchMemories();
    fetchQuality();
  }, [searchKey]);

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newContent.trim()) return;
    try {
      await api.createMemory({
        key: newKey.trim(),
        content: newContent.trim(),
        memory_type: newType,
        workspace_id: 'default_workspace',
      });
      setNewKey('');
      setNewContent('');
      setIsAdding(false);
      fetchMemories();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save memory');
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await api.deleteMemory(id);
      fetchMemories();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete memory');
    }
  };

  return (
    <div style={{
      background: '#0d1320',
      border: '1px solid #1a253a',
      borderRadius: '16px',
      padding: '24px'
    }}>
      {/* Header and Subtab Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f1f5f9' }}>
            Knowledge, Memory & Secure Tool Registry
          </h3>
          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
            Persistent cross-mission memory, AST tool security policies, and benchmark quality metrics
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', background: '#080c14', padding: '4px', borderRadius: '8px', border: '1px solid #172134' }}>
          {(['memory', 'tools', 'quality'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSubTab(tab)}
              style={{
                background: subTab === tab ? '#1e293b' : 'transparent',
                color: subTab === tab ? '#38bdf8' : '#94a3b8',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {tab === 'memory' ? '🧠 Persistent Memory' : tab === 'tools' ? '🛡️ Safe Tools' : '📊 Evaluation Quality'}
            </button>
          ))}
        </div>
      </div>

      {errorMsg && (
        <div style={{ padding: '10px 14px', background: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', borderRadius: '8px', marginBottom: '16px', fontSize: '0.78rem' }}>
          {errorMsg}
        </div>
      )}

      {/* Subtab 1: Persistent Agent Memory */}
      {subTab === 'memory' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{
              background: '#090d16',
              border: '1px solid #1c273e',
              borderRadius: '8px',
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              width: '280px'
            }}>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>🔍</span>
              <input
                type="text"
                placeholder="Filter memories by key or content..."
                value={searchKey}
                onChange={(e) => setSearchKey(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: '#f8fafc',
                  fontSize: '0.75rem',
                  width: '100%'
                }}
              />
            </div>

            <button
              onClick={() => setIsAdding(!isAdding)}
              style={{
                background: '#0284c7',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '7px 14px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {isAdding ? '✕ Cancel' : '+ Add Memory Item'}
            </button>
          </div>

          {isAdding && (
            <form onSubmit={handleCreateMemory} style={{
              background: '#0a0e18',
              border: '1px solid #1c273e',
              borderRadius: '10px',
              padding: '16px',
              marginBottom: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <input
                  type="text"
                  placeholder="Memory Key (e.g. tech_stack_guidelines)"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  style={{
                    flex: 1,
                    minWidth: '200px',
                    background: '#080c14',
                    border: '1px solid #1f2b42',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.78rem'
                  }}
                />
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as any)}
                  style={{
                    background: '#080c14',
                    border: '1px solid #1f2b42',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.78rem'
                  }}
                >
                  <option value="workspace">Scope: Workspace</option>
                  <option value="mission">Scope: Mission</option>
                  <option value="task_history">Scope: Task History</option>
                </select>
              </div>

              <textarea
                placeholder="Memory context payload (secrets will be automatically sanitized before persistence)..."
                rows={3}
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                style={{
                  background: '#080c14',
                  border: '1px solid #1f2b42',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  color: '#f8fafc',
                  fontSize: '0.78rem',
                  resize: 'vertical'
                }}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  type="submit"
                  style={{
                    background: '#10b981',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 14px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Save Context
                </button>
              </div>
            </form>
          )}

          {isLoading && memories.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
              Loading memory items...
            </div>
          ) : memories.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem', background: '#0a0e18', borderRadius: '10px' }}>
              No persistent memory records found. Autonomous missions automatically store final outcomes here.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {memories.map((mem) => (
                <div
                  key={mem.id}
                  style={{
                    background: '#0a0e18',
                    border: '1px solid #172134',
                    borderRadius: '10px',
                    padding: '12px 16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '12px'
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
                      <span style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: mem.memory_type === 'task_history' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                        color: mem.memory_type === 'task_history' ? '#34d399' : '#38bdf8',
                        border: '1px solid rgba(56, 189, 248, 0.2)'
                      }}>
                        {mem.memory_type}
                      </span>
                      <strong style={{ fontSize: '0.82rem', color: '#f8fafc' }}>
                        {mem.key}
                      </strong>
                      <span style={{ fontSize: '0.65rem', color: '#64748b' }}>
                        {new Date(mem.created_at).toLocaleDateString()} {new Date(mem.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: '#94a3b8', whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>
                      {mem.content}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDeleteMemory(mem.id)}
                    style={{
                      background: 'transparent',
                      border: '1px solid #2d3748',
                      color: '#fb7185',
                      borderRadius: '6px',
                      padding: '4px 8px',
                      fontSize: '0.68rem',
                      cursor: 'pointer'
                    }}
                    title="Delete Memory"
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Subtab 2: Secure Tool Registry */}
      {subTab === 'tools' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
          {[
            {
              name: 'calculator (v1.1.0)',
              desc: 'High-assurance AST arithmetic evaluation. Zero dynamic eval/exec, restricts syntax strictly to safe mathematical operations.',
              risk: 'LOW (Auto-Permitted)',
              status: 'Active',
              color: '#34d399'
            },
            {
              name: 'doc_inspector (v1.1.0)',
              desc: 'Read-only directory and file inspector with canonical path containment to neutralize directory traversal attacks.',
              risk: 'LOW (Auto-Permitted)',
              status: 'Active',
              color: '#34d399'
            },
            {
              name: 'text_summarizer (v1.0.0)',
              desc: 'Extractive NLP summarization scoring sentence frequency for bounded context condensation.',
              risk: 'LOW (Auto-Permitted)',
              status: 'Active',
              color: '#34d399'
            },
            {
              name: 'json_validator (v1.0.0)',
              desc: 'Strict JSON parser and key presence validator ensuring structured schemas from agent outputs.',
              risk: 'LOW (Auto-Permitted)',
              status: 'Active',
              color: '#34d399'
            },
            {
              name: 'http_get (v1.0.0)',
              desc: 'SSRF-hardened HTTP client blocking loopback, RFC1918 private IPs, and cloud metadata (169.254.169.254).',
              risk: 'HIGH (Human Approval Gate)',
              status: 'Guarded',
              color: '#fbbf24'
            },
            {
              name: 'execute_code_sandbox (v1.0.0)',
              desc: 'Isolated Python code execution with CPU timeout and memory limits, blocking host network access.',
              risk: 'LOW (Sandboxed)',
              status: 'Active',
              color: '#38bdf8'
            },
          ].map((tool) => (
            <div
              key={tool.name}
              style={{
                padding: '16px',
                background: '#0a0e18',
                border: '1px solid #172134',
                borderRadius: '10px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '8px'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.85rem' }}>
                    {tool.name}
                  </span>
                  <span style={{
                    fontSize: '0.62rem',
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(56, 189, 248, 0.1)',
                    color: tool.color,
                    border: `1px solid ${tool.color}40`
                  }}>
                    {tool.status}
                  </span>
                </div>
                <p style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: '1.4' }}>
                  {tool.desc}
                </p>
              </div>
              <div style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 600, borderTop: '1px solid #121926', paddingTop: '6px' }}>
                Safety Policy: <span style={{ color: tool.color }}>{tool.risk}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Subtab 3: Evaluation Quality Metrics */}
      {subTab === 'quality' && (
        <div>
          {quality ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                <div style={{ padding: '14px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Task Success Rate</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#34d399', marginTop: '4px' }}>
                    {quality.task_completion_rate.toFixed(1)}%
                  </div>
                </div>

                <div style={{ padding: '14px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Reviewer Acceptance</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>
                    {quality.reviewer_acceptance_rate.toFixed(1)}%
                  </div>
                </div>

                <div style={{ padding: '14px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Tool Success Rate</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#a78bfa', marginTop: '4px' }}>
                    {quality.tool_success_rate.toFixed(1)}%
                  </div>
                </div>

                <div style={{ padding: '14px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Retry Rate</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fbbf24', marginTop: '4px' }}>
                    {quality.retry_rate.toFixed(1)}%
                  </div>
                </div>

                <div style={{ padding: '14px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Average Operation Latency</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                    {quality.average_duration_ms > 0 ? `${quality.average_duration_ms.toFixed(0)}ms` : 'sub-10ms'}
                  </div>
                </div>

                <div style={{ padding: '14px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>p95 Tail Latency</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                    {quality.p95_duration_ms > 0 ? `${quality.p95_duration_ms.toFixed(0)}ms` : 'sub-15ms'}
                  </div>
                </div>
              </div>

              {/* Categorized Failure Explanations */}
              <div style={{ padding: '16px', background: '#0a0e18', border: '1px solid #172134', borderRadius: '10px' }}>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
                  Categorized Failure & Anomaly Distribution
                </h4>
                {quality.top_failure_reasons.length === 0 ? (
                  <p style={{ fontSize: '0.75rem', color: '#34d399' }}>
                    ✓ Zero operational failures recorded across active mission executions.
                  </p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {quality.top_failure_reasons.map((item, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', padding: '6px 10px', background: '#080c14', borderRadius: '6px' }}>
                        <span style={{ color: '#fb7185' }}>{item.reason}</span>
                        <span style={{ color: '#94a3b8', fontWeight: 700 }}>{item.count} events</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>
              Gathering fleet quality metrics...
            </div>
          )}
        </div>
      )}
    </div>
  );
};
