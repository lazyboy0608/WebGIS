export interface User {
  id: number;
  full_name: string;
  phone_number: string;
  email: string;
  date_of_birth: string;
  role: 'user' | 'admin';
  is_active: boolean;
  created_at: string;
}

/**
 * Response body khi login/register — token không còn trong body,
 * mà được đặt vào HTTPOnly Cookie bởi server.
 */
export interface AuthResponse {
  user: User;
  message: string;
}

export interface RegisterPayload {
  full_name: string;
  phone_number: string;
  email: string;
  date_of_birth: string;
  password: string;
  confirm_password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
