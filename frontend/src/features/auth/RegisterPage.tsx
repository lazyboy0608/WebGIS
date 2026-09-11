import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { registerApi } from './authService';
import { AuthLayout } from './AuthLayout';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    full_name: '',
    phone_number: '',
    email: '',
    date_of_birth: '',
    password: '',
    confirm_password: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [popup, setPopup] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPopup(null);

    // Client side validation
    if (
      !formData.full_name.trim() ||
      !formData.phone_number.trim() ||
      !formData.email.trim() ||
      !formData.date_of_birth ||
      !formData.password ||
      !formData.confirm_password
    ) {
      setPopup({ type: 'error', message: 'Vui lòng điền đầy đủ tất cả thông tin bắt buộc.' });
      return;
    }

    if (formData.password !== formData.confirm_password) {
      setPopup({ type: 'error', message: 'Mật khẩu xác nhận không trùng khớp.' });
      return;
    }

    if (formData.password.length < 6) {
      setPopup({ type: 'error', message: 'Mật khẩu phải có ít nhất 6 ký tự.' });
      return;
    }

    try {
      setSubmitting(true);
      await registerApi({
        full_name: formData.full_name.trim(),
        phone_number: formData.phone_number.trim(),
        email: formData.email.trim(),
        date_of_birth: formData.date_of_birth,
        password: formData.password,
        confirm_password: formData.confirm_password,
      });

      // Show success pop-up (green) and navigate to login
      setPopup({ type: 'success', message: 'Đăng ký thành công!' });
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 1500);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Đăng ký thất bại!';
      setPopup({ type: 'error', message: errorMsg });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Tạo tài khoản mới"
      subtitle="Nhập thông tin người dùng để đăng ký tài khoản WebGIS"
      popup={popup}
    >
      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="auth-field-group">
          <label htmlFor="reg-full_name">Họ và tên *</label>
          <div className="auth-input-wrapper">
            <input
              id="reg-full_name"
              name="full_name"
              type="text"
              className="auth-input"
              placeholder="Nguyễn Văn A"
              value={formData.full_name}
              onChange={handleChange}
              required
            />
          </div>
        </div>

        <div className="auth-form-row">
          <div className="auth-field-group">
            <label htmlFor="reg-phone_number">Số điện thoại *</label>
            <div className="auth-input-wrapper">
              <input
                id="reg-phone_number"
                name="phone_number"
                type="tel"
                className="auth-input"
                placeholder="0912345678"
                value={formData.phone_number}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="auth-field-group">
            <label htmlFor="reg-date_of_birth">Ngày sinh *</label>
            <div className="auth-input-wrapper">
              <input
                id="reg-date_of_birth"
                name="date_of_birth"
                type="date"
                className="auth-input"
                value={formData.date_of_birth}
                onChange={handleChange}
                required
              />
            </div>
          </div>
        </div>

        <div className="auth-field-group">
          <label htmlFor="reg-email">Email *</label>
          <div className="auth-input-wrapper">
            <input
              id="reg-email"
              name="email"
              type="email"
              className="auth-input"
              placeholder="nguyenvana@gmail.com"
              value={formData.email}
              onChange={handleChange}
              required
              autoComplete="email"
            />
          </div>
        </div>

        <div className="auth-form-row">
          <div className="auth-field-group">
            <label htmlFor="reg-password">Mật khẩu *</label>
            <div className="auth-input-wrapper">
              <input
                id="reg-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                required
                autoComplete="new-password"
              />
            </div>
          </div>

          <div className="auth-field-group">
            <label htmlFor="reg-confirm_password">Xác nhận mật khẩu *</label>
            <div className="auth-input-wrapper">
              <input
                id="reg-confirm_password"
                name="confirm_password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                placeholder="••••••••"
                value={formData.confirm_password}
                onChange={handleChange}
                required
                autoComplete="new-password"
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '-0.25rem' }}>
          <button
            type="button"
            className="auth-input-toggle"
            style={{ position: 'static' }}
            onClick={() => setShowPassword((prev) => !prev)}
          >
            {showPassword ? '👁️ Ẩn mật khẩu' : '👁️ Hiện mật khẩu'}
          </button>
        </div>

        <button type="submit" className="auth-submit-btn" disabled={submitting}>
          {submitting ? 'Đang khởi tạo tài khoản...' : 'Đăng ký tài khoản'}
        </button>
      </form>

      <div className="auth-footer-link">
        Đã có tài khoản?
        <Link to="/login">Đăng nhập</Link>
      </div>
    </AuthLayout>
  );
};
