import { io } from 'socket.io-client';
import api from './api';

const resolveSocketUrl = () => {
  const configured = (import.meta.env.VITE_SOCKET_URL || '').trim();
  if (configured) return configured;
  try { return new URL(api.defaults.baseURL, window.location.origin).origin; }
  catch { return window.location.origin; }
};

const SOCKET_URL = resolveSocketUrl();

const socket = io(SOCKET_URL, {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 800,
  reconnectionDelayMax: 10000,
  autoConnect: false,
});

socket.on('connect_error', () => {
  console.warn('Realtime socket unavailable; falling back to normal polling updates.');
});

export function connectSocket() {
  if (!socket.connected && !socket.active) socket.connect();
  return socket;
}

export function disconnectSocket() {
  if (socket.connected) socket.disconnect();
}

export default socket;
