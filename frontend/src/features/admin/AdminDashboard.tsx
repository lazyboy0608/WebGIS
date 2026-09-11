import React, { useEffect, useState } from 'react';
import { fetchDashboardStatsApi, type AdminDashboardStats } from '../../api/adminApi';
import '../../App.css';

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchDashboardStatsApi();
      setStats(data);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải số liệu thống kê hệ thống');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    // Tự động làm mới số liệu mỗi 30s
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="admin-loading-container">
        <div className="admin-spinner" />
        <span>Đang tải thông số hiệu năng và dữ liệu thống kê...</span>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="admin-error-box">
        <h3>Lỗi nạp dữ liệu thống kê</h3>
        <p>{error}</p>
        <button type="button" className="btn-primary" onClick={loadStats}>
          Thử lại
        </button>
      </div>
    );
  }

  // Chuẩn bị dữ liệu cho Biểu đồ Tăng trưởng (Growth Chart)
  const growthData = stats?.user_growth || [];
  const maxGrowthCount = Math.max(...growthData.map((d) => d.count), 5);
  const chartWidth = 500;
  const chartHeight = 180;
  const padding = 30;

  const points = growthData.map((d, i) => {
    const x = padding + (i / Math.max(growthData.length - 1, 1)) * (chartWidth - 2 * padding);
    const y = chartHeight - padding - (d.count / maxGrowthCount) * (chartHeight - 2 * padding);
    return { x, y, date: d.date, count: d.count };
  });

  const polylinePoints = points.map((p) => `${p.x},${p.y}`).join(' ');
  const areaPoints = points.length > 0
    ? `${padding},${chartHeight - padding} ${polylinePoints} ${points[points.length - 1].x},${chartHeight - padding}`
    : '';

  // Dữ liệu cho Biểu đồ Donut Phân bổ vai trò
  const totalRoles = (stats?.role_distribution.user || 0) + (stats?.role_distribution.admin || 0) || 1;
  const userPercent = Math.round(((stats?.role_distribution.user || 0) / totalRoles) * 100);
  const adminPercent = 100 - userPercent;

  // Tính toán chu vi vòng tròn Donut SVG (R = 50, C = 2 * PI * 50 = 314.159)
  const circumference = 314.16;
  const userStrokeDash = (userPercent / 100) * circumference;
  const adminStrokeDash = (adminPercent / 100) * circumference;

  return (
    <div className="admin-dashboard-view">
      {/* Header section */}
      <div className="admin-view-header">
        <div>
          <h2>Bảng điều khiển & Giám sát</h2>
          <p className="admin-subtitle">Theo dõi tài nguyên, người dùng và các chỉ số hiệu năng hệ thống thời gian thực</p>
        </div>
        <button type="button" className="btn-refresh" onClick={loadStats} title="Làm mới số liệu">
          🔄 Làm mới
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon" style={{ background: '#e0f2fe', color: '#0284c7' }}>👥</div>
          <div className="kpi-body">
            <span className="kpi-label">Tổng người dùng</span>
            <strong className="kpi-value">{stats?.total_users || 0}</strong>
          </div>
          <div className="kpi-footer">
            <span className="badge-pill success">Hoạt động: {stats?.active_users || 0}</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon" style={{ background: '#fef3c7', color: '#d97706' }}>🛡️</div>
          <div className="kpi-body">
            <span className="kpi-label">Quản trị viên</span>
            <strong className="kpi-value">{stats?.admin_users || 0}</strong>
          </div>
          <div className="kpi-footer">
            <span className="badge-pill admin">Role: Admin</span>
          </div>
        </div>

        {/* CPU Usage Card */}
        <div className="kpi-card">
          <div className="kpi-icon" style={{ background: '#ffedd5', color: '#ea580c' }}>⚡</div>
          <div className="kpi-body">
            <span className="kpi-label">Mức sử dụng CPU</span>
            <strong className="kpi-value">{stats?.cpu_usage_percent || 0}%</strong>
          </div>
          <div className="kpi-footer">
            <span className={`badge-pill ${(stats?.cpu_usage_percent || 0) > 85 ? 'admin' : 'teal'}`}>
              {stats?.cpu_cores || 4} Cores / Threads
            </span>
          </div>
        </div>

        {/* RAM Usage Card */}
        <div className="kpi-card">
          <div className="kpi-icon" style={{ background: '#ccfbf1', color: '#0d9488' }}>🧠</div>
          <div className="kpi-body">
            <span className="kpi-label">Bộ nhớ RAM</span>
            <strong className="kpi-value">{stats?.ram_usage_percent || 0}%</strong>
          </div>
          <div className="kpi-footer">
            <span className={`badge-pill ${(stats?.ram_usage_percent || 0) > 85 ? 'admin' : 'teal'}`}>
              {stats?.ram_used_gb || 0} / {stats?.ram_total_gb || 0} GB
            </span>
          </div>
        </div>

        {/* Disk Usage Card */}
        <div className="kpi-card">
          <div className="kpi-icon" style={{ background: '#f3e8ff', color: '#9333ea' }}>💽</div>
          <div className="kpi-body">
            <span className="kpi-label">Ổ đĩa máy chủ</span>
            <strong className="kpi-value">{stats?.disk_usage_percent || 0}%</strong>
          </div>
          <div className="kpi-footer">
            <span className="badge-pill purple">
              {stats?.disk_used_gb || 0} / {stats?.disk_total_gb || 0} GB
            </span>
          </div>
        </div>
      </div>

      {/* Real-time Performance Row */}
      <div className="performance-panel">
        <div className="perf-card">
          <div className="perf-header">
            <div className="live-indicator">
              <span className="pulse-dot" />
              <strong>Truy cập thời gian thực</strong>
            </div>
            <span className="perf-badge live">Live</span>
          </div>
          <div className="perf-number">{stats?.active_sessions || 1}</div>
          <small className="perf-desc">Số phiên người dùng đang hoạt động trong hệ thống</small>
        </div>

        <div className="perf-card">
          <div className="perf-header">
            <strong>Redis Cache Hit Ratio</strong>
            <span className="perf-badge success">{stats?.cache_hit_ratio}%</span>
          </div>
          <div className="progress-bar-bg">
            <div
              className="progress-bar-fill"
              style={{ width: `${stats?.cache_hit_ratio || 90}%`, background: '#10b981' }}
            />
          </div>
          <small className="perf-desc">Tốc độ phản hồi MVT Vector Tiles & Query tối ưu</small>
        </div>

        <div className="perf-card">
          <div className="perf-header">
            <strong>Cơ sở dữ liệu PostGIS</strong>
            <span className="perf-badge success">Online</span>
          </div>
          <div className="db-status-row">
            <span className="status-icon-check">✓</span>
            <span className="db-status-text">{stats?.database_status || 'Đang hoạt động'}</span>
          </div>
          <small className="perf-desc">PostgreSQL 16 với phần mở rộng PostGIS</small>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="admin-charts-grid">
        {/* User Growth Line Chart */}
        <div className="chart-container-card">
          <div className="chart-card-header">
            <h3>📈 Tăng trưởng người dùng</h3>
            <span className="chart-tag">30 ngày qua</span>
          </div>
          <div className="svg-chart-wrapper">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="admin-svg-chart">
              <defs>
                <linearGradient id="growthGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#1d7a8c" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#1d7a8c" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Grid Lines */}
              <line x1={padding} y1={padding} x2={chartWidth - padding} y2={padding} stroke="#e5e7eb" strokeDasharray="3 3" />
              <line x1={padding} y1={chartHeight / 2} x2={chartWidth - padding} y2={chartHeight / 2} stroke="#e5e7eb" strokeDasharray="3 3" />
              <line x1={padding} y1={chartHeight - padding} x2={chartWidth - padding} y2={chartHeight - padding} stroke="#cbd5e1" />

              {/* Area */}
              {areaPoints && <polygon points={areaPoints} fill="url(#growthGradient)" />}

              {/* Line */}
              {polylinePoints && (
                <polyline
                  points={polylinePoints}
                  fill="none"
                  stroke="#1d7a8c"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Data Points */}
              {points.map((p, idx) => (
                <g key={idx} className="chart-point-group">
                  <circle cx={p.x} cy={p.y} r="4.5" fill="#ffffff" stroke="#1d7a8c" strokeWidth="2.5" />
                  <title>{`${p.date}: ${p.count} người dùng`}</title>
                </g>
              ))}
            </svg>
          </div>
          <div className="chart-footer-note">
            Tổng cộng: <strong>{stats?.total_users}</strong> tài khoản đăng ký
          </div>
        </div>

        {/* Role Distribution Donut Chart */}
        <div className="chart-container-card">
          <div className="chart-card-header">
            <h3>🍩 Phân bổ vai trò người dùng</h3>
            <span className="chart-tag">Tất cả tài khoản</span>
          </div>

          <div className="donut-chart-wrapper">
            <div className="donut-svg-container">
              <svg viewBox="0 0 140 140" className="donut-svg">
                {/* Background circle */}
                <circle cx="70" cy="70" r="50" fill="none" stroke="#e2e8f0" strokeWidth="18" />

                {/* User segment (Teal) */}
                <circle
                  cx="70"
                  cy="70"
                  r="50"
                  fill="none"
                  stroke="#0284c7"
                  strokeWidth="18"
                  strokeDasharray={`${userStrokeDash} ${circumference}`}
                  strokeDashoffset="0"
                  transform="rotate(-90 70 70)"
                />

                {/* Admin segment (Orange/Gold) */}
                <circle
                  cx="70"
                  cy="70"
                  r="50"
                  fill="none"
                  stroke="#e4572e"
                  strokeWidth="18"
                  strokeDasharray={`${adminStrokeDash} ${circumference}`}
                  strokeDashoffset={-userStrokeDash}
                  transform="rotate(-90 70 70)"
                />

                <text x="70" y="66" textAnchor="middle" className="donut-center-number">
                  {stats?.total_users}
                </text>
                <text x="70" y="82" textAnchor="middle" className="donut-center-label">
                  Tài khoản
                </text>
              </svg>
            </div>

            <div className="donut-legend">
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#0284c7' }} />
                <span className="legend-name">Người dùng (User)</span>
                <strong className="legend-val">{stats?.role_distribution.user || 0} ({userPercent}%)</strong>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#e4572e' }} />
                <span className="legend-name">Quản trị viên (Admin)</span>
                <strong className="legend-val">{stats?.role_distribution.admin || 0} ({adminPercent}%)</strong>
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#10b981' }} />
                <span className="legend-name">Đang hoạt động</span>
                <strong className="legend-val">{stats?.status_distribution.active || 0}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
