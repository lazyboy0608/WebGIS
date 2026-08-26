import { TOKEN_KEY } from '../features/auth/AuthContext';

export const API_DATA_SERVING_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001').replace(/\/$/, '');
export const API_PROCESSING_URL = (import.meta.env.VITE_PROCESSING_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiClient<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (data.detail) {
        errorDetail = Array.isArray(data.detail)
          ? data.detail.map((err: { msg: string }) => err.msg).join(', ')
          : data.detail;
      }
    } catch {
      // Ignore JSON parse failure on error response
    }
    throw new Error(errorDetail);
  }

  // Check if response is empty or 204
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
