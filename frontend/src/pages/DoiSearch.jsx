import React, { useState, useRef } from 'react';
import { Container, Typography, TextField, Button, Box, Paper, Stack, Divider, IconButton } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import PlaylistAddIcon from '@mui/icons-material/PlaylistAdd';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import { useTranslation } from 'react-i18next';
import { searchDois } from '../api/services';

const DoiSearch = () => {
    const { t } = useTranslation();
    const [doiList, setDoiList] = useState(['']);
    const [searchResults, setSearchResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    const processDoiText = (text) => {
        const doiRegex = /10\.\d{4,9}\/[-._;()/:A-Z0-9]+/gi;
        let parsedDois = text.match(doiRegex) || [];
        parsedDois = [...new Set(parsedDois)];

        if (parsedDois.length > 0) {
            setDoiList(parsedDois);
        } else {
            setDoiList(['']);
        }
    };

    const handlePaste = (event) => {
        const pastedText = event.clipboardData.getData('text');
        event.preventDefault();
        processDoiText(pastedText);
    };

    const handleInputChange = (index, newValue) => {
        const updatedList = [...doiList];
        updatedList[index] = newValue;
        setDoiList(updatedList);
    };

    const handleRemoveDoi = (indexToRemove) => {
        if (doiList.length > 1) {
            setDoiList(doiList.filter((_, index) => index !== indexToRemove));
        } else {
            setDoiList(['']);
        }
    };

    const handleAddDoi = () => {
        setDoiList([...doiList, '']);
    };

    const handleKeyDown = (event, index) => {
        if (event.key === 'Backspace' && doiList[index] === '') {
            handleRemoveDoi(index);
        }
    };

    const handleSearch = async () => {
        const finalDoiList = doiList.filter(doi => doi.trim() !== '');
        if (finalDoiList.length === 0) return;
        
        setLoading(true);
        setError(null);
        setSearchResults(null);
        
        try {
            const result = await searchDois(finalDoiList);
            setSearchResults(result);
        } catch (err) {
            console.error("Erro na busca:", err);
            setError(err.response?.data?.detail || "Erro ao buscar DOIs. Tente novamente.");
        } finally {
            setLoading(false);
        }
    };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const text = e.target.result;
                processDoiText(text);
            };
            reader.readAsText(file);
        }
        event.target.value = null;
    };

    const handleImportClick = () => {
        fileInputRef.current.click();
    };

    const showAddButton = doiList.some(doi => doi.trim() !== '');

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
        {t('doiSearchTitle')}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        {t('doiSearchSubtitle')}
        </Typography>

        <Stack spacing={2} sx={{ mb: 3 }}>
        {doiList.map((doi, index) => {
            const showDeleteButton = doiList.length > 1 || (doiList.length === 1 && doi.trim() !== '');

            return (
                <Box key={index}>
                <Typography variant="caption" display="block" sx={{ mb: 0.5, color: 'text.secondary' }}>
                {doiList.length > 1 ? `DOI ${index + 1}` : " "}
                </Typography>
                <Paper component="form" sx={{ p: '2px 4px', display: 'flex', alignItems: 'center', width: '100%' }}>
                <IconButton
                sx={{ p: '10px', visibility: showDeleteButton ? 'visible' : 'hidden' }}
                aria-label="remover"
                onClick={() => handleRemoveDoi(index)}
                >
                <DeleteIcon />
                </IconButton>

                <TextField
                placeholder={index === 0 ? t('pasteOrType') : ''}
                value={doi}
                onPaste={index === 0 ? handlePaste : undefined}
                onChange={(e) => handleInputChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                variant="outlined"
                fullWidth
                sx={{ "& .MuiOutlinedInput-root": { "& > fieldset": { border: 'none' } } }}
                />
                </Paper>
                </Box>
            );
        })}
        </Stack>

        <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept=".txt,.csv,.text,.tsv,.log,.md,.json,.dat"
        />

        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
        {showAddButton && (
            <IconButton onClick={handleAddDoi} aria-label="adicionar novo DOI">
            <PlaylistAddIcon />
            </IconButton>
        )}
        </Box>

        <Stack direction="row" spacing={2} alignItems="center">
        <Button
        variant="text"
        onClick={handleImportClick}
        sx={{ fontWeight: 'bold' }}
        >
        {t('importFromFile')}
        </Button>
        <Button
        variant="contained"
        onClick={handleSearch}
        disabled={doiList.every(doi => doi.trim() === '') || loading}
        disableElevation
        >
        {loading ? <CircularProgress size={24} /> : t('search')}
        </Button>
        </Stack>
        </Stack>

        {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
                {error}
            </Alert>
        )}

        {searchResults && (
            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                    Resultados da Busca
                </Typography>
                
                <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Chip label={`Total buscado: ${searchResults.total_searched}`} />
                    <Chip label={`Encontrados: ${searchResults.found_count}`} color="success" />
                    <Chip label={`Não encontrados: ${searchResults.not_found_count}`} color="error" />
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                {searchResults.results.map((result, index) => (
                    <Box key={index} sx={{ mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Typography variant="subtitle1" fontWeight="bold">
                                {result.doi}
                            </Typography>
                            <Chip 
                                label={result.found ? 'Encontrado' : 'Não encontrado'} 
                                color={result.found ? 'success' : 'error'} 
                                size="small" 
                            />
                        </Box>
                        
                        {result.found && (
                            <>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    Total de eventos: {result.total_events}
                                </Typography>
                                
                                {result.events_by_source && (
                                    <Box sx={{ mt: 1 }}>
                                        <Typography variant="body2" fontWeight="bold">
                                            Por fonte:
                                        </Typography>
                                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                                            {Object.entries(result.events_by_source).map(([source, count]) => (
                                                <Chip key={source} label={`${source}: ${count}`} size="small" />
                                            ))}
                                        </Box>
                                    </Box>
                                )}
                                
                                {result.events_by_year && (
                                    <Box sx={{ mt: 1 }}>
                                        <Typography variant="body2" fontWeight="bold">
                                            Por ano:
                                        </Typography>
                                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                                            {Object.entries(result.events_by_year)
                                                .sort(([a], [b]) => b - a)
                                                .map(([year, count]) => (
                                                    <Chip key={year} label={`${year}: ${count}`} size="small" />
                                                ))}
                                        </Box>
                                    </Box>
                                )}
                            </>
                        )}
                    </Box>
                ))}
            </Paper>
        )}
        </Container>
    );
};

export default DoiSearch;
