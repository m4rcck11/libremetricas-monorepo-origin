import React from 'react';
import { Card, CardContent, Typography, Box, Avatar, useTheme } from '@mui/material';

const DataCard = ({ title, value, icon, color }) => {
    const theme = useTheme();
    const iconColor = theme.palette.getContrastText(color); // Calcula a melhor cor (preto ou branco)

    return (
        <Card>
        <CardContent sx={{ display: 'flex', alignItems: 'center' }}>
        <Avatar sx={{
            backgroundColor: color,
            color: iconColor,
            width: 56,
            height: 56,
            mr: 2
        }}>
        {icon}
        </Avatar>
        <Box>
        <Typography variant="h4" component="div" color="text.primary">
        {value}
        </Typography>
        <Typography color="text.secondary" variant="body2">
        {title}
        </Typography>
        </Box>
        </CardContent>
        </Card>
    );
};

DataCard.defaultProps = {
    color: '#2c3e50',
};

export default DataCard;
