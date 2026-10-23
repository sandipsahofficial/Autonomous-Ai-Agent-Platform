import React, { useState, useEffect } from 'react';
import { CustomAgent } from '../types';
import * as api from '../api/client';

export const AgentBuilder: React.FC = () => {
  const [agents, setAgents] = useState<CustomAgent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [editingAgent, setEditingAgent] = useState<CustomAgent | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [role, setRole] = useState('researcher');
  const [permittedTools, setPermittedTools] = useState<string[]>(['calculator', 'doc_inspector']);
  const [modelProvider, setModelProvider] = useState('ollama');
  const [modelName, setModelName] = useState('llama3');
  const [temperature, setTemperature] = useState(0.2);
  const [maxSteps, setMaxSteps] = useState(10);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [reviewPolicy, setReviewPolicy] = useState('standard');
  const [isEnabled, setIsEnabled] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const availableTools = [
    { id: 'calculator', name: 'Calculator (AST Math)' },
    { id: 'doc_inspector', name: 'Doc Inspector (Knowledge Retrieval)' },
    { id: 'web_search', name: 'Web Search (Live Fact Lookup)' },
    { id: 'code_sandbox', name: 'Code Sandbox (Isolated Python Exec)' },
    { id: 'workspace_reader', name: 'Workspace Reader (Safe File Read)' },
    { id: 'workspace_writer', name: 'Workspace Writer (Approval-Guarded)' },
  ];

  const fetchAgents = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await api.listCustomAgents();
      setAgents(res.agents || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load agents');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const openCreateForm = () => {
    setEditingAgent(null);
    setName('');
    setDescription('');
    setRole('researcher');
    setPermittedTools(['calculator', 'doc_inspector']);
    setModelProvider('ollama');
    setModelName('llama3');
    setTemperature(0.2);
    setMaxSteps(10);
    setSystemPrompt('You are a specialized agent operating under the MESH Agent OS guardrails.');
    setReviewPolicy('standard');
    setIsEnabled(true);
    setIsFormOpen(true);
    setDeleteError(null);
  };

  const openEditForm = (agent: CustomAgent) => {
    setEditingAgent(agent);
    setName(agent.name);
    setDescription(agent.description || '');
    setRole(agent.role);
    setPermittedTools(agent.permitted_tools || []);
    setModelProvider(agent.model_provider);
    setModelName(agent.model_name);
    setTemperature(agent.temperature);
    setMaxSteps(agent.max_steps);
    setSystemPrompt(agent.system_prompt || '');
    setReviewPolicy(agent.review_policy);
    setIsEnabled(agent.is_enabled);
    setIsFormOpen(true);
    setDeleteError(null);
  };

  const handleToolToggle = (toolId: string) => {
    if (permittedTools.includes(toolId)) {
      setPermittedTools(permittedTools.filter((t) => t !== toolId));
    } else {
      setPermittedTools([...permittedTools, toolId]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    setDeleteError(null);
    try {
      const payload = {
        name,
        description,
        role,
        permitted_tools: permittedTools,
        model_provider: modelProvider,
        model_name: modelName,
        temperature,
        max_steps: maxSteps,
        system_prompt: systemPrompt,
        review_policy: reviewPolicy,
        is_enabled: isEnabled,
      };

      if (editingAgent) {
        await api.updateCustomAgent(editingAgent.id, payload);
      } else {
        await api.createCustomAgent(payload);
      }

      setIsFormOpen(false);
      await fetchAgents();
    } catch (err: any) {
      alert(`Error saving agent: ${err?.message || err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDuplicate = async (agentId: string) => {
    try {
      await api.duplicateCustomAgent(agentId);
      await fetchAgents();
    } catch (err: any) {
      alert(`Duplicate failed: ${err?.message || err}`);
    }
  };

  const handleDelete = async (agentId: string) => {
    setDeleteError(null);
    try {
      await api.deleteCustomAgent(agentId);
      setDeleteConfirmId(null);
      await fetchAgents();
    } catch (err: any) {
      setDeleteError(err?.message || 'Could not delete agent due to workflow dependencies.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header bar */}
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
          <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em' }}>
            Visual Agent Builder & Fleet Directory
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
            Configure specialized agents, tool permissions, system prompts, and review policies with zero-cost local inference.
          </p>
        </div>
        <button
          onClick={openCreateForm}
          style={{
            background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '0.8rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
          }}
        >
          <span>+</span> Create Custom Agent
        </button>
      </div>

      {deleteError && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '8px',
          padding: '12px 16px',
          color: '#f87171',
          fontSize: '0.82rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>🛡 {deleteError}</span>
          <button
            onClick={() => setDeleteError(null)}
            style={{ background: 'transparent', border: 'none', color: '#f87171', cursor: 'pointer', fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Agents Grid */}
      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading agent fleet...</div>
      ) : error ? (
        <div style={{ padding: '30px', textAlign: 'center', color: '#f87171' }}>{error}</div>
      ) : agents.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>No agents registered yet.</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
          {agents.map((agent) => (
            <div
              key={agent.id}
              style={{
                background: '#0d1320',
                border: '1px solid #1a253a',
                borderRadius: '12px',
                padding: '18px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '14px',
                transition: 'border-color 0.15s ease',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>{agent.name}</h4>
                    <span style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'monospace' }}>
                      @{agent.slug}
                    </span>
                  </div>
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    background: agent.is_enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                    color: agent.is_enabled ? '#34d399' : '#94a3b8',
                    border: `1px solid ${agent.is_enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(148, 163, 184, 0.3)'}`,
                  }}>
                    {agent.is_enabled ? 'ACTIVE' : 'DISABLED'}
                  </span>
                </div>

                <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.4, marginBottom: '12px', minHeight: '36px' }}>
                  {agent.description || 'Specialized autonomous operative.'}
                </p>

                {/* Specs */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.72rem', color: '#cbd5e1', marginBottom: '12px' }}>
                  <div style={{ background: '#121a2b', padding: '6px 8px', borderRadius: '6px' }}>
                    <span style={{ color: '#64748b' }}>Role: </span>
                    <strong style={{ color: '#38bdf8' }}>{agent.role}</strong>
                  </div>
                  <div style={{ background: '#121a2b', padding: '6px 8px', borderRadius: '6px' }}>
                    <span style={{ color: '#64748b' }}>Model: </span>
                    <strong>{agent.model_provider}/{agent.model_name}</strong>
                  </div>
                  <div style={{ background: '#121a2b', padding: '6px 8px', borderRadius: '6px' }}>
                    <span style={{ color: '#64748b' }}>Runs: </span>
                    <strong>{agent.total_runs}</strong>
                  </div>
                  <div style={{ background: '#121a2b', padding: '6px 8px', borderRadius: '6px' }}>
                    <span style={{ color: '#64748b' }}>Success: </span>
                    <strong style={{ color: agent.total_runs > 0 ? '#34d399' : '#94a3b8' }}>
                      {agent.total_runs > 0 ? `${Math.round((agent.successful_runs / agent.total_runs) * 100)}%` : 'N/A'}
                    </strong>
                  </div>
                </div>

                {/* Permitted Tools tags */}
                <div>
                  <span style={{ fontSize: '0.68rem', color: '#64748b', display: 'block', marginBottom: '4px' }}>Permitted Tools:</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {agent.permitted_tools && agent.permitted_tools.length > 0 ? (
                      agent.permitted_tools.map((tool) => (
                        <span
                          key={tool}
                          style={{
                            fontSize: '0.65rem',
                            padding: '2px 6px',
                            background: '#151d2f',
                            border: '1px solid #23314d',
                            borderRadius: '4px',
                            color: '#94a3b8',
                            fontFamily: 'monospace'
                          }}
                        >
                          {tool}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.68rem', color: '#64748b', fontStyle: 'italic' }}>None (Pure Reasoner)</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #1a253a', paddingTop: '12px' }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={() => openEditForm(agent)}
                    style={{
                      background: '#141d2e',
                      border: '1px solid #222f46',
                      color: '#cbd5e1',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      cursor: 'pointer'
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDuplicate(agent.id)}
                    style={{
                      background: '#141d2e',
                      border: '1px solid #222f46',
                      color: '#cbd5e1',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      cursor: 'pointer'
                    }}
                  >
                    Duplicate
                  </button>
                </div>

                {deleteConfirmId === agent.id ? (
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    <button
                      onClick={() => handleDelete(agent.id)}
                      style={{
                        background: '#dc2626',
                        border: 'none',
                        color: '#fff',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setDeleteConfirmId(null)}
                      style={{
                        background: '#1e293b',
                        border: 'none',
                        color: '#94a3b8',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '0.7rem',
                        cursor: 'pointer'
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirmId(agent.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#f43f5e',
                      fontSize: '0.72rem',
                      cursor: 'pointer',
                      padding: '4px 8px'
                    }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Modal Form */}
      {isFormOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(5, 8, 14, 0.75)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999,
          padding: '20px'
        }}>
          <div style={{
            background: '#0d1320',
            border: '1px solid #1a253a',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '600px',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc' }}>
                {editingAgent ? `Edit Agent: ${editingAgent.name}` : 'Configure New Agent'}
              </h3>
              <button
                onClick={() => setIsFormOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  Agent Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Math Research Sentinel"
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.85rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  Description
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Briefly describe the agent's core capability"
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.85rem'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Role
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="researcher">Researcher</option>
                    <option value="coder">Coder</option>
                    <option value="executor">Executor</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="planner">Planner</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Review Policy
                  </label>
                  <select
                    value={reviewPolicy}
                    onChange={(e) => setReviewPolicy(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="standard">Standard Self-Review</option>
                    <option value="strict">Strict Reviewer Approval</option>
                    <option value="human_guarded">Mandatory Human Checkpoint</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Model Provider
                  </label>
                  <select
                    value={modelProvider}
                    onChange={(e) => setModelProvider(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="ollama">Ollama (Zero-Cost Local)</option>
                    <option value="mock">MockLLM (Testing)</option>
                    <option value="openai">OpenAI (Optional Cloud)</option>
                    <option value="claude">Claude (Optional Cloud)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Model Name
                  </label>
                  <input
                    type="text"
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
              </div>

              {/* Permitted Tools */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  Permitted Tools (Security Whitelist)
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', background: '#121a2b', padding: '10px', borderRadius: '8px' }}>
                  {availableTools.map((t) => (
                    <label
                      key={t.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '0.75rem',
                        color: permittedTools.includes(t.id) ? '#38bdf8' : '#94a3b8',
                        cursor: 'pointer'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={permittedTools.includes(t.id)}
                        onChange={() => handleToolToggle(t.id)}
                      />
                      <span>{t.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* System Instructions */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  System Prompt & Execution Instructions
                </label>
                <textarea
                  rows={4}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Approved behavioral constraints, instructions, and output format..."
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.8rem',
                    fontFamily: 'monospace'
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  style={{
                    background: '#1e293b',
                    color: '#cbd5e1',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 16px',
                    fontSize: '0.8rem',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 18px',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
                  }}
                >
                  {isSubmitting ? 'Saving...' : editingAgent ? 'Save Changes' : 'Create Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
