// Base URLs — All requests go through Vite proxy (/api → :8000 for uploads/deletes, :8001 for data-serving)
// Vite proxy ensures same origin (:5173) → cookie SameSite='Lax' works consistently
export const API_DATA_SERVING_URL = '';
export const API_PROCESSING_URL = import.meta.env.VITE_PROCESSING_API_BASE_URL ?? '';


// ─── Refresh Token Logic ──────────────────────────────────────────────────────
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(undefined);
    }
  });
  failedQueue = [];
}

async function tryRefreshToken(): Promise<boolean> {
  try {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ─── Core API Client ──────────────────────────────────────────────────────────
/**
 * skipRefresh: nếu true, khi nhận 401 sẽ throw thẳng thay vì cố refresh token.
 * Dùng cho getMeApi() trong initAuth() để tránh vòng lặp redirect vô tận.
 */
export async function apiClient<T>(
  url: string,
  options: RequestInit = {},
  _isRetry = false,
  skipRefresh = false,
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',  // Luôn đính kèm cookie (access_token + refresh_token)
    headers: {
      ...(options.headers || {}),
    },
  });

  // ── Xử lý 401: Access Token hết hạn ──────────────────────────────────────
  if (response.status === 401 && !_isRetry && !skipRefresh) {
    if (isRefreshing) {
      // Có request khác đang refresh — xếp vào queue, chờ refresh xong rồi retry
      return new Promise<T>((resolve, reject) => {
        failedQueue.push({
          resolve: () => resolve(apiClient<T>(url, options, true)),
          reject,
        });
      });
    }

    isRefreshing = true;
    const refreshed = await tryRefreshToken();
    isRefreshing = false;

    if (refreshed) {
      // Refresh thành công → retry tất cả request trong queue + request hiện tại
      processQueue(null);
      return apiClient<T>(url, options, true);
    } else {
      // Refresh thất bại → session hết hạn, redirect về /login
      processQueue(new Error('Session expired'));
      window.location.href = '/login';
      throw new Error('Session expired. Vui lòng đăng nhập lại.');
    }
  }

  // ── Xử lý lỗi HTTP khác ───────────────────────────────────────────────────
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
