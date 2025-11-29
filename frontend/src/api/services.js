import apiClient from './axiosConfig';

const transformApiData = (data, keyName, valueName) => {
    const keys = data[keyName] || [];
    const values = data[valueName] || [];
    return keys.map((key, index) => ({ [keyName]: key, [valueName]: values[index] }));
};

const buildEndpoint = (basePath, startYear, endYear, sources) => {
    if (apiClient.defaults.baseURL.includes('localhost:3001')) {
        return basePath;
    }

    const endpointUrl = new URL(basePath, apiClient.defaults.baseURL);
    if (startYear) endpointUrl.searchParams.append('ya', startYear);
    if (endYear) endpointUrl.searchParams.append('yb', endYear);
    if (sources && sources.length > 0) {
        sources.forEach(source => endpointUrl.searchParams.append('sources', source));
    }
    return endpointUrl.pathname + endpointUrl.search;
};

export const getEventsByYear = async (startYear, endYear, sources) => {
    const endpoint = buildEndpoint('/events_years', startYear, endYear, sources);
    return apiClient.get(endpoint).then(response => transformApiData(response.data, 'year', 'events'));
};

export const getFieldsAndEvents = async (startYear, endYear, sources) => {
    const endpoint = buildEndpoint('/fields_events', startYear, endYear, sources);
    return apiClient.get(endpoint).then(response => transformApiData(response.data, 'field', 'events'));
};

export const getEventsBySource = async (startYear, endYear, sources) => {
    const endpoint = buildEndpoint('/events_sources', startYear, endYear, sources);
    return apiClient.get(endpoint).then(response => transformApiData(response.data, 'source', 'events'));
};

export const getYearlyEventsForSource = async (source) => {
    // CORREÇÃO: Codifica o nome da fonte para ser seguro para URLs
    const endpoint = `/events_source_years/${encodeURIComponent(source)}`;
    return apiClient.get(endpoint).then(response => transformApiData(response.data, 'year', 'events')).catch(error => {
        console.error(`Erro ao buscar dados para a fonte ${source}:`, error);
        return [];
    });
};


export const getAllSources = async () => {
    return apiClient.get('/sources').then(response => response.data.sources || []);
};

export const getAvailableYears = async () => {
    return apiClient.get('/events_years').then(response => {
        const fullData = transformApiData(response.data, 'year', 'events');
        return fullData.map(item => item.year).sort((a, b) => a - b);
    }).catch(error => {
        console.error("Erro ao buscar anos disponíveis:", error);
        return [];
    });
};

export const getEventsFieldsRaw = async () => {
    const endpoint = '/all_events_fields_events';
    return apiClient.get(endpoint).then(response => response.data);
};

// @deprecated Use /all_events_data_filter_years_enriched/{ya}/{yb} para download direto via <a> tag
export const getAllEventsFilteredRaw = async (startYear, endYear) => {
    const endpoint = `/all_events_data_filter_years/${startYear}/${endYear}`;
    return apiClient.get(endpoint).then(response => response.data);
};

export const searchDois = async (dois) => {
    try {
        const response = await apiClient.post('/search_dois', { dois });
        return response.data;
    } catch (error) {
        console.error('Erro ao buscar DOIs:', error);
        throw error;
    }
};
