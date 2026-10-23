import React, { useState, useEffect, useRef } from 'react';
import {
  Workflow,
  WorkflowNode,
  WorkflowEdge,
  WorkflowDefinition,
  WorkflowRun,
  CustomAgent,
} from '../types';
import * as api from '../api/client';

export const WorkflowDesigner: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);
  const [agents, setAgents] = useState<CustomAgent[]>([]);

  // Selection & drag states
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [connectingSourceId, setConnectingSourceId] = useState<string | null>(null);

  // Validation & Run State
  const [validationResult, setValidationResult] = useState<{
    is_valid: boolean;
    errors: string[];
    warnings: string[];
  } | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [activeRun, setActiveRun] = useState<WorkflowRun | null>(null);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);

  // Load workflows & agents on mount
  useEffect(() => {
    loadWorkflows();
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const res = await api.listCustomAgents();
      setAgents(res.agents || []);
    } catch (err) {
      console.error('Error fetching agents:', err);
    }
  };

  const loadWorkflows = async () => {
    try {
      const res = await api.listWorkflows();
      const list = res.workflows || [];
      setWorkflows(list);
      if (list.length > 0 && !activeWorkflow) {
        selectWorkflow(list[0].id);
      } else if (list.length === 0) {
        initDefaultCanvas();
      }
    } catch (err) {
      console.error('Error fetching workflows:', err);
      initDefaultCanvas();
    }
  };

  const selectWorkflow = async (workflowId: string) => {
    try {
      const wf = await api.getWorkflow(workflowId);
      setActiveWorkflow(wf);
      if (wf.definition) {
        setNodes(wf.definition.nodes || []);
        setEdges(wf.definition.edges || []);
      }
      setValidationResult(null);
      setActiveRun(null);
    } catch (err) {
      console.error('Failed to get workflow details:', err);
    }
  };

  const initDefaultCanvas = () => {
    const defaultNodes: WorkflowNode[] = [
      { id: 'start_1', type: 'start', label: 'Start Trigger', position: { x: 50, y: 150 } },
      { id: 'agent_1', type: 'agent', label: 'Planner Agent', agent_slug: 'planner', position: { x: 250, y: 150 } },
      { id: 'tool_1', type: 'tool', label: 'Research Query', tool_name: 'doc_inspector', position: { x: 480, y: 100 } },
      { id: 'review_1', type: 'review', label: 'Self-Reviewer', position: { x: 700, y: 150 } },
      { id: 'end_1', type: 'end', label: 'Final Report', position: { x: 920, y: 150 } },
    ];
    const defaultEdges: WorkflowEdge[] = [
      { id: 'e1', source: 'start_1', target: 'agent_1' },
      { id: 'e2', source: 'agent_1', target: 'tool_1' },
      { id: 'e3', source: 'tool_1', target: 'review_1' },
      { id: 'e4', source: 'review_1', target: 'end_1' },
    ];
    setNodes(defaultNodes);
    setEdges(defaultEdges);
  };

  // Dragging logic
  const handleMouseDownNode = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    if (connectingSourceId) {
      // Complete edge
      if (connectingSourceId !== nodeId) {
        const newEdge: WorkflowEdge = {
          id: `e_${Date.now()}`,
          source: connectingSourceId,
          target: nodeId,
        };
        setEdges([...edges, newEdge]);
      }
      setConnectingSourceId(null);
      return;
    }

    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;

    setSelectedNodeId(nodeId);
    setDraggingNodeId(nodeId);

    const canvasRect = canvasRef.current?.getBoundingClientRect() || { left: 0, top: 0 };
    setDragOffset({
      x: e.clientX - canvasRect.left - (node.position?.x || 0),
      y: e.clientY - canvasRect.top - (node.position?.y || 0),
    });
  };

  const handleMouseMoveCanvas = (e: React.MouseEvent) => {
    if (!draggingNodeId || !canvasRef.current) return;
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const newX = Math.max(10, Math.min(1400, e.clientX - canvasRect.left - dragOffset.x));
    const newY = Math.max(10, Math.min(800, e.clientY - canvasRect.top - dragOffset.y));

    setNodes((prev) =>
      prev.map((n) => (n.id === draggingNodeId ? { ...n, position: { x: newX, y: newY } } : n))
    );
  };

  const handleMouseUpCanvas = () => {
    setDraggingNodeId(null);
  };

  // Node addition
  const addNode = (type: WorkflowNode['type']) => {
    const id = `${type}_${Date.now().toString().slice(-4)}`;
    const label = `${type.charAt(0).toUpperCase() + type.slice(1)} Node`;
    const newNode: WorkflowNode = {
      id,
      type,
      label,
      agent_slug: type === 'agent' ? 'researcher' : undefined,
      tool_name: type === 'tool' ? 'doc_inspector' : undefined,
      position: { x: 120 + Math.random() * 400, y: 100 + Math.random() * 200 },
    };
    setNodes([...nodes, newNode]);
    setSelectedNodeId(id);
  };

  // Node Deletion
  const deleteSelectedNode = () => {
    if (!selectedNodeId) return;
    setNodes(nodes.filter((n) => n.id !== selectedNodeId));
    setEdges(edges.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
    setSelectedNodeId(null);
  };

  // Node Updating
  const updateSelectedNode = (field: keyof WorkflowNode, val: any) => {
    if (!selectedNodeId) return;
    setNodes((prev) =>
      prev.map((n) => (n.id === selectedNodeId ? { ...n, [field]: val } : n))
    );
  };

  // Real-time Topology Validation
  const handleValidate = async () => {
    setIsValidating(true);
    setValidationResult(null);
    try {
      const def: WorkflowDefinition = { nodes, edges };
      const res = await api.validateWorkflow(def);
      setValidationResult(res);
    } catch (err: any) {
      setValidationResult({
        is_valid: false,
        errors: [err?.message || 'Validation request failed'],
        warnings: [],
      });
    } finally {
      setIsValidating(false);
    }
  };

  // Save / Version Workflow
  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccessMsg(null);
    try {
      const def: WorkflowDefinition = { nodes, edges };
      if (activeWorkflow) {
        const updated = await api.updateWorkflow(activeWorkflow.id, {
          name: activeWorkflow.name,
          description: activeWorkflow.description,
          definition: def,
          is_enabled: true,
        });
        setActiveWorkflow(updated);
        setSaveSuccessMsg(`Saved Version ${updated.active_version} successfully!`);
      } else {
        const created = await api.createWorkflow({
          name: 'Visual Autonomous Pipeline',
          description: 'Engineered in MESH Visual Workflow Designer',
          definition: def,
          is_enabled: true,
        });
        setActiveWorkflow(created);
        setSaveSuccessMsg('Workflow created successfully!');
        await loadWorkflows();
      }
    } catch (err: any) {
      alert(`Save failed: ${err?.message || err}`);
    } finally {
      setIsSaving(false);
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    }
  };

  // Execute Workflow
  const handleExecute = async () => {
    if (!activeWorkflow) {
      alert('Please save the workflow before executing.');
      return;
    }
    setIsExecuting(true);
    try {
      const run = await api.executeWorkflow(activeWorkflow.id, {}, activeWorkflow.name);
      setActiveRun(run);

      // Poll run status
      const pollInterval = setInterval(async () => {
        try {
          const updatedRun = await api.getWorkflowRun(run.id);
          setActiveRun(updatedRun);
          if (updatedRun.status === 'COMPLETED' || updatedRun.status === 'FAILED') {
            clearInterval(pollInterval);
            setIsExecuting(false);
          }
        } catch {
          clearInterval(pollInterval);
          setIsExecuting(false);
        }
      }, 1500);
    } catch (err: any) {
      alert(`Execution failed: ${err?.message || err}`);
      setIsExecuting(false);
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  // SVG Edge path generator
  const getEdgePath = (edge: WorkflowEdge) => {
    const sNode = nodes.find((n) => n.id === edge.source);
    const tNode = nodes.find((n) => n.id === edge.target);
    if (!sNode || !tNode) return '';

    const sx = (sNode.position?.x || 0) + 140; // right edge of source card
    const sy = (sNode.position?.y || 0) + 38;  // middle height
    const tx = (tNode.position?.x || 0);       // left edge of target card
    const ty = (tNode.position?.y || 0) + 38;

    const dx = Math.abs(tx - sx) * 0.5;
    return `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      {/* Top Controls Bar */}
      <div style={{
        background: '#0d1320',
        border: '1px solid #1a253a',
        borderRadius: '14px',
        padding: '14px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f1f5f9' }}>
              Visual Workflow Automation Designer
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
              {activeWorkflow ? `${activeWorkflow.name} (v${activeWorkflow.active_version})` : 'Untitled Dynamic Workflow'}
            </span>
          </div>

          {/* Workflow Selector dropdown */}
          {workflows.length > 0 && (
            <select
              value={activeWorkflow?.id || ''}
              onChange={(e) => selectWorkflow(e.target.value)}
              style={{
                background: '#121a2b',
                border: '1px solid #1e293b',
                borderRadius: '6px',
                padding: '4px 8px',
                color: '#94a3b8',
                fontSize: '0.75rem',
              }}
            >
              {workflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} (v{w.active_version})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={handleValidate}
            disabled={isValidating}
            style={{
              background: '#121a2b',
              border: '1px solid #1e293b',
              color: '#38bdf8',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>✓</span> {isValidating ? 'Validating...' : 'Validate Graph'}
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            style={{
              background: '#141d2e',
              border: '1px solid #222f46',
              color: '#34d399',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {isSaving ? 'Saving...' : 'Save Version'}
          </button>

          <button
            onClick={handleExecute}
            disabled={isExecuting}
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
            }}
          >
            {isExecuting ? '⚡ Running...' : '⚡ Run Pipeline'}
          </button>
        </div>
      </div>

      {/* Validation Feedback & Save Banner */}
      {saveSuccessMsg && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          padding: '8px 14px',
          borderRadius: '8px',
          color: '#34d399',
          fontSize: '0.78rem',
        }}>
          ✓ {saveSuccessMsg}
        </div>
      )}

      {validationResult && (
        <div style={{
          background: validationResult.is_valid ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${validationResult.is_valid ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          padding: '10px 16px',
          borderRadius: '8px',
          fontSize: '0.78rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ fontWeight: 700, color: validationResult.is_valid ? '#34d399' : '#f87171' }}>
            {validationResult.is_valid ? '✓ Workflow Topology Verified: Ready for Autonomous Execution' : '⚠ Topology Validation Issues Detected:'}
          </div>
          {validationResult.errors.map((e, idx) => (
            <div key={idx} style={{ color: '#f87171', paddingLeft: '12px' }}>• {e}</div>
          ))}
          {validationResult.warnings.map((w, idx) => (
            <div key={idx} style={{ color: '#fbbf24', paddingLeft: '12px' }}>• Warning: {w}</div>
          ))}
        </div>
      )}

      {/* Main Designer Canvas & Node Palette */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 280px', gap: '16px', flex: 1, minHeight: '520px' }}>
        
        {/* Canvas Area */}
        <div
          ref={canvasRef}
          onMouseMove={handleMouseMoveCanvas}
          onMouseUp={handleMouseUpCanvas}
          style={{
            background: '#090d16',
            border: '1px solid #172033',
            borderRadius: '14px',
            position: 'relative',
            overflow: 'hidden',
            minHeight: '500px',
            userSelect: 'none',
            backgroundImage: 'radial-gradient(#1a263d 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        >
          {/* Node Palette floating button row */}
          <div style={{
            position: 'absolute',
            top: '12px',
            left: '12px',
            zIndex: 10,
            display: 'flex',
            gap: '6px',
            background: 'rgba(13, 19, 32, 0.85)',
            backdropFilter: 'blur(6px)',
            padding: '6px 8px',
            borderRadius: '8px',
            border: '1px solid #1a253a'
          }}>
            <button onClick={() => addNode('agent')} style={paletteBtnStyle} title="Add Agent">+ Agent</button>
            <button onClick={() => addNode('tool')} style={paletteBtnStyle} title="Add Tool">+ Tool</button>
            <button onClick={() => addNode('conditional')} style={paletteBtnStyle} title="Add Branch">+ Branch</button>
            <button onClick={() => addNode('approval')} style={paletteBtnStyle} title="Add Human Checkpoint">+ Approval</button>
            <button onClick={() => addNode('parallel')} style={paletteBtnStyle} title="Add Parallel Fork">+ Fork</button>
            <button onClick={() => addNode('merge')} style={paletteBtnStyle} title="Add Merge">+ Merge</button>
            <button onClick={() => addNode('review')} style={paletteBtnStyle} title="Add Review">+ Review</button>
            <button onClick={() => addNode('end')} style={paletteBtnStyle} title="Add Terminal Node">+ End</button>
          </div>

          {/* SVG Connection Lines */}
          <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="5"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
              </marker>
            </defs>
            {edges.map((e) => (
              <path
                key={e.id}
                d={getEdgePath(e)}
                fill="none"
                stroke="#38bdf8"
                strokeWidth="2"
                strokeDasharray="4 2"
                markerEnd="url(#arrow)"
                opacity="0.8"
              />
            ))}
          </svg>

          {/* Render Nodes */}
          {nodes.map((node) => {
            const isSelected = selectedNodeId === node.id;
            const isConnecting = connectingSourceId === node.id;
            const nodeState = activeRun?.node_states?.[node.id] || 'idle';

            return (
              <div
                key={node.id}
                onMouseDown={(e) => handleMouseDownNode(e, node.id)}
                style={{
                  position: 'absolute',
                  left: `${node.position?.x || 50}px`,
                  top: `${node.position?.y || 50}px`,
                  width: '140px',
                  background: getNodeBackground(node.type),
                  border: isSelected
                    ? '2px solid #38bdf8'
                    : isConnecting
                    ? '2px dashed #fbbf24'
                    : '1px solid #1e293b',
                  borderRadius: '10px',
                  padding: '10px 12px',
                  cursor: 'grab',
                  boxShadow: isSelected ? '0 0 16px rgba(56, 189, 248, 0.4)' : '0 4px 12px rgba(0,0,0,0.5)',
                  zIndex: isSelected ? 5 : 2,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{
                    fontSize: '0.62rem',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    color: getNodeTypeColor(node.type),
                  }}>
                    {node.type}
                  </span>
                  {nodeState !== 'idle' && (
                    <span style={{
                      fontSize: '0.58rem',
                      padding: '1px 4px',
                      borderRadius: '4px',
                      background: nodeState === 'completed' ? '#065f46' : nodeState === 'active' ? '#0369a1' : '#7f1d1d',
                      color: '#fff',
                      fontWeight: 700
                    }}>
                      {nodeState}
                    </span>
                  )}
                </div>

                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {node.label}
                </div>

                {node.agent_slug && (
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginTop: '2px' }}>
                    @{node.agent_slug}
                  </div>
                )}
                {node.tool_name && (
                  <div style={{ fontSize: '0.65rem', color: '#38bdf8', fontFamily: 'monospace', marginTop: '2px' }}>
                    [{node.tool_name}]
                  </div>
                )}

                {/* Connector Handle */}
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    setConnectingSourceId(node.id);
                  }}
                  title="Click to connect to another node"
                  style={{
                    position: 'absolute',
                    right: '-6px',
                    top: '32px',
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: '#38bdf8',
                    border: '2px solid #090d16',
                    cursor: 'crosshair',
                  }}
                />
              </div>
            );
          })}
        </div>

        {/* Right Configuration Inspector Panel */}
        <div style={{
          background: '#0d1320',
          border: '1px solid #1a253a',
          borderRadius: '14px',
          padding: '18px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#f8fafc', borderBottom: '1px solid #1a253a', paddingBottom: '8px' }}>
            Node Inspector
          </h4>

          {selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '4px' }}>
                  Node Label
                </label>
                <input
                  type="text"
                  value={selectedNode.label}
                  onChange={(e) => updateSelectedNode('label', e.target.value)}
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    padding: '6px 8px',
                    color: '#f8fafc',
                    fontSize: '0.78rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '4px' }}>
                  Node Type
                </label>
                <span style={{ fontSize: '0.78rem', color: getNodeTypeColor(selectedNode.type), fontWeight: 700 }}>
                  {selectedNode.type.toUpperCase()}
                </span>
              </div>

              {selectedNode.type === 'agent' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '4px' }}>
                    Assigned Agent
                  </label>
                  <select
                    value={selectedNode.agent_slug || ''}
                    onChange={(e) => updateSelectedNode('agent_slug', e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '6px',
                      padding: '6px 8px',
                      color: '#f8fafc',
                      fontSize: '0.78rem'
                    }}
                  >
                    <option value="">Select agent...</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.slug}>
                        {a.name} (@{a.slug})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {selectedNode.type === 'tool' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', fontWeight: 700, marginBottom: '4px' }}>
                    Tool Operation
                  </label>
                  <select
                    value={selectedNode.tool_name || ''}
                    onChange={(e) => updateSelectedNode('tool_name', e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '6px',
                      padding: '6px 8px',
                      color: '#f8fafc',
                      fontSize: '0.78rem'
                    }}
                  >
                    <option value="calculator">calculator (AST Math)</option>
                    <option value="doc_inspector">doc_inspector (Knowledge Citation)</option>
                    <option value="web_search">web_search (Live Facts)</option>
                    <option value="code_sandbox">code_sandbox (Isolated Python)</option>
                    <option value="workspace_reader">workspace_reader (Workspace Files)</option>
                    <option value="workspace_writer">workspace_writer (Human Guarded)</option>
                  </select>
                </div>
              )}

              <button
                onClick={deleteSelectedNode}
                style={{
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  color: '#f87171',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  marginTop: '12px'
                }}
              >
                Delete Selected Node
              </button>
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.75rem', textAlign: 'center', marginTop: '40px' }}>
              Select a node on canvas to view and configure properties.
            </div>
          )}

          {/* Active Run Status Widget */}
          {activeRun && (
            <div style={{ marginTop: 'auto', background: '#121a2b', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px' }}>
              <div style={{ fontSize: '0.7rem', color: '#64748b', fontWeight: 700 }}>EXECUTION RUN</div>
              <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#38bdf8', marginTop: '2px' }}>
                Status: {activeRun.status}
              </div>
              <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginTop: '4px' }}>
                Run ID: {activeRun.id.slice(0, 8)}...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const paletteBtnStyle: React.CSSProperties = {
  background: '#141d2e',
  border: '1px solid #222f46',
  color: '#cbd5e1',
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '0.68rem',
  fontWeight: 700,
  cursor: 'pointer',
};

function getNodeBackground(type: WorkflowNode['type']): string {
  switch (type) {
    case 'start': return '#064e3b';
    case 'end': return '#701a75';
    case 'agent': return '#0f2942';
    case 'tool': return '#1e1b4b';
    case 'conditional': return '#451a03';
    case 'approval': return '#78350f';
    case 'review': return '#1e293b';
    default: return '#111827';
  }
}

function getNodeTypeColor(type: WorkflowNode['type']): string {
  switch (type) {
    case 'start': return '#34d399';
    case 'end': return '#f472b6';
    case 'agent': return '#38bdf8';
    case 'tool': return '#a78bfa';
    case 'conditional': return '#fbbf24';
    case 'approval': return '#f59e0b';
    case 'review': return '#94a3b8';
    default: return '#cbd5e1';
  }
}
