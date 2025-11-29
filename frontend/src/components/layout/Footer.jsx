import React from 'react';
import { Box, Typography, IconButton, SvgIcon, Container, useTheme } from '@mui/material';

// ÍCONES ATUALIZADOS CONFORME SOLICITADO
const YouTubeIcon = (props) => (
  <SvgIcon {...props}>
  <path d="M10 15V9l5.2 3-5.2 3zm11.35-7.19c-.23-.86-.91-1.54-1.77-1.77C18.25 5 12 5 12 5s-6.25 0-7.81.42c-.86.23-1.54.91-1.77 1.77C2 8.75 2 12 2 12s0 3.25.42 4.81c.23.86.91 1.54 1.77 1.77C5.75 19 12 19 12 19s6.25 0 7.81-.42c.86-.23 1.54-.91 1.77-1.77C22 15.25 22 12 22 12s0-3.25-.65-4.81z" />
  </SvgIcon>
);


const FacebookIcon = (props) => (
  <SvgIcon {...props}>
  <path d="M22 12c0-5.5-4.5-10-10-10S2 6.5 2 12c0 5 3.7 9.1 8.5 9.9v-7h-2.6v-2.9h2.6V9.8c0-2.6 1.5-4 3.8-4 1.1 0 2.3.2 2.3.2v2.5h-1.3c-1.3 0-1.7.8-1.7 1.6v2h3l-.5 2.9h-2.5v7C18.3 21.1 22 17 22 12z"/>
  </SvgIcon>
);

const TwitterXIcon = (props) => (
  <SvgIcon {...props}>
  <path d="M20.4 3h-3.4l-4 5.5-4-5.5H5.6l6 8-6 8h3.4l4-5.5 4 5.5h3.4l-6-8z"/>
  </SvgIcon>
);

const LinkedInIcon = (props) => (
  <SvgIcon {...props}>
  <path d="M19 0h-14c-2.8 0-5 2.2-5 5v14c0 2.8 2.2 5 5 5h14c2.8 0 5-2.2 5-5v-14c0-2.8-2.2-5-5-5zm-11 19h-3v-9h3v9zm-1.5-10.2c-1 0-1.7-.7-1.7-1.7s.7-1.8 1.7-1.8c1 0 1.7.7 1.7 1.7s-.7 1.8-1.7 1.8zm13.5 10.2h-3v-4.5c0-1.1 0-2.5-1.5-2.5s-1.7 1.2-1.7 2.4v4.6h-3v-9h2.8v1.2h.1c.4-.8 1.4-1.6 2.9-1.6 3.1 0 3.7 2 3.7 4.6v4.8z"/>
  </SvgIcon>
);


function Footer({ logoSize = 50 }) {
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  const ibictLogoSrc = isLight ? "/logos/assinatura-gov-ibict.png" : "/logos/logo-ibict-branca.png";
  const ministerioLogoSrc = isLight ? "/logos/assinatura-gov-ministerio.png" : "/logos/assinatura-gov-ministerio.png";

  const ibictLogoStyle = {
    height: '40px', // Altura reduzida
    width: 'auto',
  };

  const ministerioLogoStyle = {
    height: `${logoSize}px`,
    width: 'auto',
  };

  return (
    <Box
    component="footer"
    sx={{
      backgroundColor: 'transparent',
      py: 4,
      mt: 8,
      borderTop: '1px solid',
      borderColor: 'divider'
    }}
    >
    <Container maxWidth="xl">
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: '60px' }}>

    <Box sx={{ flex: 1, display: 'flex', justifyContent: 'flex-start' }}>
    <IconButton aria-label="YouTube" href="https://www.youtube.com/user/IBICTbr/" target="_blank" color="inherit"><YouTubeIcon /></IconButton>
    <IconButton aria-label="Facebook" href="https://www.facebook.com/IBICTbr/" target="_blank" color="inherit"><FacebookIcon /></IconButton>
    <IconButton aria-label="Twitter" href="https://twitter.com/ibictbr" target="_blank" color="inherit"><TwitterXIcon /></IconButton>
    <IconButton aria-label="LinkedIn" href="https://www.linkedin.com/company/ibict---instituto-brasileiro-de-informa-o-em-ci-ncia-e-tecnologia/mycompany/" target="_blank" color="inherit"><LinkedInIcon /></IconButton>
    </Box>

    <Box sx={{ flex: 1, textAlign: 'center' }}>
    <Typography variant="body2" color="text.secondary">
    Instituto Brasileiro de Informação em Ciência e Tecnologia (Ibict)
    <br />
    SAUS Quadra 5 - Lote 6 Bloco H - Asa Sul - CEP: 70.070-912 - Brasília - DF
    </Typography>
    </Box>

    <Box sx={{ flex: 1, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 3 }}>
    <img src={ibictLogoSrc} alt="Logo IBICT" style={ibictLogoStyle} />
    <img src={ministerioLogoSrc} alt="Logo MCTI" style={ministerioLogoStyle} />
    </Box>
    </Box>
    </Container>
    </Box>
  );
}

export default Footer;
