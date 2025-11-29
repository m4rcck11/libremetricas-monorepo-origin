import React, { useState, useEffect, useRef, useMemo } from 'react';
import { CssBaseline, ThemeProvider, createTheme, Box } from '@mui/material';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import DoiSearch from './pages/DoiSearch';
import Navbar from './components/layout/Navbar';
import GovBar from './components/layout/GovBar';
import Footer from './components/layout/Footer';

// TEMA CLARO (Inspirado na Logo Principal)
const getLightTheme = () => createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#5D3A9B' },
    secondary: { main: '#FDB813' },
    accent: { main: '#29ABE2' },
    background: {
      default: '#f0f2f5',
        paper: 'rgba(255, 255, 255, 0.7)',
                                        paperLighter: 'rgba(255, 255, 255, 0.9)',
    },
    text: { primary: '#1A2027', secondary: '#4A5568' },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h3: { fontWeight: 700 }, h4: { fontWeight: 700 }, h5: { fontWeight: 700 }, h6: { fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        // Usamos uma função para aceder ao tema e garantir a cor de fundo correta
        root: ({ theme }) => ({
          backgroundColor: theme.palette.background.paper, // CORREÇÃO APLICADA AQUI
          border: '1px solid rgba(0, 0, 0, 0.12)',
                              backdropFilter: 'blur(16px)',
                              boxShadow: '0 8px 24px rgba(0,0,0,0.05)',
                              borderRadius: '12px',
                              '& .recharts-surface': {
                                background: 'transparent',
                              },
        })
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: '1px solid rgba(0, 0, 0, 0.12)',
                                        backdropFilter: 'blur(16px)',
                                        boxShadow: '0 8px 24px rgba(0,0,0,0.05)',
                                        borderRadius: '12px',
                                        transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                                        '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 30px rgba(0,0,0,0.08)' }
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255, 255, 255, 0.7)',
                                        backdropFilter: 'blur(16px)',
                                        boxShadow: 'none',
                                        borderBottom: '1px solid rgba(0, 0, 0, 0.12)',
        }
      }
    },
    MuiAutocomplete: {
      styleOverrides: {
        popper: {
          border: '1px solid rgba(0, 0, 0, 0.12)',
                                        backdropFilter: 'blur(16px)',
                                        boxShadow: '0 8px 24px rgba(0,0,0,0.1)',
                                        borderRadius: '12px',
                                        backgroundColor: 'rgba(255, 255, 255, 0.75)'
        }
      }
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: 'rgba(255, 255, 255, 0.4)',
                                        borderRadius: '8px',
          },
        },
      },
    },
  }
});

// TEMA ESCURO (Inspirado na Logo Branca)
const getDarkTheme = () => createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#66FCF1' },
    secondary: { main: '#C3E93B' },
    accent: { main: '#BE93FD' },
    background: {
      default: '#12182B',
        paper: 'rgba(28, 37, 64, 0.65)',
                                       paperLighter: 'rgba(28, 37, 64, 0.8)',
    },
    text: { primary: '#FFFFFF', secondary: '#A0AEC0' }
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h3: { fontWeight: 700 }, h4: { fontWeight: 700 }, h5: { fontWeight: 700 }, h6: { fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        // Usamos uma função para aceder ao tema e garantir a cor de fundo correta
        root: ({ theme }) => ({
          backgroundColor: theme.palette.background.paper, // CORREÇÃO APLICADA AQUI
          border: '1px solid rgba(255, 255, 255, 0.15)',
                              backdropFilter: 'blur(16px)',
                              boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.2)',
                              borderRadius: '12px',
                              '& .recharts-surface': {
                                background: 'transparent',
                              },
        })
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: '1px solid rgba(255, 255, 255, 0.15)',
                                       backdropFilter: 'blur(16px)',
                                       boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.2)',
                                       borderRadius: '12px',
                                       transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                                       '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 40px 0 rgba(0, 0, 0, 0.25)' }
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(18, 24, 43, 0.7)',
                                       backdropFilter: 'blur(16px)',
                                       boxShadow: 'none',
                                       borderBottom: '1px solid rgba(255, 255, 255, 0.15)',
        }
      }
    },
    MuiAutocomplete: {
      styleOverrides: {
        popper: {
          border: '1px solid rgba(255, 255, 255, 0.15)',
                                       backdropFilter: 'blur(16px)',
                                       boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.25)',
                                       borderRadius: '12px',
                                       backgroundColor: 'rgba(28, 37, 64, 0.8)'
        }
      }
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: 'rgba(28, 37, 64, 0.4)',
                                       borderRadius: '8px',
          },
        },
      },
    },
  }
});


function App() {
  const [showLogoInNavbar, setShowLogoInNavbar] = useState(false);
  const [mode, setMode] = useState('light');
  const logoInBodyRef = useRef(null);

  const theme = useMemo(() => (mode === 'light' ? getLightTheme() : getDarkTheme()), [mode]);

  const toggleColorMode = () => {
    setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
  };

  useEffect(() => {
    const handleScroll = () => {
      if (logoInBodyRef.current) {
        const { bottom } = logoInBodyRef.current.getBoundingClientRect();
        setShowLogoInNavbar(bottom < 0);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const bodyBackground = mode === 'light'
  ? 'linear-gradient(180deg, #f0f2f5 0%, #e6e9ee 100%)'
  : theme.palette.background.default;

  return (
    <ThemeProvider theme={theme}>
    <CssBaseline />
    <Router>
    <Box sx={{
      display: 'flex', flexDirection: 'column', minHeight: '100vh',
      background: bodyBackground,
      transition: 'background 0.3s ease-in-out',
    }}>
    <GovBar />
    <Navbar showLogo={showLogoInNavbar} toggleTheme={toggleColorMode} currentMode={mode} />
    <Box component="main" sx={{ flexGrow: 1 }}>
    <Routes>
    <Route path="/" element={<Dashboard logoRef={logoInBodyRef} />} />
    <Route path="/doi-search" element={<DoiSearch />} />
    </Routes>
    </Box>
    <Footer logoSize={60} />
    </Box>
    </Router>
    </ThemeProvider>
  );
}

export default App;
