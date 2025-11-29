import React, { useState } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TablePagination } from '@mui/material';
import { useTranslation } from 'react-i18next'; // Importe o hook

const DataTable = ({ data, columns }) => {
    const { t } = useTranslation(); // Inicialize o hook
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(5);

    if (!data || data.length === 0) {
        return <p>{t('noData')}</p>;
    }

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    return (
        <Paper variant="outlined" sx={{ mt: 2, borderRadius: '8px', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 300 }}>
        <Table stickyHeader aria-label="sticky table" sx={{ minWidth: '100%', tableLayout: 'fixed' }}>
        <TableHead>
        <TableRow sx={{
            "& .MuiTableCell-root:first-of-type": {
                borderTopLeftRadius: "8px",
            },
            "& .MuiTableCell-root:last-of-type": {
                borderTopRightRadius: "8px",
            },
        }}>
        {columns.map((col) => (
            <TableCell
            key={col.key}
            sx={{
                fontWeight: 'bold',
                textAlign: col.align || 'left',
                width: col.width,
            }}
            >
            {col.header}
            </TableCell>
        ))}
        </TableRow>
        </TableHead>
        <TableBody>
        {data.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((row, index) => (
            <TableRow hover role="checkbox" tabIndex={-1} key={index}>
            {columns.map((col) => (
                <TableCell
                key={col.key}
                sx={{
                    textAlign: col.align || 'left',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                }}
                >
                {row[col.key]}
                </TableCell>
            ))}
            </TableRow>
        ))}
        </TableBody>
        </Table>
        </TableContainer>
        <TablePagination
        rowsPerPageOptions={[5, 10, 25]}
        component="div"
        count={data.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        // --- CORREÇÃO APLICADA AQUI ---
        labelRowsPerPage={t('rowsPerPage')}
        />
        </Paper>
    );
};

export default DataTable;
