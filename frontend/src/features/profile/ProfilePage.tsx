import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { updateProfileApi, uploadAvatarApi } from '../auth/authService';
import '../../App.css';

// Chuyển đổi từ ISO (YYYY-MM-DD) sang hiển thị kiểu Việt Nam (DD/MM/YYYY)
function formatIsoToDisplayDate(isoStr?: string | null): string {
  if (!isoStr) return '';
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(isoStr)) return isoStr;
  const match = isoStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    const [, y, m, d] = match;
    return `${d}/${m}/${y}`;
  }
  return isoStr;
}

// Chuyển đổi từ hiển thị (DD/MM/YYYY) sang chuẩn ISO (YYYY-MM-DD) cho Backend
function formatDisplayToIsoDate(displayStr: string): string | null {
  const trimmed = displayStr.trim();
  if (!trimmed) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed;
  
  const match = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (match) {
    const [, d, m, y] = match;
    const day = parseInt(d, 10);
    const month = parseInt(m, 10);
    const year = parseInt(y, 10);

    if (day < 1 || day > 31 || month < 1 || month > 12 || year < 1900 || year > 2100) {
      return null;
    }
    return `${y}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  }
  return null;
}

export const ProfilePage: React.FC = () => {
  const { user, updateUser, logout } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [phoneNumber, setPhoneNumber] = useState(user?.phone_number || '');
  const [dateOfBirthDisplay, setDateOfBirthDisplay] = useState(() => 
    formatIsoToDisplayDate(user?.date_of_birth)
  );
  
  const [avatarPreview, setAvatarPreview] = useState<string | null>(user?.avatar_url || null);
  const [selectedAvatarFile, setSelectedAvatarFile] = useState<File | null>(null);
  
  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (<= 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setErrorMsg('Ảnh đại diện không được vượt quá 5MB');
      return;
    }

    setSelectedAvatarFile(file);
    const objectUrl = URL.createObjectURL(file);
    setAvatarPreview(objectUrl);
    setErrorMsg(null);
    setSuccessMsg(null);
  };

  const handleDobChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value;
    // Cho phép nhập số và dấu gạch chéo
    val = val.replace(/[^\d/]/g, '');
    setDateOfBirthDisplay(val);
    setErrorMsg(null);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    // Validate ngày sinh theo định dạng DD/MM/YYYY
    let isoDob: string | undefined = undefined;
    if (dateOfBirthDisplay.trim()) {
      const converted = formatDisplayToIsoDate(dateOfBirthDisplay);
      if (!converted) {
        setErrorMsg('Ngày sinh không hợp lệ. Vui lòng nhập đúng định dạng dd/mm/yyyy (ví dụ: 08/06/2004)');
        return;
      }
      isoDob = converted;
    }

    setSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      let latestUser = user;

      // 1. Upload avatar nếu có file mới được chọn
      if (selectedAvatarFile) {
        setUploadingAvatar(true);
        latestUser = await uploadAvatarApi(selectedAvatarFile);
        setSelectedAvatarFile(null);
        setUploadingAvatar(false);
      }

      // 2. Cập nhật thông tin profile
      const updatedUser = await updateProfileApi({
        full_name: fullName.trim(),
        phone_number: phoneNumber.trim(),
        date_of_birth: isoDob,
      });

      // Gộp dữ liệu mới nhất
      const finalUser = {
        ...updatedUser,
        avatar_url: latestUser.avatar_url ?? updatedUser.avatar_url,
      };

      updateUser(finalUser);
      setDateOfBirthDisplay(formatIsoToDisplayDate(finalUser.date_of_birth));
      setSuccessMsg('Cập nhật thông tin cá nhân thành công!');
    } catch (err: any) {
      setErrorMsg(err.message || 'Lỗi khi cập nhật thông tin');
    } finally {
      setSaving(false);
      setUploadingAvatar(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  if (!user) {
    return null;
  }

  // Chữ cái đầu tiên nếu không có avatar
  const initials = user.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase()
    : 'U';

  const homePath = user.role === 'admin' ? '/admin' : '/dashboard';
  const backBtnText = user.role === 'admin' ? '← Quay lại Trang Quản trị' : '← Quay lại Bản đồ';

  return (
    <div className="profile-layout">
      {/* Top Header */}
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            type="button"
            className="back-btn"
            onClick={() => navigate(homePath)}
            title={backBtnText}
          >
            {backBtnText}
          </button>
          <div>
            <span className="eyebrow">TÀI KHOẢN NGƯỜI DÙNG</span>
            <h1 style={{ color: '#172326' }}>Thông tin cá nhân</h1>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button type="button" className="logout-btn" onClick={handleLogout}>
            Đăng xuất
          </button>
        </div>
      </header>

      {/* Main Profile Container */}
      <main className="profile-container">
        <div className="profile-card">
          {/* Avatar Section */}
          <div className="profile-avatar-section">
            <div className="avatar-wrapper">
              {avatarPreview ? (
                <img
                  src={avatarPreview}
                  alt={user.full_name}
                  className="profile-avatar-img"
                  onError={() => setAvatarPreview(null)}
                />
              ) : (
                <div className="profile-avatar-placeholder">
                  {initials}
                </div>
              )}

              <button
                type="button"
                className="avatar-edit-badge"
                onClick={() => fileInputRef.current?.click()}
                title="Thay đổi ảnh đại diện"
              >
                📷
              </button>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={handleAvatarFileChange}
            />

            <div className="avatar-meta">
              <h2 className="profile-user-name">{user.full_name || 'Người dùng'}</h2>
              <span className={`role-tag ${user.role}`}>
                {user.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}
              </span>
              <p className="avatar-hint">Nhấp vào biểu tượng máy ảnh để tải ảnh đại diện từ máy tính</p>
            </div>
          </div>

          <hr className="profile-divider" />

          {/* Messages */}
          {successMsg && <div className="profile-alert success">{successMsg}</div>}
          {errorMsg && <div className="profile-alert error">{errorMsg}</div>}

          {/* Form Section */}
          <form className="profile-form" onSubmit={handleSave}>
            <div className="profile-form-grid">
              {/* Họ và tên */}
              <div className="form-group">
                <label className="field-label" htmlFor="full_name">
                  Họ và tên <span style={{ color: '#ff6b6b' }}>*</span>
                </label>
                <input
                  id="full_name"
                  type="text"
                  className="profile-input"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Nhập họ và tên"
                  required
                />
              </div>

              {/* Số điện thoại */}
              <div className="form-group">
                <label className="field-label" htmlFor="phone_number">
                  Số điện thoại <span style={{ color: '#ff6b6b' }}>*</span>
                </label>
                <input
                  id="phone_number"
                  type="text"
                  className="profile-input"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="Nhập số điện thoại"
                  required
                />
              </div>

              {/* Ngày sinh */}
              <div className="form-group">
                <label className="field-label" htmlFor="date_of_birth">
                  Ngày sinh (dd/mm/yyyy)
                </label>
                <input
                  id="date_of_birth"
                  type="text"
                  className="profile-input"
                  value={dateOfBirthDisplay}
                  onChange={handleDobChange}
                  placeholder="dd/mm/yyyy (ví dụ: 08/06/2004)"
                  maxLength={10}
                />
                <small className="field-hint">Định dạng: ngày/tháng/năm (dd/mm/yyyy)</small>
              </div>

              {/* Email (Read only) */}
              <div className="form-group">
                <label className="field-label" htmlFor="email">
                  Địa chỉ Email <span className="readonly-badge">Chỉ đọc</span>
                </label>
                <input
                  id="email"
                  type="email"
                  className="profile-input readonly"
                  value={user.email}
                  readOnly
                  disabled
                />
                <small className="field-hint">Email được dùng làm định danh đăng nhập và không thể thay đổi.</small>
              </div>
            </div>

            {/* Actions */}
            <div className="profile-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => navigate(homePath)}
              >
                Hủy bỏ
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={saving || uploadingAvatar}
              >
                {saving || uploadingAvatar ? 'Đang lưu...' : 'Lưu thay đổi'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};
