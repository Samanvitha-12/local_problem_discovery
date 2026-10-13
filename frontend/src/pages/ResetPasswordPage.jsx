import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Box, Button, Container, Paper, TextField, Typography, Alert } from '@mui/material';
import api from '../services/api';

export default function ResetPasswordPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    if (password !== confirmPassword) {
      setMessage({ severity: 'error', text: 'Passwords must match' });
      setLoading(false);
      return;
    }
    try {
      const response = await api.post('/auth/reset-password', { email: email.trim(), password });
      setMessage({ severity: 'success', text: response.data.message });
      setTimeout(() => navigate('/auth/login/user'), 1500);
    } catch (error) {
      const serverMessage = error?.response?.data?.message;
      const text = serverMessage || (error?.response?.status === 404
        ? 'The password reset endpoint was not found. Restart the backend and check the /api proxy.'
        : error?.code === 'ERR_NETWORK'
          ? 'Could not reach the server. Check that the backend is running and try again.'
          : error?.message || 'Password reset failed. Please try again.');
      setMessage({ severity: 'error', text });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 12 }}>
      <Paper sx={{ p: 4, borderRadius: 4, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)' }}>
        <Typography variant="h4" sx={{ mb: 2 }}>
          Reset Password
        </Typography>
        <Typography sx={{ mb: 3, color: 'grey.400' }}>
          Enter the same email address and choose a new secure password.
        </Typography>
        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'grid', gap: 2 }}>
          <TextField label="Email" type="email" required variant="filled" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField label="New Password" type="password" required variant="filled" value={password} onChange={(e) => setPassword(e.target.value)} />
          <TextField label="Confirm Password" type="password" required variant="filled" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          <Button type="submit" variant="contained" size="large" disabled={loading}>
            Reset Password
          </Button>
          {message && <Alert severity={message.severity}>{message.text}</Alert>}
        </Box>
        <Box sx={{ mt: 2 }}>
          <Link to="/" style={{ color: '#00d4ff' }}>
            Back to Home
          </Link>
        </Box>
      </Paper>
    </Container>
  );
}
