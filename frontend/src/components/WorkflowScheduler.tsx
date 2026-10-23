import React, { useState, useEffect } from 'react';
import { WorkflowSchedule, ScheduleExecution } from '../types';
import * as api from '../api/client';

export const WorkflowScheduler: React.FC = () => {
  const [schedules, setSchedules] = useState<WorkflowSchedule[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);
  const [executions, setExecutions] = useState<ScheduleExecution[]>([]);
  const [isLoadingExecs, setIsLoadingExecs] = useState<boolean>(false);

  // Form State
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [scheduleType, setScheduleType] = useState<'one_time' | 'recurring'>('recurring');
  const [cronExpression, setCronExpression] = useState('0 9 * * 1-5');
  const [timezoneStr, setTimezoneStr] = useState('America/New_York');
  const [allowOverlap, setAllowOverlap] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchSchedules = async () => {
    try {
      setIsLoading(true);
      const res = await api.listSchedules();
      setSchedules(res.schedules || []);
    } catch (err) {
      console.error('Failed to load schedules:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedules();
  }, []);

  const openCreateModal = () => {
    setName('');
    setGoal('');
    setScheduleType('recurring');
    setCronExpression('0 9 * * 1-5');
    setTimezoneStr('America/New_York');
    setAllowOverlap(false);
    setIsFormOpen(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !goal.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createSchedule({
        name,
        goal,
        schedule_type: scheduleType,
        cron_expression: scheduleType === 'recurring' ? cronExpression : undefined,
        timezone_str: timezoneStr,
        allow_overlap: allowOverlap,
        is_enabled: true,
      });
      setIsFormOpen(false);
      await fetchSchedules();
    } catch (err: any) {
      alert(`Error creating schedule: ${err?.message || err}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTriggerNow = async (schedId: string) => {
    try {
      const res = await api.triggerScheduleManual(schedId);
      alert(`Dispatched execution! Run status: ${res.status}`);
      await fetchSchedules();
    } catch (err: any) {
      alert(`Failed to trigger: ${err?.message || err}`);
    }
  };

  const handleDelete = async (schedId: string) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await api.deleteSchedule(schedId);
      if (selectedScheduleId === schedId) {
        setSelectedScheduleId(null);
        setExecutions([]);
      }
      await fetchSchedules();
    } catch (err: any) {
      alert(`Delete failed: ${err?.message || err}`);
    }
  };

  const viewExecutions = async (schedId: string) => {
    setSelectedScheduleId(schedId);
    setIsLoadingExecs(true);
    try {
      const res = await api.listScheduleExecutions(schedId);
      setExecutions(res.executions || []);
    } catch (err) {
      console.error('Failed to load executions:', err);
    } finally {
      setIsLoadingExecs(false);
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
            Workflow Scheduler & Cron Engine
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
            Automate agent missions with standard cron expressions, timezone anchoring, non-overlapping execution locks, and idempotency guarantees.
          </p>
        </div>
        <button
          onClick={openCreateModal}
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
          <span>+</span> Create Schedule
        </button>
      </div>

      {/* Schedules List & Execution History Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedScheduleId ? '1.5fr 1fr' : '1fr', gap: '16px' }}>
        {/* Schedules Table */}
        <div style={{
          background: '#0d1320',
          border: '1px solid #1a253a',
          borderRadius: '14px',
          padding: '18px',
          overflowX: 'auto',
        }}>
          {isLoading ? (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Loading schedules...</div>
          ) : schedules.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
              No automated schedules configured. Create a schedule to trigger autonomous agent workflows on recurring intervals.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1a253a', color: '#64748b', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '10px 12px' }}>Name & Goal</th>
                  <th style={{ padding: '10px 12px' }}>Cron & Timezone</th>
                  <th style={{ padding: '10px 12px' }}>Next Run</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {schedules.map((s) => (
                  <tr
                    key={s.id}
                    style={{
                      borderBottom: '1px solid #141c2c',
                      background: selectedScheduleId === s.id ? '#121a2b' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontWeight: 700, color: '#f8fafc' }}>{s.name}</div>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {s.goal}
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 700 }}>
                        {s.cron_expression || 'One-Time'}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>{s.timezone_str}</div>
                    </td>
                    <td style={{ padding: '12px', color: '#cbd5e1', fontSize: '0.74rem' }}>
                      {s.next_run_at ? new Date(s.next_run_at).toLocaleString() : '—'}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        background: s.is_enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                        color: s.is_enabled ? '#34d399' : '#94a3b8',
                        border: `1px solid ${s.is_enabled ? 'rgba(16, 185, 129, 0.3)' : 'rgba(148, 163, 184, 0.3)'}`,
                      }}>
                        {s.is_enabled ? 'ACTIVE' : 'PAUSED'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          onClick={() => handleTriggerNow(s.id)}
                          title="Trigger manual execution now"
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
                          ⚡ Run
                        </button>
                        <button
                          onClick={() => viewExecutions(s.id)}
                          style={{
                            background: '#141d2e',
                            border: '1px solid #222f46',
                            color: '#94a3b8',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            cursor: 'pointer',
                          }}
                        >
                          History
                        </button>
                        <button
                          onClick={() => handleDelete(s.id)}
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

        {/* Executions History Drawer */}
        {selectedScheduleId && (
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
              <h4 style={{ fontSize: '0.88rem', fontWeight: 800, color: '#f8fafc' }}>Execution History</h4>
              <button
                onClick={() => setSelectedScheduleId(null)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {isLoadingExecs ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Loading history...</div>
            ) : executions.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.75rem' }}>
                No executions recorded yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '420px', overflowY: 'auto' }}>
                {executions.map((e) => (
                  <div
                    key={e.id}
                    style={{
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      fontSize: '0.74rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{
                        fontWeight: 800,
                        color: e.status === 'SUCCESS' ? '#34d399' : e.status === 'RUNNING' ? '#38bdf8' : '#f87171',
                      }}>
                        {e.status}
                      </span>
                      <span style={{ color: '#64748b', fontSize: '0.68rem' }}>
                        {new Date(e.executed_time).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ color: '#64748b', fontFamily: 'monospace', fontSize: '0.65rem' }}>
                      Key: {e.idempotency_key}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Create Schedule Modal */}
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
          padding: '20px',
        }}>
          <div style={{
            background: '#0d1320',
            border: '1px solid #1a253a',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '520px',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>
                Configure Workflow Schedule
              </h3>
              <button
                onClick={() => setIsFormOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#64748b', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                  Schedule Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Daily Vulnerability Audit"
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
                  Autonomous Goal / Instructions *
                </label>
                <textarea
                  rows={3}
                  required
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="Specific mission prompt executed on each scheduled trigger..."
                  style={{
                    width: '100%',
                    background: '#121a2b',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: '#f8fafc',
                    fontSize: '0.8rem'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Cadence Type
                  </label>
                  <select
                    value={scheduleType}
                    onChange={(e) => setScheduleType(e.target.value as any)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '0.82rem'
                    }}
                  >
                    <option value="recurring">Recurring Cron</option>
                    <option value="one_time">One-Time Run</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Cron Expression
                  </label>
                  <input
                    type="text"
                    disabled={scheduleType === 'one_time'}
                    value={cronExpression}
                    onChange={(e) => setCronExpression(e.target.value)}
                    placeholder="0 9 * * 1-5"
                    style={{
                      width: '100%',
                      background: scheduleType === 'one_time' ? '#0d1320' : '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontFamily: 'monospace',
                      fontSize: '0.82rem'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>
                    Timezone
                  </label>
                  <select
                    value={timezoneStr}
                    onChange={(e) => setTimezoneStr(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#121a2b',
                      border: '1px solid #1e293b',
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: '#f8fafc',
                      fontSize: '0.82rem'
                    }}
                  >
                    <option value="America/New_York">America/New_York (EST/EDT)</option>
                    <option value="UTC">UTC (Coordinated Universal)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                    <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '22px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: '#cbd5e1', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={allowOverlap}
                      onChange={(e) => setAllowOverlap(e.target.checked)}
                    />
                    <span>Allow Overlap Lock</span>
                  </label>
                </div>
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
                  }}
                >
                  {isSubmitting ? 'Creating...' : 'Activate Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
