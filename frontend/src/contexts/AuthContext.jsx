import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../services/api';

const AuthContext = createContext({});

const normaliseUser = (userData) => {
  if (!userData) return null;
  const role = String(userData.role || 'user').trim().toLowerCase();
  return { ...userData, role: role === 'citizen' ? 'user' : role };
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return normaliseUser(JSON.parse(localStorage.getItem('ai_user') || 'null')); }
    catch { localStorage.removeItem('ai_user'); return null; }
  });
  const [accessToken, setAccessToken] = useState(() => {
    const token = localStorage.getItem('ai_access_token');
    if (token) api.defaults.headers.common.Authorization = `Bearer ${token}`;
    return token;
  });

  useEffect(() => {
    if (accessToken) {
      localStorage.setItem('ai_access_token', accessToken);
      // Set Authorization header for API calls
      api.defaults.headers.common.Authorization = 'Bearer ' + accessToken;
    } else {
      localStorage.removeItem('ai_access_token');
      delete api.defaults.headers.common.Authorization;
    }
  }, [accessToken]);

  useEffect(() => {
    if (user) {
      localStorage.setItem('ai_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('ai_user');
    }
  }, [user]);

  const login = (userData, token) => {
    const normalized = normaliseUser(userData);
    if (token) {
      localStorage.setItem('ai_access_token', token);
      api.defaults.headers.common.Authorization = `Bearer ${token}`;
    }
    if (normalized) localStorage.setItem('ai_user', JSON.stringify(normalized));
    setUser(normalized);
    setAccessToken(token);
  };

  const logout = () => {
    localStorage.removeItem('ai_access_token');
    localStorage.removeItem('ai_user');
    delete api.defaults.headers.common.Authorization;
    setUser(null);
    setAccessToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, accessToken, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}




