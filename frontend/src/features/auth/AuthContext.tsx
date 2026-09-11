import React, { createContext, useContext, useEffect, useState } from 'react';
import { getMeApi, loginApi, logoutApi, registerApi } from './authService';
import type { LoginPayload, RegisterPayload, User } from './types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (updatedUser: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Khi app khởi động, thử lấy thông tin user bằng cookie hiện có
  // Nếu cookie hết hạn hoặc không có → user = null → redirect /login
  useEffect(() => {
    async function initAuth() {
      try {
        const userData = await getMeApi();
        setUser(userData);
      } catch {
        // Cookie không có hoặc không hợp lệ — user chưa đăng nhập
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    initAuth();
  }, []);

  const login = async (payload: LoginPayload) => {
    const res = await loginApi(payload);
    // Server đã set cookie — chỉ cần lưu user vào state
    setUser(res.user);
  };

  const register = async (payload: RegisterPayload) => {
    const res = await registerApi(payload);
    setUser(res.user);
  };

  const updateUser = (updatedUser: User) => {
    setUser(updatedUser);
  };

  const logout = async () => {
    try {
      // Gọi API để server xóa cookie và revoke refresh token trong DB
      await logoutApi();
    } catch {
      // Dù API có lỗi vẫn clear state phía client
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
