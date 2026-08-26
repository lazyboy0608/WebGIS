import React from 'react';
import './auth.css';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
  popup?: { type: 'success' | 'error'; message: string } | null;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle, popup }) => {
  return (
    <div className="auth-container">
      {popup && (
        <div className={`auth-popup auth-popup-${popup.type}`}>
          <span className="auth-popup-icon">{popup.type === 'success' ? '✓' : '✕'}</span>
          <span>{popup.message}</span>
        </div>
      )}

      <div className="auth-bg-shapes">
        <div className="auth-blob auth-blob-1" />
        <div className="auth-blob auth-blob-2" />
        <div className="auth-grid-overlay" />
      </div>

      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand">
            <span>🌐 WebGIS Seismic Atlas</span>
          </div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>

        {children}
      </div>
    </div>
  );
};
