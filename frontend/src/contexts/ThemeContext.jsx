import React, { createContext, useContext, useMemo, useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const ColorModeContext = createContext({ toggleColorMode: () => {} });
const STORAGE_KEY = 'smart-civic-theme';

export function ColorModeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved || 'dark';
    } catch (e) {
      return 'dark';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, mode);
      document.documentElement.style.colorScheme = mode;
    } catch (e) {}
  }, [mode]);

  const colorMode = useMemo(
    () => ({
      toggleColorMode: (value) => {
        setMode((prevMode) => {
          if (typeof value === 'string') return value;
          return prevMode === 'light' ? 'dark' : 'light';
        });
      },
      mode,
    }),
    [mode]
  );

  const theme = useMemo(() => {
    const isLight = mode === 'light';
    return createTheme({
      palette: {
        mode,
        primary: { main: '#0066FF' },
        secondary: { main: '#00C853' },
        background: {
          default: isLight ? '#F8FAFC' : '#0F172A',
          paper: isLight ? '#FFFFFF' : '#111827',
        },
        custom: {
          gradient: isLight
            ? 'linear-gradient(180deg, #F8FAFC 0%, #E2E8F0 100%)'
            : 'linear-gradient(180deg, #0F172A 0%, #111827 50%, #1E293B 100%)',
        },
      },
      typography: {
        fontFamily: "Poppins, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      },
      components: {
        MuiButton: {
          defaultProps: { disableRipple: false },
        },
      },
    });
  }, [mode]);

  return (
    <ColorModeContext.Provider value={{ ...colorMode, theme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export function useColorMode() {
  return useContext(ColorModeContext);
}
