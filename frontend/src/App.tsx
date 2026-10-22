import React, { useState, useEffect } from 'react';
import { Task, AuditLog, PendingApprovalItem } from './types';
import * as api from './api/client';
import { MeshHeader } from './components/MeshHeader';
import { MeshSidebar } from './components/MeshSidebar';
import { MeshStatCards } from './components/MeshStatCards';
import { MeshMissionGraph } from './components/MeshMissionGraph';
import { MeshApprovalQueue } from './components/MeshApprovalQueue';
import { MeshAgentFleetTable } from './components/MeshAgentFleetTable';
import { MeshMobileShowcase } from './components/MeshMobileShowcase';
import { NewMissionModal } from './components/NewMissionModal';
import { AgentTimeline } from './components/AgentTimeline';
import { AuditLogViewer } from './components/AuditLogViewer';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [, setTasks] = useState<Task[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApprovalItem[]>([]);
  const [isLoadingApprovals, setIsLoadingApprovals] = useState(false);
  const [approvalsError, setApprovalsError] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditFilter, setAuditFilter] = useState<string | undefined>(undefined);
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [isNewMissionOpen, setIsNewMissionOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // 2-second real-time polling
  useEffect(() => {
    const poll = async () => {
      try {
        // 1. Fetch recent tasks
        const taskData = await api.listTasks();
        setTasks(taskData.tasks);

        const currentId = activeTaskId || (taskData.tasks.length > 0 ? taskData.tasks[0].id : null);
        if (currentId) {
          if (!activeTaskId) setActiveTaskId(currentId);
          const taskDetail = await api.getTask(currentId);
          setActiveTask(taskDetail);
        }

        // 2. Fetch real pending approvals across all tasks
        try {
          const approvalsData = await api.listPendingApprovals();
          setPendingApprovals(approvalsData.approvals || []);
          setApprovalsError(null);
        } catch (apprErr: any) {
          setApprovalsError(apprErr?.message || 'Error fetching approvals');
        }

        // 3. Fetch audit logs
        const auditData = await api.listAuditLogs(auditFilter);
        setAuditLogs(auditData.logs);
      } catch (err) {
        // Backend live reload or initialization
      } finally {
        setIsLoadingApprovals(false);
      }
    };

    setIsLoadingApprovals(true);
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [activeTaskId, auditFilter]);

  const handleCreateTask = async (goal: string) => {
    setIsDeploying(true);
    try {
      const newTask = await api.createTask(goal);
      setActiveTaskId(newTask.id);
      setActiveTask(newTask);
      setIsNewMissionOpen(false);
      setActiveTab('overview');
    } catch (err) {
      alert(`Error creating mission: ${err}`);
    } finally {
      setIsDeploying(false);
    }
  };

  const handleApprovalAction = async (taskId: string, approved: boolean, feedback?: string) => {
    setIsSubmittingApproval(true);
    try {
      await api.submitApproval(taskId, approved, feedback);
      // Immediately refresh pending approvals and tasks
      const approvalsData = await api.listPendingApprovals();
      setPendingApprovals(approvalsData.approvals || []);
      const taskData = await api.listTasks();
      setTasks(taskData.tasks);
      if (activeTaskId === taskId) {
        const updated = await api.getTask(taskId);
        setActiveTask(updated);
      }
    } catch (err: any) {
      alert(`Error submitting approval decision: ${err?.message || err}`);
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#07090e', color: '#f8fafc', padding: '32px 24px' }}>
      <div style={{ maxWidth: '1440px', margin: '0 auto' }}>
        
        {/* Top Hero & Header matching screenshot */}
        <MeshHeader onOpenNewMission={() => setIsNewMissionOpen(true)} />

        {/* Section title */}
        <div style={{
          fontSize: '0.72rem',
          fontWeight: 700,
          color: '#64748b',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: '12px',
          paddingLeft: '4px'
        }}>
          Desktop Command Center • Production operations at a glance
        </div>

        {/* Main Desktop Window Frame matching screenshot */}
        <div style={{
          background: '#0a0e18',
          border: '1px solid #1c273e',
          borderRadius: '20px',
          boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
          overflow: 'hidden',
          display: 'flex',
          minHeight: '740px'
        }}>
          {/* Left Sidebar */}
          <MeshSidebar
            activeTab={activeTab}
            onTabChange={setActiveTab}
            pendingApprovalsCount={pendingApprovals.length}
          />

          {/* Main Dashboard Canvas */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            
            {/* Top Bar matching screenshot */}
            <div style={{
              padding: '16px 24px',
              borderBottom: '1px solid #172134',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px',
              background: '#0b101c'
            }}>
              <div>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  Good morning, Sandip Sah
                </h2>
                <p style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                  Your agent network is healthy. <span style={{ color: pendingApprovals.length > 0 ? '#fbbf24' : '#34d399', fontWeight: 600 }}>{pendingApprovals.length} action{pendingApprovals.length === 1 ? '' : 's'}</span> {pendingApprovals.length === 1 ? 'needs' : 'need'} approval.
                </p>
              </div>

              {/* Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {/* Search */}
                <div style={{
                  background: '#0e1524',
                  border: '1px solid #1f2b42',
                  borderRadius: '8px',
                  padding: '6px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '240px'
                }}>
                  <span style={{ color: '#64748b', fontSize: '0.8rem' }}>🔍</span>
                  <input
                    type="text"
                    placeholder="Search runs, agents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      outline: 'none',
                      color: '#f8fafc',
                      fontSize: '0.75rem',
                      width: '100%'
                    }}
                  />
                  <span style={{ fontSize: '0.62rem', color: '#475569', background: '#172134', padding: '1px 4px', borderRadius: '4px' }}>
                    ⌘K
                  </span>
                </div>

                {/* Notifications */}
                <button style={{
                  background: '#0e1524',
                  border: '1px solid #1f2b42',
                  borderRadius: '8px',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  position: 'relative'
                }}>
                  <span>🔔</span>
                  <span style={{
                    position: 'absolute',
                    top: '4px',
                    right: '4px',
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: '#f43f5e'
                  }}></span>
                </button>

                {/* New Mission Button */}
                <button
                  onClick={() => setIsNewMissionOpen(true)}
                  style={{
                    background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '7px 14px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
                  }}
                >
                  <span>⚡</span> + New Mission
                </button>

                {/* Profile Avatar */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #38bdf8, #818cf8)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '0.7rem',
                  letterSpacing: '0.04em',
                  color: '#090d16'
                }}>
                  SS
                </div>
              </div>
            </div>

            {/* Dashboard Content Container */}
            <div style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
              {activeTab === 'overview' && (
                <>
                  {/* KPI Stat Cards (4 across) */}
                  <MeshStatCards
                    activeCount={12}
                    successRate={98.4}
                    avgCost={0.42}
                    pendingApprovals={pendingApprovals.length}
                  />

                  {/* Middle Row: Live Mission Graph (65%) & Approval Queue (35%) */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(0, 1.8fr) minmax(0, 1.2fr)',
                    gap: '18px',
                    marginBottom: '20px'
                  }}>
                    <MeshMissionGraph
                      activeTask={activeTask}
                      onSelectNode={(node) => console.log('Selected node:', node)}
                    />
                    <MeshApprovalQueue
                      approvals={pendingApprovals}
                      isLoading={isLoadingApprovals}
                      error={approvalsError}
                      onApprove={(taskId, feedback) => handleApprovalAction(taskId, true, feedback)}
                      onReject={(taskId, feedback) => handleApprovalAction(taskId, false, feedback)}
                      isSubmitting={isSubmittingApproval}
                    />
                  </div>

                  {/* Bottom Row: Agent Fleet Performance Table */}
                  <MeshAgentFleetTable onNewAgent={() => setIsNewMissionOpen(true)} />
                </>
              )}

              {/* Runs & Traces Tab */}
              {(activeTab === 'runs' || activeTab === 'guardrails') && activeTask && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div style={{ background: '#0d1320', border: '1px solid #1a253a', borderRadius: '14px', padding: '16px' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '4px' }}>
                      Active Mission: {activeTask.goal}
                    </h3>
                    <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      Task ID: {activeTask.id} • Status: {activeTask.status} • Total Steps: {activeTask.subtasks?.length || 0}
                    </p>
                  </div>
                  <AgentTimeline task={activeTask} />
                </div>
              )}

              {/* Audit Log Tab */}
              {activeTab === 'audit' && (
                <AuditLogViewer
                  logs={auditLogs}
                  onFilterChange={setAuditFilter}
                  selectedFilter={auditFilter}
                />
              )}
            </div>
          </div>
        </div>

        {/* Lower Mobile Showcase Section matching bottom of screenshot */}
        <MeshMobileShowcase />

      </div>

      {/* New Mission Modal */}
      <NewMissionModal
        isOpen={isNewMissionOpen}
        onClose={() => setIsNewMissionOpen(false)}
        onSubmit={handleCreateTask}
        isDeploying={isDeploying}
      />
    </div>
  );
};
