import React, { useState, useEffect } from 'react';
import { Template } from '../types';
import * as api from '../api/client';

interface TemplateLibraryProps {
  onWorkflowCloned?: (workflowId: string) => void;
}

export const TemplateLibrary: React.FC<TemplateLibraryProps> = ({ onWorkflowCloned }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isImportModalOpen, setIsImportModalOpen] = useState<boolean>(false);
  const [importJsonText, setImportJsonText] = useState<string>('');
  const [importError, setImportError] = useState<string | null>(null);
  const [isCloning, setIsCloning] = useState<string | null>(null);

  const categories = ['all', 'Research', 'Development', 'QA', 'Enterprise'];

  const fetchTemplates = async () => {
    try {
      setIsLoading(true);
      const categoryParam = selectedCategory === 'all' ? undefined : selectedCategory;
      const res = await api.listTemplates(categoryParam);
      setTemplates(res.templates || []);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, [selectedCategory]);

  const handleClone = async (templateId: string, templateName: string) => {
    setIsCloning(templateId);
    try {
      const cloned = await api.cloneTemplate(templateId, `${templateName} (Cloned)`);
      alert(`Template cloned successfully as workflow: "${cloned.name}"!`);
      if (onWorkflowCloned) {
        onWorkflowCloned(cloned.id);
      }
    } catch (err: any) {
      alert(`Clone failed: ${err?.message || err}`);
    } finally {
      setIsCloning(null);
    }
  };

  const handleExport = async (templateId: string, filename: string) => {
    try {
      const data = await api.exportTemplateJson(templateId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename.toLowerCase().replace(/\s+/g, '_')}_template.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err?.message || err}`);
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setImportError(null);
    try {
      const parsed = JSON.parse(importJsonText);
      await api.importTemplateJson(parsed);
      setIsImportModalOpen(false);
      setImportJsonText('');
      await fetchTemplates();
    } catch (err: any) {
      setImportError(err?.message || 'Invalid JSON format or untrusted payload structure.');
    }
  };

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
            Agent & Workflow Template Library
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
            Jumpstart autonomous workflows with built-in reference architectures, security-audited topologies, and portable JSON export/import.
          </p>
        </div>

        <button
          onClick={() => setIsImportModalOpen(true)}
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
          <span>📥</span> Import Template JSON
        </button>
      </div>

      {/* Category Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px' }}>
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setSelectedCategory(c)}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 700,
              background: selectedCategory === c ? '#0284c7' : '#121a2b',
              color: selectedCategory === c ? '#ffffff' : '#94a3b8',
              border: selectedCategory === c ? '1px solid #38bdf8' : '1px solid #1e293b',
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Templates Grid */}
      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>Loading templates...</div>
      ) : templates.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>No templates found in this category.</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
          {templates.map((t) => (
            <div
              key={t.id}
              style={{
                background: '#0d1320',
                border: '1px solid #1a253a',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '14px',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: '#151d2f',
                    border: '1px solid #23314d',
                    color: '#38bdf8',
                    textTransform: 'uppercase',
                  }}>
                    {t.category}
                  </span>
                  {t.is_built_in && (
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      color: '#34d399',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      ✓ Verified Built-in
                    </span>
                  )}
                </div>

                <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#f8fafc', marginBottom: '6px' }}>
                  {t.name}
                </h4>
                <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.4, marginBottom: '14px' }}>
                  {t.description}
                </p>

                {/* Node Counts & Author */}
                <div style={{ display: 'flex', gap: '10px', fontSize: '0.7rem', color: '#64748b', marginBottom: '12px' }}>
                  <span>Nodes: <strong>{t.workflow_definition?.nodes?.length || 0}</strong></span>
                  <span>Edges: <strong>{t.workflow_definition?.edges?.length || 0}</strong></span>
                  <span>Author: <strong>{t.author}</strong></span>
                </div>

                {/* Tags */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {t.tags?.map((tag) => (
                    <span
                      key={tag}
                      style={{
                        fontSize: '0.65rem',
                        padding: '2px 6px',
                        background: '#121a2b',
                        borderRadius: '4px',
                        color: '#cbd5e1',
                      }}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #1a253a', paddingTop: '12px' }}>
                <button
                  onClick={() => handleExport(t.id, t.name)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#94a3b8',
                    fontSize: '0.74rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span>⬇</span> Export JSON
                </button>

                <button
                  onClick={() => handleClone(t.id, t.name)}
                  disabled={isCloning === t.id}
                  style={{
                    background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 14px',
                    fontSize: '0.74rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px rgba(2, 132, 199, 0.3)'
                  }}
                >
                  {isCloning === t.id ? 'Cloning...' : '⚡ Clone to Workflow'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Import JSON Modal */}
      {isImportModalOpen && (
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
          padding: '20px',
        }}>
          <div style={{
            background: '#0d1320',
            border: '1px solid #1a253a',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '560px',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>
                Import Workflow Template JSON
              </h3>
              <button
                onClick={() => setIsImportModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {importError && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#f87171',
                fontSize: '0.8rem',
                marginBottom: '14px'
              }}>
                ⚠ {importError}
              </div>
            )}

            <form onSubmit={handleImportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  Paste Template Definition JSON
                </label>
                <textarea
                  rows={10}
                  required
                  value={importJsonText}
                  onChange={(e) => setImportJsonText(e.target.value)}
                  placeholder={`{\n  "name": "Custom Pipeline",\n  "category": "Development",\n  "description": "...",\n  "workflow_definition": { "nodes": [], "edges": [] }\n}`}
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f8fafc',
                    fontFamily: 'monospace',
                    fontSize: '0.78rem'
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
                <button
                  type="button"
                  onClick={() => setIsImportModalOpen(false)}
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
                  style={{
                    background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 18px',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Verify & Import
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
