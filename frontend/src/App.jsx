import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Container from '@mui/material/Container';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { useColorMode } from './contexts/ThemeContext';
import Home from './pages/Home';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import TrainingPage from './pages/TrainingPage';
import { useTheme } from '@mui/material/styles';
import { useEffect } from 'react';

function ProtectedRoute({ children, allowedRoles }) {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/auth/login/user" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/auth/:mode/:role" element={<AuthPage />} />
      <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute allowedRoles={['user', 'official', 'admin']}>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="/training" element={<ProtectedRoute allowedRoles={['admin']}><TrainingPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function TopBar() {
  const { mode, toggleColorMode } = useColorMode();
  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', py: 1 }}>
      <Tooltip title={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}>
        <IconButton onClick={toggleColorMode} color="inherit">
          {mode === 'light' ? <Brightness4Icon /> : <Brightness7Icon />}
        </IconButton>
      </Tooltip>
    </Box>
  );
}

function App() {
  const { mode } = useColorMode();
  const theme = useTheme();

  // ensure body background uses theme gradient for instant change
  useEffect(() => {
    try {
      document.body.style.background = theme.palette.custom?.gradient || theme.palette?.background?.default || '';
      document.body.style.transition = 'background 180ms linear';
      document.body.style.color = theme.palette.text?.primary || '';
    } catch (e) {}
  }, [theme, mode]);

  return (
    <AuthProvider>
      <Box sx={{ minHeight: '100vh' }}>
        <Container maxWidth="xl" sx={{ py: 2 }}>
          <TopBar />
          <AppRoutes />
        </Container>
      </Box>
    </AuthProvider>
  );
}

export default App;
