import React from 'react';
import { Modal, Box, Typography, Button, Grid, RadioGroup, FormControlLabel, Radio, FormControl, FormLabel, Divider } from '@mui/material';
import { saveAs } from 'file-saver';
import Papa from 'papaparse';
import { toPng } from 'html-to-image';
import { useTranslation } from 'react-i18next';
import { getEventsFieldsRaw } from '../../api/services';
import apiClient from '../../api/axiosConfig';

const style = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: 400,
    bgcolor: 'background.paperLighter',
    boxShadow: 24,
    p: 4,
    borderRadius: '12px',
    backdropFilter: 'blur(16px)',
    border: '1px solid',
    borderColor: 'divider',
};

const transformRawDataForCsv = (rawData) => {
    if (!rawData) return [];
    const keys = Object.keys(rawData);
    if (keys.length === 0) return [];

    // Assumindo que todas as colunas (arrays) têm o mesmo comprimento
    const numRows = rawData[keys[0]].length;
    const result = [];

    for (let i = 0; i < numRows; i++) {
        const row = {};
        for (const key of keys) {
            // Verifica se a chave existe e se o índice é válido
            if (rawData[key] && rawData[key].length > i) {
                row[key] = rawData[key][i];
            } else {
                row[key] = null; // Ou valor padrão
            }
        }
        result.push(row);
    }
    return result;
};


const ExportModal = ({ open, handleClose, data, chartRefs, yearFilter, availableYears }) => {
    const { t } = useTranslation();
    const [exportType, setExportType] = React.useState('table');
    const [selectedData, setSelectedData] = React.useState('trendData');

    // --- NOVO STATE ---
    // State para controlar se a exportação de gráfico é permitida
    const [isChartExportable, setIsChartExportable] = React.useState(true);

    // --- NOVO EFFECT ---
    // Atualiza se o gráfico pode ser exportado quando a seleção de dados muda
    React.useEffect(() => {
        if (selectedData === 'allEventsFields' || selectedData === 'allEventsPeriod') {
            setIsChartExportable(false);
            setExportType('table'); // Força a seleção para "tabela"
        } else {
            setIsChartExportable(true);
        }
    }, [selectedData]);


    const handleExport = async () => {
        const { trendData, mentionsByField, mentionsBySource } = data;
        const chartRefMap = {
            trendData: chartRefs.trendChartRef,
            mentionsByField: chartRefs.fieldChartRef,
            mentionsBySource: chartRefs.sourceChartRef
        };

        // --- LÓGICA DE GRÁFICO (PNG) ---
        if (exportType === 'chart' && isChartExportable) {
            const chartRefToExport = chartRefMap[selectedData];
            if (chartRefToExport && chartRefToExport.current) {
                toPng(chartRefToExport.current, { cacheBust: true })
                .then((dataUrl) => {
                    saveAs(dataUrl, `${selectedData}.png`);
                })
                .catch((err) => {
                    console.error('oops, something went wrong!', err);
                });
            }
            handleClose();
            return;
        }

        // --- LÓGICA DE TABELA (CSV) ---
        if (exportType === 'table') {
            let dataToExport = [];
            let filename = `${selectedData}.csv`;

            if (selectedData === 'trendData') {
                dataToExport = trendData;
            } else if (selectedData === 'mentionsByField') {
                dataToExport = mentionsByField;
            } else if (selectedData === 'mentionsBySource') {
                dataToExport = mentionsBySource;

                // --- NOVOS CASOS DE EXPORTAÇÃO ---
            } else if (selectedData === 'allEventsFields') {
                try {
                    const rawData = await getEventsFieldsRaw();
                    dataToExport = transformRawDataForCsv(rawData);
                    filename = 'eventos_completos_por_area.csv';
                } catch (error) {
                    console.error("Erro ao buscar dados de eventos por área:", error);
                }

            } else if (selectedData === 'allEventsPeriod') {
                // Direct download via streaming endpoint
                const sYear = yearFilter.start || (availableYears.length > 0 ? availableYears[0] : '1900');
                const eYear = yearFilter.end || (availableYears.length > 0 ? availableYears[availableYears.length - 1] : '2100');

                const baseURL = apiClient.defaults.baseURL || '';
                const downloadUrl = `${baseURL}/all_events_data_filter_years_enriched/${sYear}/${eYear}`;

                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = `altmetrics_${sYear}_${eYear}.csv`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                handleClose();
                return;
            }

            // Gera e baixa o CSV
            const csv = Papa.unparse(dataToExport);
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            saveAs(blob, filename);
        }

        handleClose();
    };


    return (
        <Modal
        open={open}
        onClose={handleClose}
        aria-labelledby="export-modal-title"
        >
        <Box sx={style}>
        <Typography id="export-modal-title" variant="h6" component="h2">
        {t('exportData')}
        </Typography>
        <Divider sx={{ my: 2 }} />
        <Grid container spacing={3}>
        <Grid item xs={12}>
        <FormControl component="fieldset">
        <FormLabel component="legend">{t('selectData')}</FormLabel>
        <RadioGroup row value={selectedData} onChange={(e) => setSelectedData(e.target.value)}>
        <FormControlLabel value="trendData" control={<Radio />} label={t('evolution')} />
        <FormControlLabel value="mentionsByField" control={<Radio />} label={t('area')} />
        <FormControlLabel value="mentionsBySource" control={<Radio />} label={t('base')} />
        {/* --- NOVAS OPÇÕES (adicione as chaves 'eventsByAreaFull' e 'allEventsPeriod' aos seus arquivos i18n) --- */}
        <FormControlLabel value="allEventsFields" control={<Radio />} label={t('agregado')} />
        <FormControlLabel value="allEventsPeriod" control={<Radio />} label={t('bruto')} />
        </RadioGroup>
        </FormControl>
        </Grid>
        <Grid item xs={12}>
        <FormControl component="fieldset">
        <FormLabel component="legend">{t('format')}</FormLabel>
        <RadioGroup row value={exportType} onChange={(e) => setExportType(e.target.value)}>
        <FormControlLabel value="table" control={<Radio />} label={t('tableCsv')} />
        {/* --- OPÇÃO DE GRÁFICO AGORA É DESABILITÁVEL --- */}
        <FormControlLabel
        value="chart"
        control={<Radio />}
        label={t('chartPng')}
        disabled={!isChartExportable}
        />
        </RadioGroup>
        </FormControl>
        </Grid>
        <Grid item xs={12} sx={{ display: 'flex', justifyContent: '', gap: 1 }}>
        <Button onClick={handleClose}>{t('cancel')}</Button>
        <Button variant="contained" onClick={handleExport}>{t('export')}</Button>
        </Grid>
        </Grid>
        </Box>
        </Modal>
    );
};

export default ExportModal;
