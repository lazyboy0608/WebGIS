import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { AuthLayout } from './AuthLayout';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [popup, setPopup] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPopup(null);

    if (!email.trim() || !password) {
      setPopup({ type: 'error', message: 'Vui lòng nhập đầy đủ Email và Mật khẩu.' });
      return;
    }

    try {
      setSubmitting(true);
      // Gọi login() từ AuthContext — nó gọi API và cập nhật user state trong context
      await login({ email: email.trim(), password });

      // Hiển thị popup thành công rồi chuyển hướng
      setPopup({ type: 'success', message: 'Đăng nhập thành công!' });

      // Delay 1.5s để user thấy popup xanh trước khi navigate
      setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 1500);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Đăng nhập thất bại!';
      setPopup({ type: 'error', message: errorMsg });
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Đăng nhập tài khoản"
      subtitle="Nhập Email và Mật khẩu để truy cập hệ thống WebGIS Atlas"
      popup={popup}
    >
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="auth-field-group">
          <label htmlFor="login-email">Email</label>
          <div className="auth-input-wrapper">
            <input
              id="login-email"
              type="email"
              className="auth-input"
              placeholder="nhanvien@geospatial.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
        </div>

        <div className="auth-field-group">
          <label htmlFor="login-password">Mật khẩu</label>
          <div className="auth-input-wrapper">
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              className="auth-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <button
              type="button"
              className="auth-input-toggle"
              onClick={() => setShowPassword((prev) => !prev)}
            >
              {showPassword ? 'Ẩn' : 'Hiện'}
            </button>
          </div>
        </div>

        <button type="submit" className="auth-submit-btn" disabled={submitting}>
          {submitting ? 'Đang xác thực...' : 'Đăng nhập'}
        </button>
      </form>

      <div className="auth-footer-link">
        Chưa có tài khoản?
        <Link to="/register">Đăng ký ngay</Link>
      </div>
    </AuthLayout>
  );
};
