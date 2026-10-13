import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import IconButton from '@mui/material/IconButton';
import NotificationsIcon from '@mui/icons-material/Notifications';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

const heroBg = 'linear-gradient(135deg, #06121f 0%, #08293a 40%, #0b2f3f 100%)';
const citizenImg = '/citizen.svg';
const officialImg = '/official.svg';
const adminImg = '/admin.svg';

function RoleCard({ title, desc, img, buttonText, gradient, to }) {
  return (
    <Paper
      elevation={6}
      sx={{
        borderRadius: 3,
        p: 3,
        minHeight: 340,
        position: 'relative',
        backdropFilter: 'blur(10px)',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        overflow: 'hidden',
        transition: 'transform 300ms ease, box-shadow 300ms ease',
        '&:hover': {
          transform: 'translateY(-8px)',
          boxShadow: '0 20px 40px rgba(2,12,27,0.6)'
        }
      }}
    >
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>{title}</Typography>
          <Typography variant="body2" sx={{ color: 'grey.300', mt: 1 }}>{desc}</Typography>
          <Button component={Link} to={to} variant="contained" size="large" sx={{ mt: 3, alignSelf: 'flex-start', background: gradient }}>
            {buttonText}
          </Button>
        </Box>
        <Box sx={{ width: 160, display: { xs: 'none', sm: 'block' }, transform: 'translateY(-6px)' }}>
          <img src={img} alt="illustration" style={{ width: '100%', borderRadius: 16, boxShadow: '0 8px 24px rgba(2,12,27,0.6)' }} />
        </Box>
      </Box>
    </Paper>
  );
}

import { useTranslation } from 'react-i18next';

export default function Home() {
  const { t, i18n } = useTranslation();
  const [language, setLanguage] = useState(i18n.language || 'en');

  const setLang = (lng) => {
    i18n.changeLanguage(lng);
    localStorage.setItem('smart-civic-lang', lng);
    setLanguage(lng);
  };

  
  return (
    <Box sx={{ minHeight: '100vh', background: heroBg, color: 'white', pb: 8, position: 'relative', overflow: 'hidden' }}>
      {/* subtle animated particles / shapes */}
      <Box sx={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 0 }}>
        <Box sx={{ position: 'absolute', width: 420, height: 420, bgcolor: 'rgba(6,80,120,0.14)', filter: 'blur(60px)', borderRadius: '50%', top: -80, left: -80, animation: 'float 8s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', width: 280, height: 280, bgcolor: 'rgba(120,45,200,0.12)', filter: 'blur(48px)', borderRadius: '50%', bottom: -60, right: -60, animation: 'float 10s ease-in-out infinite reverse' }} />
        <Box sx={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 10% 10%, rgba(255,255,255,0.02), transparent 6%), radial-gradient(ellipse at 90% 90%, rgba(255,255,255,0.02), transparent 6%)' }} />
      </Box>

      <Box sx={{ maxWidth: 1200, mx: 'auto', px: 3, position: 'relative', zIndex: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ width: 56, height: 56, borderRadius: '12px', bgcolor: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 6px 18px rgba(2,12,27,0.6)' }}>
              <img src="/logo.svg" alt="gov-logo" style={{ width: 40, height: 40, borderRadius: 8 }} onError={(e)=>{ e.currentTarget.onerror=null; e.currentTarget.src='/fallback-logo.svg' }} />
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 800, fontSize: 20 }}>{t('appName')}</Typography>
              <Typography sx={{ fontSize: 12, color: 'grey.300' }}>{t('tagline')}</Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TextField
              select
              size="small"
              value={language}
              onChange={(e) => setLang(e.target.value)}
              sx={{ minWidth: 120, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 2, color: 'common.white' }}
              InputProps={{ sx: { color: 'common.white' } }}
            >
              <MenuItem value="en">English</MenuItem>
              <MenuItem value="kn">ಕನ್ನಡ</MenuItem>
            </TextField>

            <IconButton sx={{ color: 'white' }}><HelpOutlineIcon /></IconButton>
            <IconButton sx={{ color: 'white' }}><NotificationsIcon /></IconButton>
            <Box sx={{ ml: 2, px: 2, py: 1, borderRadius: 4, bgcolor: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.04)' }}>{/* theme label placeholder */}</Box>
          </Box>
        </Box>

        <Box sx={{ mt: 6, display: 'grid', gap: 2 }}>
          <Typography variant="h3" sx={{ fontWeight: 800, fontSize: { xs: 28, md: 40 } }}>{t('welcomeTitle')}</Typography>
          <Typography variant="h6" sx={{ color: 'grey.300' }}>{t('chooseRole')}</Typography>

          <Grid container spacing={3} sx={{ mt: 3 }}>
            <Grid item xs={12} md={4}>
              <RoleCard
                title={t('citizen')}
                desc={t('citizenDesc')}
                img={citizenImg}
                buttonText={t('continueCitizen')}
                gradient="linear-gradient(90deg,#00B4FF,#0066FF)"
                to="/auth/login/user"
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <RoleCard
                title={t('official')}
                desc={t('officialDesc')}
                img={officialImg}
                buttonText={t('continueOfficial')}
                gradient="linear-gradient(90deg,#00C853,#007E33)"
                to="/auth/login/official"
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <RoleCard
                title={t('admin')}
                desc={t('adminDesc')}
                img={adminImg}
                buttonText={t('continueAdmin')}
                gradient="linear-gradient(90deg,#8A2BE2,#6A00F4)"
                to="/auth/login/admin"
              />
            </Grid>
          </Grid>
        </Box>
      </Box>

      <style>{`@keyframes float { 0% { transform: translateY(0) } 50% { transform: translateY(-20px) } 100% { transform: translateY(0) } }`}</style>
    </Box>
  );
}
