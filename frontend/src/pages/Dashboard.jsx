import React, { useState, useEffect, useMemo, memo, useRef } from 'react';
import { Container, Typography, CircularProgress, Box, Grid, Paper, useTheme, keyframes } from '@mui/material';
import DataChart from '../components/shared/DataChart';
import DataTable from '../components/shared/DataTable';
import DataCard from '../components/shared/DataCard';
import FilterControls from '../components/shared/FilterControls';
import ExportModal from '../components/shared/ExportModal';
import { getFieldsAndEvents, getAllSources, getAvailableYears, getEventsBySource, getYearlyEventsForSource } from '../api/services';
import { useTranslation, Trans } from 'react-i18next';

import ShowChartIcon from '@mui/icons-material/ShowChart';
import SourceIcon from '@mui/icons-material/Source';
import DateRangeIcon from '@mui/icons-material/DateRange';


const fadeIn = keyframes`
from {
    opacity: 0;
    transform: translateY(20px);
}
to {
    opacity: 1;
    transform: translateY(0);
}
`;

const LoadingOverlay = () => {
    const theme = useTheme();
    return (
        <Box
        sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            backgroundColor: theme.palette.mode === 'light' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.5)',
            borderRadius: '12px',
            zIndex: 10
        }}
        >
        <CircularProgress />
        </Box>
    );
};


