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

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
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
