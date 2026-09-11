import { apiClient, API_DATA_SERVING_URL } from './client';
import type { AuthResponse, LoginPayload, RegisterPayload, UpdateProfilePayload, User } from '../features/auth/types';

// Vite proxy chuyển /api → localhost:8001 nên dùng path tương đối
const AUTH_BASE = `/api/v1/auth`;

export async function registerApi(payload: RegisterPayload): Promise<AuthResponse> {
  return apiClient<AuthResponse>(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function loginApi(payload: LoginPayload): Promise<AuthResponse> {
  return apiClient<AuthResponse>(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function getMeApi(): Promise<User> {
  // skipRefresh=true: nếu chưa đăng nhập thì chỉ throw — không trigger refresh/redirect
  return apiClient<User>(`${AUTH_BASE}/me`, { method: 'GET' }, false, true);
}

export async function updateProfileApi(payload: UpdateProfilePayload): Promise<User> {
  return apiClient<User>(`${AUTH_BASE}/me`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function uploadAvatarApi(file: File): Promise<User> {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient<User>(`${AUTH_BASE}/me/avatar`, {
    method: 'POST',
    body: formData,
  });
}

/**
 * Gọi API refresh token — browser tự đính kèm refresh_token cookie.
 * Server sẽ validate và set cookie mới (access_token + refresh_token).
 */
export async function refreshApi(): Promise<AuthResponse> {
  return apiClient<AuthResponse>(`${AUTH_BASE}/refresh`, {
    method: 'POST',
  });
}

/**
 * Logout — server xóa cookie và revoke refresh token trong DB.
 */
export async function logoutApi(): Promise<void> {
  await apiClient<{ message: string }>(`${AUTH_BASE}/logout`, {
    method: 'POST',
  });
}

// Giữ backward compat cho seismicApi và các file khác import từ client
export { API_DATA_SERVING_URL };

