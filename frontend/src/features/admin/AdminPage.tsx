import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { AdminDashboard } from './AdminDashboard';
import { UserManagement } from './UserManagement';
import '../../App.css';

export const AdminPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'users'>('dashboard');
  const [showUserDropdown, setShowUserDropdown] = useState<boolean>(false);
  const userDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userDropdownRef.current && !userDropdownRef.current.contains(event.target as Node)) {
        setShowUserDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase()
    : 'AD';

  return (
    <main className="shell admin-shell">
      {/* ── 1. TOPBAR HEADER ──────────────────────────────────────────────── */}
      <header className="topbar">
        <div>
          <span className="eyebrow">WEBGIS / HỆ THỐNG QUẢN TRỊ</span>
          <h1 style={{ color: '#172326' }}>Quản trị & Giám sát hệ thống</h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* User Dropdown */}
          {user && (
            <div className="user-dropdown-container" ref={userDropdownRef}>
              <button
                type="button"
                className={`user-dropdown-btn ${showUserDropdown ? 'active' : ''}`}
                onClick={() => setShowUserDropdown((prev) => !prev)}
                aria-expanded={showUserDropdown}
              >
                <div className="user-dropdown-avatar" style={{ background: '#e4572e' }}>
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt={user.full_name} className="avatar-img-sm" />
                  ) : (
                    <span>{initials}</span>
                  )}
                </div>
                <span className="user-dropdown-name">{user.full_name || user.email}</span>
                <span className="user-dropdown-caret">{showUserDropdown ? '▲' : '▼'}</span>
              </button>

              {showUserDropdown && (
                <div className="user-dropdown-menu">
                  <div className="user-dropdown-header">
                    <div className="user-dropdown-header-name">{user.full_name}</div>
                    <div className="user-dropdown-header-email">{user.email}</div>
                    <span className="role-tag admin">Quản trị viên</span>
                  </div>
                  <div className="user-dropdown-divider" />
                  <button
                    type="button"
                    className="user-dropdown-item"
                    onClick={() => {
                      setShowUserDropdown(false);
                      navigate('/profile');
                    }}
                  >
                    <span className="menu-icon">👤</span>
                    <span>Thông tin cá nhân</span>
                  </button>
                  <button
                    type="button"
                    className="user-dropdown-item logout-item"
                    onClick={() => {
                      setShowUserDropdown(false);
                      handleLogout();
                    }}
                  >
                    <span className="menu-icon">🚪</span>
                    <span>Đăng xuất</span>
                  </button>
                </div>
              )}
            </div>
          )}

          <span className="connection">
            <i /> Đã kết nối PostGIS
          </span>
        </div>
      </header>

      {/* ── 2. ADMIN WORKSPACE (SIDEBAR + MAIN CONTENT) ────────────────────── */}
      <section className="admin-workspace">
        {/* Admin Navigation Sidebar */}
        <aside className="admin-sidebar">
          <div className="admin-nav-menu">
            <button
              type="button"
              className={`admin-nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <span className="nav-icon">📊</span>
              <div className="nav-text-group">
                <span className="nav-title">Bảng điều khiển</span>
                <small className="nav-desc">Thống kê & Giám sát</small>
              </div>
            </button>

            <button
              type="button"
              className={`admin-nav-item ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              <span className="nav-icon">👥</span>
              <div className="nav-text-group">
                <span className="nav-title">Quản lý người dùng</span>
                <small className="nav-desc">Tài khoản & Phân quyền</small>
              </div>
            </button>
          </div>

          <div className="admin-sidebar-footer">
            <div className="admin-system-info">
              <span className="system-dot" />
              <strong>WebGIS Admin v2.0</strong>
            </div>
            <small>Chế độ Quản trị Hệ thống</small>
          </div>
        </aside>

        {/* Main Admin Content Body */}
        <div className="admin-content-panel">
          {activeTab === 'dashboard' ? <AdminDashboard /> : <UserManagement />}
        </div>
      </section>
    </main>
  );
};