const Dashboard = ({ logoRef }) => {
    const theme = useTheme();
    const { t } = useTranslation();

    // --- LÓGICA DE ANIMAÇÃO REMOVIDA DAQUI ---

    const [chartKey, setChartKey] = useState(0);

    useEffect(() => {
        const timer = setTimeout(() => {
            setChartKey(prevKey => prevKey + 1);
            window.dispatchEvent(new Event('resize'));
        }, 500);

        return () => clearTimeout(timer);
    }, [theme.palette.mode]);

    const [sources, setSources] = useState([]);
    const [availableYears, setAvailableYears] = useState([]);

    const [yearFilter, setYearFilter] = useState({ start: null, end: null });
    const [selectedSources, setSelectedSources] = useState([]);

    const [mentionsByField, setMentionsByField] = useState([]);
    const [mentionsBySource, setMentionsBySource] = useState([]);
    const [trendData, setTrendData] = useState([]);

    const [loading, setLoading] = useState(true);
    const [isInitialLoad, setIsInitialLoad] = useState(true);

    const [isExportModalOpen, setExportModalOpen] = useState(false);

    const trendChartRef = useRef(null);
    const fieldChartRef = useRef(null);
    const sourceChartRef = useRef(null);

    useEffect(() => {
        const fetchAllData = async (filters) => {
            setLoading(true);

            let currentSources = sources;
            let currentYears = availableYears;

            if (isInitialLoad) {
                const [sourcesData, yearsListData] = await Promise.all([getAllSources(), getAvailableYears()]);
                setSources(sourcesData);
                setAvailableYears(yearsListData);
                currentSources = sourcesData;
                currentYears = yearsListData;
            }

            const fieldPromise = getFieldsAndEvents(filters.yearFilter.start, filters.yearFilter.end, filters.selectedSources);
            const sourcePromise = getEventsBySource(filters.yearFilter.start, filters.yearFilter.end, filters.selectedSources);

            const sourcesForTrend = filters.selectedSources.length > 0 ? filters.selectedSources : currentSources;
            const sourceTrendPromises = sourcesForTrend.map(source => getYearlyEventsForSource(source));

            const trendPromise = Promise.all(sourceTrendPromises).then(results => {
                const yearlyTotals = {};
                (currentYears || []).forEach(year => {
                    yearlyTotals[year] = { year, total_events: 0 };
                    (sourcesForTrend || []).forEach(source => { yearlyTotals[year][source] = 0; });
                });
                results.forEach((sourceData, index) => {
                    const sourceName = sourcesForTrend[index];
                    sourceData.forEach(item => { if (yearlyTotals[item.year]) { yearlyTotals[item.year][sourceName] = item.events; } });
                });
                Object.values(yearlyTotals).forEach(yearData => {
                    let total = 0;
                    sourcesForTrend.forEach(sourceName => { total += yearData[sourceName] || 0; });
                    yearData.total_events = total;
                });
                let finalData = Object.values(yearlyTotals).sort((a, b) => a.year - b.year);
                const start = filters.yearFilter.start ?? -Infinity;
                const end = filters.yearFilter.end ?? Infinity;
                return finalData.filter(item => item.year >= start && item.year <= end);
            });

            const [fieldData, sourceData, trendResultData] = await Promise.all([fieldPromise, sourcePromise, trendPromise]);

            setMentionsByField(fieldData);
            setMentionsBySource(sourceData);
            setTrendData(trendResultData);
            setLoading(false);
            if(isInitialLoad) setIsInitialLoad(false);
        };

            const handler = setTimeout(() => {
                fetchAllData({ yearFilter, selectedSources });
            }, isInitialLoad ? 0 : 500);

            return () => {
                clearTimeout(handler);
            };
    }, [yearFilter, selectedSources, isInitialLoad, sources, availableYears]);


    const { totalMentions, period, sourcesCount } = useMemo(() => {
        const total = trendData.reduce((acc, item) => acc + item.total_events, 0);
        const sYear = yearFilter.start || (availableYears.length > 0 ? availableYears[0] : '');
        const eYear = yearFilter.end || (availableYears.length > 0 ? availableYears[availableYears.length - 1] : '');
        return {
            totalMentions: total,
            period: sYear && eYear ? `${sYear} - ${eYear}` : 'Todos os anos',
            sourcesCount: selectedSources.length || sources.length,
        };
    }, [trendData, yearFilter, availableYears, sources, selectedSources]);

    const handleClearFilters = () => {
        setYearFilter({ start: null, end: null });
        setSelectedSources([]);
    };

    const trendTableColumns = useMemo(() => {
        const columns = [{ key: 'year', header: t('year') }];
        const activeSources = selectedSources.length > 0 ? selectedSources : sources;
        activeSources.forEach(source => columns.push({ key: source, header: source }));
        columns.push({ key: 'total_events', header: t('totalMentionsHeader') });
        return columns;
    }, [selectedSources, sources, t]);

    const handleOpenExportModal = () => setExportModalOpen(true);
    const handleCloseExportModal = () => setExportModalOpen(false);


    const ContentSection = ({ card, title, text, cardSide = 'left' }) => {
        const TextBlock = (
            <Grid item xs={12} md={5} key="text">
            <Box sx={{ textAlign: { xs: 'center', md: 'left' } }}>
            <Typography variant="h4" component="h3" color="text.primary" gutterBottom sx={{ fontWeight: 'bold' }}>
            {title}
            </Typography>
            <Typography variant="body1" color="text.secondary">{text}</Typography>
            </Box>
            </Grid>
        );

        const CardBlock = (
            <Grid item xs={12} md={5} key="card" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {card}
            </Grid>
        );

        return (
            // --- PROPS DE ANIMAÇÃO REMOVIDAS DAQUI ---
            <Grid container spacing={4} alignItems="center" justifyContent="center" sx={{ py: 4 }}>
            {cardSide === 'left' ? [CardBlock, TextBlock] : [TextBlock, CardBlock]}
            </Grid>
        );
    };

    if (isInitialLoad) {
        return <Box sx={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh'}}><CircularProgress /></Box>;
    }

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* --- ANIMAÇÃO REMOVIDA DAQUI --- */}
        <Box ref={logoRef} sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', my: 4 }}>
        <img src={theme.palette.mode === 'light' ? "/logos/logo_plataforma.png" : "/logos/logo_plataforma_branca.png"} alt="Logo da Plataforma de Altmetria" style={{ height: '120px', marginRight: '24px' }} />
        <Typography variant="h3" component="h1" color="text.primary" sx={{ fontWeight: 'bold' }}>
        <Trans i18nKey="platformTitle" components={{ br: <br /> }} />
        </Typography>
        </Box>

        {/* --- ANIMAÇÃO REMOVIDA DAQUI --- */}
        <Box>
        <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 6, maxWidth: '800px', mx: 'auto' }}>
        {t('platformSubtitle')}
        </Typography>
        </Box>

        <Box sx={{ maxWidth: '1200px', width: '100%', mx: 'auto' }}>
        <Box display="flex" flexDirection="column" sx={{ gap: theme.spacing(3) }}>
        {/* --- PROPS DE ANIMAÇÃO REMOVIDAS DAS CHAMADAS ABAIXO --- */}
        <ContentSection
        card={<DataCard title={t('totalMentions')} value={totalMentions.toLocaleString('pt-BR')} icon={<ShowChartIcon />} color={theme.palette.primary.main} />}
        title={t('generalOverview')}
        text={<Trans i18nKey="generalOverviewText" components={{ br: <br /> }} />}
        cardSide="right"
        />
        <ContentSection
        card={<DataCard title={t('analyzedSources')} value={sourcesCount} icon={<SourceIcon />} color={theme.palette.secondary.main} />}
        title={t('whereVoicesComeFrom')}
        text={<Trans i18nKey="whereVoicesComeFromText" components={{ br: <br /> }} />}
        cardSide="left"
        />
        <ContentSection
        card={<DataCard title={t('periodUnderAnalysis')} value={period} icon={<DateRangeIcon />} color={theme.palette.accent.main} />}
        title={t('journeyThroughTime')}
        text={<Trans i18nKey="journeyThroughTimeText" components={{ br: <br /> }} />}
        cardSide="right"
        />

        <FilterControls
        availableYears={availableYears}
        yearFilter={yearFilter}
        setYearFilter={setYearFilter}
        sources={sources}
        selectedSources={selectedSources}
        setSelectedSources={setSelectedSources}
        handleClearFilters={handleClearFilters}
        handleOpenExportModal={handleOpenExportModal}
        />

        <Paper ref={trendChartRef} sx={{ p: 3, position: 'relative', minHeight: '400px' }}>
        {loading && <LoadingOverlay />}
        <Box sx={{ transition: 'opacity 0.2s', opacity: loading ? 0.5 : 1 }}>
        <Typography variant="h6" color="text.primary" gutterBottom>{t('mentionsEvolutionByYear')}</Typography>
        <DataChart key={chartKey} data={trendData} xKey="year" yKey="total_events" />
        <DataTable data={trendData} columns={trendTableColumns} />
        </Box>
        </Paper>

        <Paper ref={fieldChartRef} sx={{ p: 3, position: 'relative', minHeight: '400px' }}>
        {loading && <LoadingOverlay />}
        <Box sx={{ transition: 'opacity 0.2s', opacity: loading ? 0.5 : 1 }}>
        <Typography variant="h6" color="text.primary" gutterBottom>{t('totalMentionsByArea')}</Typography>
        <DataChart key={chartKey} data={mentionsByField} xKey="field" yKey="events" />
        <DataTable
        data={mentionsByField}
        columns={[
            { key: 'field', header: t('area'), width: '85%' },
            { key: 'events', header: t('mentions'), align: 'right' }
        ]}
        />
        </Box>
        </Paper>

        <Paper ref={sourceChartRef} sx={{ p: 3, position: 'relative', minHeight: '400px' }}>
        {loading && <LoadingOverlay />}
        <Box sx={{ transition: 'opacity 0.2s', opacity: loading ? 0.5 : 1 }}>
        <Typography variant="h6" color="text.primary" gutterBottom>{t('totalMentionsByBase')}</Typography>
        <DataChart key={chartKey} data={mentionsBySource} xKey="source" yKey="events" />
        <DataTable
        data={mentionsBySource}
        columns={[
            { key: 'source', header: t('base'), width: '85%' },
            { key: 'events', header: t('mentions'), align: 'right' }
        ]}
        />
        </Box>
        </Paper>
        </Box>
        </Box>

        <ExportModal
        open={isExportModalOpen}
        handleClose={handleCloseExportModal}
        data={{ trendData, mentionsByField, mentionsBySource }}
        chartRefs={{ trendChartRef, fieldChartRef, sourceChartRef }}
        yearFilter={yearFilter}
        availableYears={availableYears}
        />
        </Container>
    );
};

export default memo(Dashboard);
