import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useTheme } from '@mui/material/styles';
import { useTranslation } from 'react-i18next';

// Componente para renderizar o rótulo do eixo com todos os ajustes finais
const CustomizedAxisTick = (props) => {
    const { x, y, payload } = props;
    const valueAsString = String(payload.value);
    const words = valueAsString.split(' ');
    const maxCharsPerLine = 14;

    // Lógica para rótulos de linha única
    if (words.length === 1 || valueAsString.length <= maxCharsPerLine) {
        return (
            <g transform={`translate(${x},${y})`}>
            <text
            x={0}
            y={0}
            dx={-15}
            dy={20} // Posição vertical para linha única
            textAnchor="end"
            fill={useTheme().palette.text.secondary}
            transform="rotate(-45)"
            style={{ fontSize: '12px', userSelect: 'none' }}
            >
            {valueAsString}
            </text>
            </g>
        );
    }

    const lines = words.reduce((result, word) => {
        const lastLine = result.length > 0 ? result[result.length - 1] : null;

        if (!lastLine || (lastLine.length + word.length + 1) > maxCharsPerLine) {
            result.push(word);
        } else {
            result[result.length - 1] = `${lastLine} ${word}`;
        }
        return result;
    }, []);

    // Lógica para rótulos de múltiplas linhas
    return (
        <g transform={`translate(${x},${y})`}>
        <text
        x={0}
        y={0}
        dx={-15}
        dy={35} // Posição vertical AUMENTADA para múltiplas linhas
        textAnchor="end"
        fill={useTheme().palette.text.secondary}
        transform="rotate(-45)"
        style={{ fontSize: '12px', userSelect: 'none' }}
        >
        {lines.map((line, i) => (
            <tspan x={0} dy={i === 0 ? 0 : '1.4em'} key={i}>
            {line}
            </tspan>
        ))}
        </text>
        </g>
    );
};


const DataChart = ({ data, xKey, yKey }) => {
    const theme = useTheme();
    const { t } = useTranslation();

    const textColor = theme.palette.text.secondary;
    const gridColor = theme.palette.divider;
    const tooltipBg = theme.palette.background.paper;

    const gradient = (
        <defs>
        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.9}/>
        <stop offset="95%" stopColor={theme.palette.accent.main} stopOpacity={0.7}/>
        </linearGradient>
        </defs>
    );

    return (
        <ResponsiveContainer width="100%" height={400}>
        <BarChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 100 }}
        >
        {gradient}
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
        <XAxis
        dataKey={xKey}
        interval={0}
        tick={<CustomizedAxisTick />}
        stroke={textColor}
        />
        <YAxis tick={{ fill: textColor }} stroke={textColor} />
        <Tooltip
        cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
        contentStyle={{
            background: tooltipBg,
            border: `1px solid ${gridColor}`,
            borderRadius: '8px',
            backdropFilter: 'blur(5px)',
        }}
        />
        <Legend verticalAlign="top" height={36} wrapperStyle={{ color: textColor }} />
        <Bar dataKey={yKey} fill="url(#chartGradient)" name={t('mentions')} radius={[4, 4, 0, 0]} />
        </BarChart>
        </ResponsiveContainer>
    );
};

export default DataChart;
