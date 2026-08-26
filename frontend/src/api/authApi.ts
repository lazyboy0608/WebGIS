import { apiClient, API_DATA_SERVING_URL } from './client';
import type { AuthResponse, LoginPayload, RegisterPayload, User } from '../features/auth/types';

const AUTH_BASE = `${API_DATA_SERVING_URL}/api/v1/auth`;

export async function registerApi(payload: RegisterPayload): Promise<AuthResponse> {
  return apiClient<AuthResponse>(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export async function loginApi(payload: LoginPayload): Promise<AuthResponse> {
  return apiClient<AuthResponse>(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export async function getMeApi(token?: string): Promise<User> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return apiClient<User>(`${AUTH_BASE}/me`, {
    method: 'GET',
    headers,
  });
}
