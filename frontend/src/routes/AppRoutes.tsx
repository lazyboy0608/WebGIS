import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';
import { LoginPage } from '../features/auth/LoginPage';
import { RegisterPage } from '../features/auth/RegisterPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { ProfilePage } from '../features/profile/ProfilePage';
import { AdminPage } from '../features/admin/AdminPage';
import { ProtectedRoute } from './ProtectedRoute';
import { AdminRoute } from './AdminRoute';
import { UserRoute } from './UserRoute';

export const AppRoutes: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();

  // Khi đang kiểm tra session lần đầu (initAuth), hiển thị màn hình chờ
  if (isLoading) {
    return (
      <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', background: '#0d131f', color: '#fff' }}>
        <span>Đang tải...</span>
      </div>
    );
  }

  // Trang chủ mặc định theo vai trò: Admin -> /admin, User -> /dashboard
  const homeRedirect = user?.role === 'admin' ? '/admin' : '/dashboard';

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to={homeRedirect} replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to={homeRedirect} replace /> : <RegisterPage />}
      />
      <Route
        path="/dashboard"
        element={
          <UserRoute>
            <DashboardPage />
          </UserRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <AdminPage />
          </AdminRoute>
        }
      />
      <Route
        path="/admin/*"
        element={
          <AdminRoute>
            <AdminPage />
          </AdminRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={<Navigate to={isAuthenticated ? homeRedirect : '/login'} replace />}
      />
      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  );
};

