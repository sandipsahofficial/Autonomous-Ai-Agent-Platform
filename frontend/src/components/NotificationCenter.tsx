import React, { useState, useEffect, useRef } from 'react';
import { Notification } from '../types';
import * as api from '../api/client';

export const NotificationCenter: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      setIsLoading(true);
      const res = await api.listNotifications();
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error('Error marking read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Error marking all read:', err);
    }
  };

  return (
    <div style={{ position: 'relative' }} ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: isOpen ? '#141d2e' : 'transparent',
          border: '1px solid',
          borderColor: isOpen ? '#222f46' : 'transparent',
          borderRadius: '8px',
          width: '32px',
          height: '32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#94a3b8',
          cursor: 'pointer',
          position: 'relative',
        }}
        title="In-App Notifications"
      >
        <span style={{ fontSize: '0.95rem' }}>🔔</span>
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute',
            top: '2px',
            right: '2px',
            minWidth: '16px',
            height: '16px',
            padding: '0 3px',
            borderRadius: '9999px',
            background: '#f43f5e',
            color: '#fff',
            fontSize: '0.62rem',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 6px rgba(244, 63, 94, 0.4)'
          }}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '38px',
          right: 0,
          width: '340px',
          background: '#0d1320',
          border: '1px solid #1a253a',
          borderRadius: '12px',
          boxShadow: '0 16px 36px rgba(0,0,0,0.5)',
          zIndex: 1000,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* Popover Header */}
          <div style={{
            padding: '12px 14px',
            borderBottom: '1px solid #1a253a',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#f8fafc' }}>
                Notifications
              </span>
              {unreadCount > 0 && (
                <span style={{
                  fontSize: '0.65rem',
                  padding: '1px 6px',
                  borderRadius: '9999px',
                  background: 'rgba(244, 63, 94, 0.15)',
                  color: '#f43f5e',
                  fontWeight: 700
                }}>
                  {unreadCount} new
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#38bdf8',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification Items List */}
          <div style={{ maxHeight: '340px', overflowY: 'auto' }}>
            {isLoading && notifications.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.78rem' }}>
                Loading updates...
              </div>
            ) : notifications.length === 0 ? (
              <div style={{ padding: '28px', textAlign: 'center', color: '#64748b', fontSize: '0.78rem' }}>
                No notifications. You are all caught up!
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  style={{
                    padding: '10px 14px',
                    borderBottom: '1px solid #141c2c',
                    background: n.is_read ? 'transparent' : 'rgba(56, 189, 248, 0.04)',
                    display: 'flex',
                    gap: '10px',
                    alignItems: 'flex-start',
                    transition: 'background 0.15s ease',
                  }}
                >
                  {/* Severity Dot */}
                  <span style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: getSeverityColor(n.severity),
                    marginTop: '4px',
                    flexShrink: 0
                  }} />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.76rem', fontWeight: n.is_read ? 600 : 700, color: '#f8fafc' }}>
                        {n.title}
                      </span>
                      {!n.is_read && (
                        <button
                          onClick={(e) => handleMarkRead(n.id, e)}
                          title="Mark as read"
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#64748b',
                            fontSize: '0.7rem',
                            cursor: 'pointer',
                            padding: '0 4px',
                          }}
                        >
                          ✓
                        </button>
                      )}
                    </div>
                    <p style={{ fontSize: '0.72rem', color: '#94a3b8', margin: '2px 0 4px 0', lineHeight: 1.35 }}>
                      {n.message}
                    </p>
                    <span style={{ fontSize: '0.64rem', color: '#475569' }}>
                      {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

function getSeverityColor(severity: Notification['severity']): string {
  switch (severity) {
    case 'SUCCESS': return '#34d399';
    case 'WARNING': return '#fbbf24';
    case 'ERROR': return '#f43f5e';
    default: return '#38bdf8';
  }
}
