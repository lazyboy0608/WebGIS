import { apiClient } from './client';

export interface AdminDashboardStats {
  total_users: number;
  active_users: number;
  admin_users: number;
  cpu_usage_percent: number;
  cpu_cores: number;
  ram_usage_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  disk_usage_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  active_sessions: number;
  cache_hit_ratio: number;
  database_status: string;
  user_growth: Array<{ date: string; count: number }>;
  role_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
}

export interface AdminUserItem {
  id: number;
  full_name: string;
  phone_number: string;
  email: string;
  date_of_birth: string;
  role: 'user' | 'admin';
  is_active: boolean;
  avatar_url?: string | null;
  created_at: string;
  segy_files_count: number;
}

export interface AdminUserCreatePayload {
  full_name: string;
  phone_number: string;
  email: string;
  date_of_birth: string;
  password: string;
  role: 'user' | 'admin';
  is_active: boolean;
}

export interface AdminUserUpdatePayload {
  full_name?: string;
  phone_number?: string;
  date_of_birth?: string;
  role?: 'user' | 'admin';
  is_active?: boolean;
}

export interface ResetPasswordResponse {
  message: string;
  email: string;
  new_password: string;
}

const ADMIN_BASE = '/api/v1/admin';

export async function fetchDashboardStatsApi(): Promise<AdminDashboardStats> {
  return apiClient<AdminDashboardStats>(`${ADMIN_BASE}/dashboard-stats`, {
    method: 'GET',
  });
}

export async function fetchAdminUsersApi(params?: {
  search?: string;
  role?: string;
  is_active?: boolean;
}): Promise<AdminUserItem[]> {
  const query = new URLSearchParams();
  if (params?.search) query.append('search', params.search);
  if (params?.role) query.append('role', params.role);
  if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));

  const url = `${ADMIN_BASE}/users${query.toString() ? `?${query.toString()}` : ''}`;
  return apiClient<AdminUserItem[]>(url, {
    method: 'GET',
  });
}

export async function createAdminUserApi(payload: AdminUserCreatePayload): Promise<AdminUserItem> {
  return apiClient<AdminUserItem>(`${ADMIN_BASE}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function updateAdminUserApi(
  userId: number,
  payload: AdminUserUpdatePayload
): Promise<AdminUserItem> {
  return apiClient<AdminUserItem>(`${ADMIN_BASE}/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function resetUserPasswordApi(
  userId: number,
  newPassword?: string
): Promise<ResetPasswordResponse> {
  return apiClient<ResetPasswordResponse>(`${ADMIN_BASE}/users/${userId}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_password: newPassword || null }),
  });
}

export async function deleteAdminUserApi(userId: number): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`${ADMIN_BASE}/users/${userId}`, {
    method: 'DELETE',
  });
}
