import React from 'react';
import { AppBar, Toolbar, Box, Button, Container, Typography, Divider, IconButton, useTheme, Menu, MenuItem } from '@mui/material';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { useTranslation } from 'react-i18next';
import LanguageIcon from '@mui/icons-material/Language';

const Navbar = ({ showLogo, toggleTheme, currentMode }) => {
    const theme = useTheme();
    const { t, i18n } = useTranslation();
    const [anchorEl, setAnchorEl] = React.useState(null);

    const navItems = [
        { text: t('home'), href: '/' },
        { text: t('doiSearch'), href: '/doi-search' }
    ];

    const isLight = currentMode === 'light';
    const logoSrc = isLight ? "/logos/logo_plataforma.png" : "/logos/logo_plataforma_branca.png";
    const ibictLogoSrc = isLight ? "/logos/logo-ibict.png" : "/logos/logo-ibict-pb.png";
    const textColor = isLight ? theme.palette.text.primary : theme.palette.text.primary;

    const handleLanguageMenu = (event) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const changeLanguage = (lng) => {
        i18n.changeLanguage(lng);
        handleClose();
    };


    return (
        <AppBar position="sticky" elevation={0} color="transparent">
        <Container maxWidth="xl">
        <Toolbar disableGutters sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>

        <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <Box sx={{
            display: 'flex', alignItems: 'center', opacity: showLogo ? 1 : 0,
            width: showLogo ? 'auto' : '0%', transition: 'width 0.4s ease, opacity 0.2s ease',
            overflow: 'hidden', whiteSpace: 'nowrap',
        }}>
        <img src={logoSrc} alt="Logo da Plataforma de Altmetria" style={{ height: '40px', marginRight: '8px' }} />
        <Typography variant="h6" component="div" sx={{ color: textColor, fontWeight: 'bold' }}>
        {t('platformTitleNavbar')}
        </Typography>
        </Box>

        <Divider orientation="vertical" flexItem sx={{
            height: '32px', opacity: showLogo ? 1 : 0,
            mx: showLogo ? 2 : 0, transition: 'opacity 0.4s ease, margin 0.4s ease',
        }} />

        <Box sx={{ display: 'flex', marginLeft: showLogo ? 0 : '-17.5px', transition: 'margin 0.4s ease' }}>
        <a href="https://www.gov.br/ibict/pt-br" target="_blank" rel="noopener noreferrer">
        <img src={ibictLogoSrc} alt="Logo do Ibict" style={{ maxWidth: '120px', verticalAlign: 'middle' }} />
        </a>
        </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center' }}>
        {navItems.map((item) => (
            <Button key={item.text} component="a" href={item.href} sx={{
                fontWeight: 'bold', color: textColor,
                '&:hover': { backgroundColor: 'action.hover' },
            }}>
            {item.text}
            </Button>
        ))}

        <IconButton
        sx={{ ml: 1 }}
        onClick={handleLanguageMenu}
        color="inherit"
        >
        <LanguageIcon sx={{ color: 'text.primary' }} />
        </IconButton>
        <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        >
        <MenuItem onClick={() => changeLanguage('pt')}>Português</MenuItem>
        <MenuItem onClick={() => changeLanguage('en')}>English</MenuItem>
        <MenuItem onClick={() => changeLanguage('es')}>Español</MenuItem>
        </Menu>

        <IconButton sx={{ ml: 1 }} onClick={toggleTheme} color="inherit">
        {currentMode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon sx={{ color: 'text.primary' }} />}
        </IconButton>
        </Box>
        </Toolbar>
        </Container>
        </AppBar>
    );
};

export default Navbar;
