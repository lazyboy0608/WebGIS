import React, { useEffect, useState, useMemo } from 'react';
import {
  fetchAdminUsersApi,
  createAdminUserApi,
  updateAdminUserApi,
  resetUserPasswordApi,
  deleteAdminUserApi,
  type AdminUserItem,
  type AdminUserCreatePayload,
} from '../../api/adminApi';
import { useAuth } from '../auth/AuthContext';
import '../../App.css';

// Helper: Format ISO YYYY-MM-DD -> DD/MM/YYYY
function formatIsoToDisplayDate(isoStr?: string | null): string {
  if (!isoStr) return '—';
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(isoStr)) return isoStr;
  const match = isoStr.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    const [, y, m, d] = match;
    return `${d}/${m}/${y}`;
  }
  return isoStr;
}

// Helper: Format DD/MM/YYYY -> YYYY-MM-DD
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

export const UserManagement: React.FC = () => {
  const { user: currentAdmin } = useAuth();

  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modals state
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [showEditModal, setShowEditModal] = useState<boolean>(false);
  const [showResetModal, setShowResetModal] = useState<boolean>(false);
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);

  // Target user for actions
  const [selectedUser, setSelectedUser] = useState<AdminUserItem | null>(null);

  // Form states - Add User
  const [newFullName, setNewFullName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newDobDisplay, setNewDobDisplay] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'user' | 'admin'>('user');
  const [newIsActive, setNewIsActive] = useState(true);

  // Form states - Edit User
  const [editFullName, setEditFullName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editDobDisplay, setEditDobDisplay] = useState('');
  const [editRole, setEditRole] = useState<'user' | 'admin'>('user');
  const [editIsActive, setEditIsActive] = useState(true);

  // Form states - Reset Password
  const [customPassword, setCustomPassword] = useState('WebGIS@2026');
  const [resetSuccessMessage, setResetSuccessMessage] = useState<string | null>(null);
  const [copiedPassword, setCopiedPassword] = useState(false);

  // Action status
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAdminUsersApi();
      setUsers(data);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách người dùng');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Filtered users list
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const q = searchQuery.toLowerCase().trim();
      const matchQuery =
        !q ||
        u.full_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.phone_number.toLowerCase().includes(q);

      const matchRole = roleFilter === 'all' || u.role === roleFilter;
      const matchStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && u.is_active) ||
        (statusFilter === 'inactive' && !u.is_active);

      return matchQuery && matchRole && matchStatus;
    });
  }, [users, searchQuery, roleFilter, statusFilter]);

  // Handle Add User
  const handleOpenAddModal = () => {
    setNewFullName('');
    setNewPhone('');
    setNewEmail('');
    setNewDobDisplay('');
    setNewPassword('WebGIS@2026');
    setNewRole('user');
    setNewIsActive(true);
    setModalError(null);
    setShowAddModal(true);
  };

  const handleConfirmAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);

    const isoDob = formatDisplayToIsoDate(newDobDisplay);
    if (!isoDob) {
      setModalError('Ngày sinh không hợp lệ. Vui lòng nhập đúng định dạng dd/mm/yyyy (ví dụ: 08/06/2004)');
      return;
    }

    setSubmitting(true);
    try {
      const payload: AdminUserCreatePayload = {
        full_name: newFullName.trim(),
        phone_number: newPhone.trim(),
        email: newEmail.trim().toLowerCase(),
        date_of_birth: isoDob,
        password: newPassword,
        role: newRole,
        is_active: newIsActive,
      };

      await createAdminUserApi(payload);
      setShowAddModal(false);
      showToast(`Đã tạo thành công tài khoản "${payload.email}"!`);
      await loadUsers();
    } catch (err: any) {
      setModalError(err?.message || 'Lỗi khi tạo người dùng mới');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Edit User
  const handleOpenEditModal = (u: AdminUserItem) => {
    setSelectedUser(u);
    setEditFullName(u.full_name);
    setEditPhone(u.phone_number);
    setEditDobDisplay(formatIsoToDisplayDate(u.date_of_birth));
    setEditRole(u.role);
    setEditIsActive(u.is_active);
    setModalError(null);
    setShowEditModal(true);
  };

  const handleConfirmEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    setModalError(null);

    const isoDob = formatDisplayToIsoDate(editDobDisplay);
    if (!isoDob) {
      setModalError('Ngày sinh không hợp lệ. Vui lòng nhập đúng định dạng dd/mm/yyyy (ví dụ: 08/06/2004)');
      return;
    }

    setSubmitting(true);
    try {
      await updateAdminUserApi(selectedUser.id, {
        full_name: editFullName.trim(),
        phone_number: editPhone.trim(),
        date_of_birth: isoDob,
        role: editRole,
        is_active: editIsActive,
      });

      setShowEditModal(false);
      showToast(`Đã cập nhật thông tin người dùng "${selectedUser.email}"`);
      await loadUsers();
    } catch (err: any) {
      setModalError(err?.message || 'Lỗi khi cập nhật người dùng');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Reset Password
  const handleOpenResetModal = (u: AdminUserItem) => {
    setSelectedUser(u);
    setCustomPassword('WebGIS@2026');
    setResetSuccessMessage(null);
    setCopiedPassword(false);
    setModalError(null);
    setShowResetModal(true);
  };

  const handleConfirmResetPassword = async () => {
    if (!selectedUser) return;
    setModalError(null);
    setSubmitting(true);

    try {
      const res = await resetUserPasswordApi(selectedUser.id, customPassword.trim());
      setResetSuccessMessage(
        `Đã đặt lại mật khẩu cho tài khoản "${res.email}" thành: ${res.new_password}`
      );
      showToast(`Đặt lại mật khẩu cho ${res.email} thành công!`);
    } catch (err: any) {
      setModalError(err?.message || 'Lỗi khi đặt lại mật khẩu');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyPassword = () => {
    if (customPassword) {
      navigator.clipboard.writeText(customPassword);
      setCopiedPassword(true);
      setTimeout(() => setCopiedPassword(false), 2500);
    }
  };

  // Handle Delete User
  const handleOpenDeleteModal = (u: AdminUserItem) => {
    setSelectedUser(u);
    setModalError(null);
    setShowDeleteModal(true);
  };

  const handleConfirmDeleteUser = async () => {
    if (!selectedUser) return;
    setSubmitting(true);
    setModalError(null);

    try {
      await deleteAdminUserApi(selectedUser.id);
      setShowDeleteModal(false);
      showToast(`Đã xóa tài khoản "${selectedUser.email}"`);
      await loadUsers();
    } catch (err: any) {
      setModalError(err?.message || 'Lỗi khi xóa người dùng');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="admin-users-view">
      {/* Toast Notification */}
      {toastMessage && <div className="admin-toast-alert">{toastMessage}</div>}

      {/* Header & Actions */}
      <div className="admin-view-header">
        <div>
          <h2>Quản lý người dùng</h2>
          <p className="admin-subtitle">Danh sách tài khoản nhân sự, phân quyền và cấp lại mật khẩu</p>
        </div>
        <button type="button" className="btn-primary" onClick={handleOpenAddModal}>
          + Thêm người dùng
        </button>
      </div>

      {/* Toolbar Filters */}
      <div className="admin-table-toolbar">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Tìm theo Tên, Email hoặc Số điện thoại..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="admin-search-input"
          />
          {searchQuery && (
            <button type="button" className="clear-search-btn" onClick={() => setSearchQuery('')}>
              ✕
            </button>
          )}
        </div>

        <div className="filter-group">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="admin-select-filter"
          >
            <option value="all">Tất cả vai trò</option>
            <option value="user">Người dùng (User)</option>
            <option value="admin">Quản trị viên (Admin)</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="admin-select-filter"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="active">Đang hoạt động</option>
            <option value="inactive">Đã khóa</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="admin-table-container">
        {loading ? (
          <div className="admin-table-empty">
            <div className="admin-spinner" />
            <span>Đang tải danh sách người dùng...</span>
          </div>
        ) : error ? (
          <div className="admin-table-empty error">
            <span>{error}</span>
            <button type="button" className="btn-secondary" onClick={loadUsers} style={{ marginTop: '8px' }}>
              Thử lại
            </button>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="admin-table-empty">
            <span>Không tìm thấy người dùng nào phù hợp với bộ lọc.</span>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Họ và tên</th>
                <th>Số điện thoại</th>
                <th>Ngày sinh</th>
                <th>Email</th>
                <th>Vai trò</th>
                <th>Trạng thái</th>
                <th>Khảo sát SEG-Y</th>
                <th style={{ textAlign: 'right' }}>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((u) => {
                const initials = u.full_name
                  ? u.full_name.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase()
                  : 'U';
                const isSelf = u.id === currentAdmin?.id;

                return (
                  <tr key={u.id} className={!u.is_active ? 'row-inactive' : ''}>
                    <td>
                      <div className="table-user-cell">
                        <div className="table-avatar">
                          {u.avatar_url ? (
                            <img src={u.avatar_url} alt={u.full_name} className="table-avatar-img" />
                          ) : (
                            <span>{initials}</span>
                          )}
                        </div>
                        <div>
                          <strong className="table-user-name">{u.full_name}</strong>
                          {isSelf && <span className="self-tag">(Bạn)</span>}
                        </div>
                      </div>
                    </td>
                    <td>{u.phone_number || '—'}</td>
                    <td>{formatIsoToDisplayDate(u.date_of_birth)}</td>
                    <td>
                      <span className="table-email">{u.email}</span>
                    </td>
                    <td>
                      <span className={`role-tag ${u.role}`}>
                        {u.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${u.is_active ? 'active' : 'inactive'}`}>
                        <i /> {u.is_active ? 'Hoạt động' : 'Đã khóa'}
                      </span>
                    </td>
                    <td>
                      <span className="badge-files">{u.segy_files_count} files</span>
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="btn-action-reset"
                          onClick={() => handleOpenResetModal(u)}
                          title="Đặt lại mật khẩu"
                        >
                          🔑 Reset mật khẩu
                        </button>
                        <button
                          type="button"
                          className="btn-action-edit"
                          onClick={() => handleOpenEditModal(u)}
                          title="Chỉnh sửa thông tin"
                        >
                          ✏️ Sửa
                        </button>
                        <button
                          type="button"
                          className="btn-action-delete"
                          onClick={() => handleOpenDeleteModal(u)}
                          disabled={isSelf}
                          title={isSelf ? 'Không thể xóa tài khoản của chính mình' : 'Xóa tài khoản'}
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ── MODAL 1: THÊM NGƯỜI DÙNG MỚI ───────────────────────────────────── */}
      {showAddModal && (
        <div className="modal-backdrop">
          <div className="modal-box admin-modal">
            <h3>+ Thêm người dùng mới</h3>
            <p>Tạo tài khoản truy cập hệ thống WebGIS cho nhân viên</p>

            {modalError && <div className="profile-alert error">{modalError}</div>}

            <form onSubmit={handleConfirmAddUser}>
              <div className="modal-form-grid">
                <div className="form-group">
                  <label className="field-label">Họ và tên *</label>
                  <input
                    type="text"
                    required
                    className="profile-input"
                    placeholder="Ví dụ: Nguyễn Văn A"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Số điện thoại *</label>
                  <input
                    type="text"
                    required
                    className="profile-input"
                    placeholder="Ví dụ: 0912345678"
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Ngày sinh (dd/mm/yyyy) *</label>
                  <input
                    type="text"
                    required
                    className="profile-input"
                    placeholder="dd/mm/yyyy (ví dụ: 15/08/1995)"
                    value={newDobDisplay}
                    onChange={(e) => setNewDobDisplay(e.target.value.replace(/[^\d/]/g, ''))}
                    maxLength={10}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Email đăng nhập *</label>
                  <input
                    type="email"
                    required
                    className="profile-input"
                    placeholder="user@company.com"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Mật khẩu khởi tạo *</label>
                  <input
                    type="text"
                    required
                    className="profile-input"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Vai trò</label>
                  <select
                    className="profile-input"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value as 'user' | 'admin')}
                  >
                    <option value="user">Người dùng (User)</option>
                    <option value="admin">Quản trị viên (Admin)</option>
                  </select>
                </div>
              </div>

              <div className="form-group" style={{ marginTop: '12px' }}>
                <label className="toggle-checkbox-label">
                  <input
                    type="checkbox"
                    checked={newIsActive}
                    onChange={(e) => setNewIsActive(e.target.checked)}
                  />
                  <span>Kích hoạt tài khoản ngay</span>
                </label>
              </div>

              <div className="modal-actions" style={{ marginTop: '20px' }}>
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setShowAddModal(false)}
                  disabled={submitting}
                >
                  Hủy bỏ
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Đang tạo...' : 'Tạo người dùng'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL 2: CHỈNH SỬA THÔNG TIN ──────────────────────────────────── */}
      {showEditModal && selectedUser && (
        <div className="modal-backdrop">
          <div className="modal-box admin-modal">
            <h3>✏️ Chỉnh sửa người dùng</h3>
            <p>Tài khoản: <strong>{selectedUser.email}</strong></p>

            {modalError && <div className="profile-alert error">{modalError}</div>}

            <form onSubmit={handleConfirmEditUser}>
              <div className="modal-form-grid">
                <div className="form-group">
                  <label className="field-label">Họ và tên *</label>
                  <input
                    type="text"
                    required
                    className="profile-input"
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Số điện thoại *</label>
                  <input
                    type="text"
                    required
                    className="profile-input"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Ngày sinh (dd/mm/yyyy)</label>
                  <input
                    type="text"
                    className="profile-input"
                    value={editDobDisplay}
                    onChange={(e) => setEditDobDisplay(e.target.value.replace(/[^\d/]/g, ''))}
                    maxLength={10}
                  />
                </div>

                <div className="form-group">
                  <label className="field-label">Vai trò</label>
                  <select
                    className="profile-input"
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value as 'user' | 'admin')}
                  >
                    <option value="user">Người dùng (User)</option>
                    <option value="admin">Quản trị viên (Admin)</option>
                  </select>
                </div>
              </div>

              <div className="form-group" style={{ marginTop: '12px' }}>
                <label className="toggle-checkbox-label">
                  <input
                    type="checkbox"
                    checked={editIsActive}
                    onChange={(e) => setEditIsActive(e.target.checked)}
                  />
                  <span>Tài khoản đang hoạt động (Is Active)</span>
                </label>
              </div>

              <div className="modal-actions" style={{ marginTop: '20px' }}>
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setShowEditModal(false)}
                  disabled={submitting}
                >
                  Hủy bỏ
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Đang lưu...' : 'Lưu thay đổi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL 3: RESET MẬT KHẨU (HƯỚNG 1) ──────────────────────────────── */}
      {showResetModal && selectedUser && (
        <div className="modal-backdrop">
          <div className="modal-box admin-modal">
            <h3>🔑 Đặt lại mật khẩu (Reset Password)</h3>
            <p>
              Cấp lại mật khẩu mới cho tài khoản: <strong>{selectedUser.full_name}</strong> ({selectedUser.email})
            </p>

            {modalError && <div className="profile-alert error">{modalError}</div>}
            {resetSuccessMessage && (
              <div className="profile-alert success" style={{ wordBreak: 'break-all' }}>
                {resetSuccessMessage}
              </div>
            )}

            {!resetSuccessMessage ? (
              <div>
                <div className="form-group">
                  <label className="field-label">Mật khẩu mới / Mật khẩu tạm thời</label>
                  <div className="input-copy-group">
                    <input
                      type="text"
                      className="profile-input"
                      value={customPassword}
                      onChange={(e) => setCustomPassword(e.target.value)}
                      placeholder="Nhập mật khẩu mới (hoặc WebGIS@2026)"
                    />
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => setCustomPassword(`WebGIS@${new Date().getFullYear()}`)}
                      title="Sinh mật khẩu tạm thời"
                    >
                      🎲 Tự sinh
                    </button>
                  </div>
                  <small className="field-hint">Mật khẩu tạm thời mặc định: <code>WebGIS@2026</code></small>
                </div>

                <div className="modal-actions" style={{ marginTop: '24px' }}>
                  <button
                    type="button"
                    className="btn-cancel"
                    onClick={() => setShowResetModal(false)}
                    disabled={submitting}
                  >
                    Hủy bỏ
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={handleConfirmResetPassword}
                    disabled={submitting || !customPassword.trim()}
                  >
                    {submitting ? 'Đang đặt lại...' : 'Xác nhận Đặt lại Mật khẩu'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="reset-success-actions">
                <button
                  type="button"
                  className="btn-copy-full"
                  onClick={handleCopyPassword}
                >
                  {copiedPassword ? '✓ Đã sao chép mật khẩu!' : '📋 Sao chép mật khẩu mới'}
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setShowResetModal(false)}
                >
                  Đóng
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL 4: XÁC NHẬN XÓA TÀI KHOẢN ───────────────────────────────── */}
      {showDeleteModal && selectedUser && (
        <div className="modal-backdrop">
          <div className="modal-box">
            <h3>Xác nhận xóa tài khoản</h3>
            <p>
              Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản của <strong>{selectedUser.full_name}</strong> (<code>{selectedUser.email}</code>)?
            </p>
            <p style={{ color: '#dc2626', fontSize: '13px' }}>
              ⚠️ Hành động này không thể hoàn tác!
            </p>

            {modalError && <div className="profile-alert error">{modalError}</div>}

            <div className="modal-actions">
              <button
                type="button"
                className="btn-cancel"
                onClick={() => setShowDeleteModal(false)}
                disabled={submitting}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn-delete-confirm"
                onClick={handleConfirmDeleteUser}
                disabled={submitting}
              >
                {submitting ? 'Đang xóa...' : 'Xóa vĩnh viễn'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
