# Changelog - Frontend

## [Unreleased]

### Changed
- Migrada exportação de dados brutos para usar endpoint de streaming CSV do backend
- Substituída abordagem fetch JSON + transform por download direto via endpoint `/all_events_data_filter_years_enriched/{ya}/{yb}`
- Removida dependência da função `getAllEventsFilteredRaw()` no componente ExportModal

### Performance
- Eliminado processamento de JSON para CSV no cliente
- Reduzido uso de memória no browser ao exportar datasets grandes
- Download de CSV agora inicia imediatamente sem aguardar transformação de dados

### Deprecated
- Função `getAllEventsFilteredRaw()` em `src/api/services.js` marcada como deprecated

### Technical Details
- Arquivo modificado: `src/components/shared/ExportModal.jsx`
  - Removido import de `getAllEventsFilteredRaw`
  - Adicionado import de `apiClient`
  - Implementado download direto via elemento `<a>` temporário
- Arquivo modificado: `src/api/services.js`
  - Adicionado comentário `@deprecated` na função `getAllEventsFilteredRaw()`

### CSV Export Columns
O endpoint de streaming exporta 9 colunas:
1. DOI
2. Timestamp
3. Year
4. Source
5. Prefix
6. Title
7. Publication Year
8. Journal
9. Field
