import React from 'react';
import { Autocomplete, TextField, Button, Paper, Typography, Box, IconButton } from '@mui/material';
import ReplayIcon from '@mui/icons-material/Replay';
import { useTranslation } from 'react-i18next';

const FilterControls = ({
    availableYears,
    yearFilter,
    setYearFilter,
    sources,
    selectedSources,
    setSelectedSources,
    handleClearFilters,
    handleOpenExportModal
}) => {
    const { t } = useTranslation();
    const endYearOptions = yearFilter.start ? availableYears.filter(year => year >= yearFilter.start) : availableYears;

    const isFilterApplied = yearFilter.start || yearFilter.end || selectedSources.length > 0;

    return (
        <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="h6" component="div" color="text.primary" sx={{ mr: 1, flexShrink: 0 }}>
        {t('filters')}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1, flexWrap: 'wrap' }}>
        <Autocomplete
        options={availableYears}
        getOptionLabel={(o) => o.toString()}
        onChange={(_, val) => setYearFilter(p => ({ ...p, start: val, end: val > p.end ? null : p.end }))}
        renderInput={(params) => <TextField {...params} label={t('startYear')} size="small" />}
        value={yearFilter.start}
        sx={{ minWidth: 40, flex: '0.1 1 auto' }}
        />
        <Autocomplete
        options={endYearOptions}
        getOptionLabel={(o) => o.toString()}
        onChange={(_, val) => setYearFilter(p => ({ ...p, end: val }))}
        renderInput={(params) => <TextField {...params} label={t('endYear')} size="small" />}
        key={`end-year-${yearFilter.start}`}
        value={yearFilter.end}
        sx={{ minWidth: 40, flex: '0.1 1 auto' }}
        />
        <Autocomplete
        multiple
        options={sources}
        getOptionLabel={(o) => o}
        onChange={(_, val) => setSelectedSources(val)}
        value={selectedSources}
        renderTags={(value, getTagProps) => {
            const tagsToShow = value.slice(0, 2);
            const remainingTags = value.length - tagsToShow.length;
            let tagsText = tagsToShow.join(', ');
            if (remainingTags > 0) {
                tagsText += `, +${remainingTags}`;
            }
            return (
                <Typography variant="body2" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {tagsText}
                </Typography>
            );
        }}
        renderInput={(params) => <TextField {...params} label={t('sources')} size="small" />}
        sx={{ minWidth: 70, flex: '0.06 1 auto' }}
        />

        {/* --- BOTÃO MOVIDO PARA CÁ --- */}
        {isFilterApplied && (
            <IconButton onClick={handleClearFilters} size="small">
            <ReplayIcon />
            </IconButton>
        )}
        </Box>

        <Box sx={{ flexGrow: 1 }} /> {/* Espaçador */}

        {/* --- BOTÃO REMOVIDO DAQUI --- */}

        <Button
        variant="text"
        onClick={handleOpenExportModal}
        sx={{ fontWeight: 'bold' }}
        >
        {t('export')}
        </Button>
        </Paper>
    );
};

export default FilterControls;
