import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Box, Button, Container, Paper, TextField, Typography, Alert } from '@mui/material';
import api from '../services/api';
import { useTranslation } from 'react-i18next';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const response = await api.post('/auth/forgot-password', { email });
      setMessage({ severity: 'success', text: response.data.message });
      setTimeout(() => navigate('/auth/reset-password'), 1800);
    } catch (error) {
      setMessage({ severity: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  const { t } = useTranslation();
  return (
    <Container maxWidth="sm" sx={{ mt: 12 }}>
      <Paper sx={{ p: 4, borderRadius: 4, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.14)' }}>
        <Typography variant="h4" sx={{ mb: 2 }}>
          {t('forgotPassword')}
        </Typography>
        <Typography sx={{ mb: 3, color: 'grey.400' }}>
          {t('email')} {"-"} {t('forgotPassword')}
        </Typography>
        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'grid', gap: 2 }}>
          <TextField label={t('email')} type="email" required variant="filled" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button type="submit" variant="contained" size="large" disabled={loading}>
            {t('sendReset')}
          </Button>
          {message && <Alert severity={message.severity}>{message.text}</Alert>}
        </Box>
        <Box sx={{ mt: 2 }}>
          <Link to="/" style={{ color: '#00d4ff' }}>
            {t('backToHome')}
          </Link>
        </Box>
      </Paper>
    </Container>
  );
}
