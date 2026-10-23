import React, { useState, useEffect } from 'react';
import { KnowledgeDocument, DocumentChunk, DocumentCitation } from '../types';
import * as api from '../api/client';

export const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Direct Text Input Modal
  const [isTextModalOpen, setIsTextModalOpen] = useState<boolean>(false);
  const [textFilename, setTextFilename] = useState('');
  const [textContent, setTextContent] = useState('');

  // Selected Document & Chunks Viewer
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null);

  // Live Citation Search Tester
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [citations, setCitations] = useState<DocumentCitation[]>([]);

  const fetchDocs = async () => {
    try {
      setIsLoading(true);
      setUploadError(null);
      const res = await api.listDocuments();
      setDocuments(res.documents || []);
    } catch (err: any) {
      console.error('Failed to load documents:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocumentFile(file);
      await fetchDocs();
    } catch (err: any) {
      setUploadError(err?.message || 'File upload failed');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleCreateTextDoc = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textFilename.trim() || !textContent.trim()) return;

    try {
      await api.createDocumentText(textFilename, textContent);
      setIsTextModalOpen(false);
      setTextFilename('');
      setTextContent('');
      await fetchDocs();
    } catch (err: any) {
      alert(`Failed to create document: ${err?.message || err}`);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document and all its indexed chunks?')) return;
    try {
      await api.deleteDocument(docId);
      if (selectedDoc?.id === docId) setSelectedDoc(null);
      await fetchDocs();
    } catch (err: any) {
      alert(`Delete failed: ${err?.message || err}`);
    }
  };

  const handleCitationSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const res = await api.queryDocumentCitations(searchQuery, 3);
      setCitations(res.citations || []);
    } catch (err: any) {
      alert(`Citation search failed: ${err?.message || err}`);
    } finally {
      setIsSearching(false);
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
            Knowledge Base & Document Retrieval
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
            Ingest TXT, Markdown, PDF, and DOCX documents with magic-byte validation, chunk indexing, and citation search.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setIsTextModalOpen(true)}
            style={{
              background: '#141d2e',
              border: '1px solid #222f46',
              color: '#38bdf8',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            + New Text Doc
          </button>

          <label style={{
            background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
            color: '#ffffff',
            borderRadius: '8px',
            padding: '8px 16px',
            fontSize: '0.8rem',
            fontWeight: 700,
            cursor: isUploading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)',
          }}>
            <span>📄</span> {isUploading ? 'Ingesting...' : 'Upload File'}
            <input
              type="file"
              disabled={isUploading}
              accept=".txt,.md,.pdf,.docx"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
          </label>
        </div>
      </div>

      {uploadError && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '8px',
          padding: '10px 14px',
          color: '#f87171',
          fontSize: '0.8rem'
        }}>
          ⚠ {uploadError}
        </div>
      )}

      {/* Main Grid: Document List (left) & Chunks/Citation Inspector (right) */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedDoc ? '1.3fr 1fr' : '1fr', gap: '16px' }}>
        
        {/* Document Inventory Table */}
        <div style={{
          background: '#0d1320',
          border: '1px solid #1a253a',
          borderRadius: '14px',
          padding: '18px',
          overflowX: 'auto',
        }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#f8fafc', marginBottom: '14px' }}>
            Ingested Knowledge Documents ({documents.length})
          </h4>

          {isLoading ? (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Loading documents...</div>
          ) : documents.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
              No documents in knowledge repository. Upload a PDF, DOCX, or Markdown file to index.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1a253a', color: '#64748b', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 12px' }}>Document</th>
                  <th style={{ padding: '10px 12px' }}>Format</th>
                  <th style={{ padding: '10px 12px' }}>Size / Pages</th>
                  <th style={{ padding: '10px 12px' }}>Chunks</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr
                    key={d.id}
                    style={{
                      borderBottom: '1px solid #141c2c',
                      background: selectedDoc?.id === d.id ? '#121a2b' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontWeight: 700, color: '#f8fafc' }}>{d.filename}</div>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>ID: {d.id.slice(0, 8)}...</div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: '#151d2f',
                        border: '1px solid #23314d',
                        color: '#38bdf8',
                        fontFamily: 'monospace',
                        fontSize: '0.7rem'
                      }}>
                        {d.file_type.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: '#cbd5e1', fontSize: '0.75rem' }}>
                      {Math.round(d.file_size_bytes / 1024)} KB • {d.page_count} pg
                    </td>
                    <td style={{ padding: '12px', color: '#cbd5e1', fontSize: '0.75rem' }}>
                      {d.chunks?.length || 0} chunks
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          onClick={() => setSelectedDoc(d)}
                          style={{
                            background: '#121a2b',
                            border: '1px solid #1e293b',
                            color: '#38bdf8',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                          }}
                        >
                          View Chunks
                        </button>
                        <button
                          onClick={() => handleDelete(d.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#f43f5e',
                            padding: '4px 6px',
                            fontSize: '0.7rem',
                            cursor: 'pointer',
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Selected Document Chunks Drawer */}
        {selectedDoc && (
          <div style={{
            background: '#0d1320',
            border: '1px solid #1a253a',
            borderRadius: '14px',
            padding: '18px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1a253a', paddingBottom: '8px' }}>
              <div>
                <h4 style={{ fontSize: '0.88rem', fontWeight: 800, color: '#f8fafc' }}>
                  Chunks: {selectedDoc.filename}
                </h4>
                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                  Total {selectedDoc.chunks?.length || 0} indexed segments
                </span>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '420px', overflowY: 'auto' }}>
              {selectedDoc.chunks?.map((chunk: DocumentChunk) => (
                <div
                  key={chunk.id}
                  style={{
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    fontSize: '0.74rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38bdf8', fontWeight: 700, marginBottom: '4px' }}>
                    <span>Chunk #{chunk.chunk_index} (Page {chunk.page_number})</span>
                    <span style={{ color: '#64748b' }}>~{chunk.token_count} tokens</span>
                  </div>
                  <p style={{ color: '#cbd5e1', lineHeight: 1.4, margin: 0, fontFamily: 'monospace', fontSize: '0.7rem' }}>
                    {chunk.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Live Citation Search Tester */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '20px',
      }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f8fafc', marginBottom: '6px' }}>
          Live Citation Retrieval & Semantic Match Tester
        </h4>
        <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '14px' }}>
          Query your knowledge base to verify exact page-number citations, relevance scores, and untrusted framing.
        </p>

        <form onSubmit={handleCitationSearch} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="e.g. What are the external database TLS encryption policies?"
            style={{
              flex: 1,
              background: '#121a2b',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              padding: '8px 14px',
              color: '#f8fafc',
              fontSize: '0.85rem'
            }}
          />
          <button
            type="submit"
            disabled={isSearching}
            style={{
              background: '#141d2e',
              border: '1px solid #222f46',
              color: '#38bdf8',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            {isSearching ? 'Searching...' : 'Search Citations'}
          </button>
        </form>

        {citations.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 700 }}>
              VERIFIED CITATIONS RETRIEVED ({citations.length}):
            </span>
            {citations.map((c, idx) => (
              <div
                key={idx}
                style={{
                  background: '#121a2b',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '12px',
                  fontSize: '0.78rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 700, color: '#38bdf8' }}>
                    [{c.filename}] Page {c.page_number} (Chunk #{c.chunk_index})
                  </span>
                  <span style={{
                    fontSize: '0.68rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(56, 189, 248, 0.15)',
                    color: '#38bdf8',
                    fontWeight: 700
                  }}>
                    Score: {c.score}
                  </span>
                </div>
                <blockquote style={{
                  margin: 0,
                  padding: '6px 10px',
                  borderLeft: '3px solid #38bdf8',
                  background: '#090d16',
                  color: '#e2e8f0',
                  fontFamily: 'monospace',
                  fontSize: '0.74rem'
                }}>
                  "{c.matched_snippet}"
                </blockquote>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Direct Text Document Modal */}
      {isTextModalOpen && (
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
                Create Knowledge Document
              </h3>
              <button
                onClick={() => setIsTextModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTextDoc} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  Filename (e.g. infrastructure_policies.txt) *
                </label>
                <input
                  type="text"
                  required
                  value={textFilename}
                  onChange={(e) => setTextFilename(e.target.value)}
                  placeholder="company_handbook.md"
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
                  Document Content *
                </label>
                <textarea
                  rows={8}
                  required
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  placeholder="Paste or write raw documentation here for automatic chunk indexing..."
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontFamily: 'monospace',
                    fontSize: '0.8rem'
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsTextModalOpen(false)}
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
                  Index Document
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
