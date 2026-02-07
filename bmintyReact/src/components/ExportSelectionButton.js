import React, { useState } from 'react';
import {
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Typography,
    Box,
    Snackbar,
    Alert,
    FormControlLabel,
    RadioGroup,
    Radio,
    CircularProgress,
    Stack,
    Tooltip
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import axios from 'axios';
import { API_BASE } from '../config';

export default function ExportSelectionButton({ filters, onExportSuccess }) {
    const [dialogOpen, setDialogOpen] = useState(false);
    const [exportFormat, setExportFormat] = useState('sqlite');
    const [selectedTable, setSelectedTable] = useState('study');
    const [loading, setLoading] = useState(false);
    const [loadingRoCrate, setLoadingRoCrate] = useState(false);
    const [snackOpen, setSnackOpen] = useState(false);
    const [snackMessage, setSnackMessage] = useState('');
    const [snackSeverity, setSnackSeverity] = useState('success');

    const tables = ['study', 'assay', 'interval', 'assembly', 'signal', 'cell', 'pipeline'];

    const openDialog = () => {
        setDialogOpen(true);
    };

    const closeDialog = () => {
        setDialogOpen(false);
    };

    const handleSnackClose = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackOpen(false);
    };

    const handleExport = async (includeRoCrate = false) => {
        const isRoCrate = includeRoCrate;
        if (isRoCrate) {
            setLoadingRoCrate(true);
        } else {
            setLoading(true);
        }
        try {
            // Build query params from filters
            const params = new URLSearchParams();
            
            // Add all filter parameters
            Object.entries(filters).forEach(([key, value]) => {
                if (value && value !== '' && value !== 'all' && value !== 'All') {
                    // Handle availability filters
                    if (key === 'study_availability') {
                        if (value === 'available') params.append(key, 'true');
                        else if (value === 'unavailable') params.append(key, 'false');
                    } else if (key === 'assay_availability') {
                        if (value === 'available') params.append(key, 'true');
                        else if (value === 'unavailable') params.append(key, 'false');
                    } else if (Array.isArray(value)) {
                        // Handle array values by appending each item separately
                        value.forEach(item => {
                            if (item) params.append(`${key}[]`, item);
                        });
                    } else {
                        params.append(key, value);
                    }
                }
            });

            // Handle full database dump
            if (exportFormat === 'full') {
                // For full dump, export just the SQLite database file (fast)
                const url = `${API_BASE}/database/export/sqlite/`;
                
                const response = await axios.get(url, {
                    responseType: 'blob',
                });

                const filename = 'full_database.sqlite3';
                const blob = new Blob([response.data], { type: 'application/x-sqlite3' });
                const link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(link.href);

                setSnackMessage('Full database export successful! File downloaded.');
                setSnackSeverity('success');
                setSnackOpen(true);
                closeDialog();
                onExportSuccess?.();
                return;
            }

            // Add format parameter
            params.append('export_format', exportFormat);

            // Add RO-Crate parameter if enabled
            if (includeRoCrate) {
                params.append('ro_crate', 'true');
            }

            // Add table parameter if CSV format
            if (exportFormat === 'csv') {
                params.append('table', selectedTable);
            }

            // Build the URL
            const url = `${API_BASE}/export_filtered_sqlite/?${params.toString()}`;

            // Download the file
            const response = await axios.get(url, {
                responseType: exportFormat === 'zip' ? 'blob' : 'blob',
            });

            // Determine filename
            let filename = 'export';
            const contentType = response.headers['content-type'];
            if (contentType && contentType.includes('sqlite')) {
                filename += '.sqlite3';
            } else if (contentType && contentType.includes('zip')) {
                filename = includeRoCrate ? 'export_ro-crate.zip' : 'export.zip';
            } else if (contentType && contentType.includes('csv')) {
                filename += `_${selectedTable}.csv`;
            }

            // Create blob and download
            const blob = new Blob([response.data], { type: contentType });
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(link.href);

            const roCrateMsg = includeRoCrate ? ' with RO-Crate metadata' : '';
            setSnackMessage(`Export${roCrateMsg} successful! File downloaded.`);
            setSnackSeverity('success');
            setSnackOpen(true);
            closeDialog();
            onExportSuccess?.();
        } catch (error) {
            console.error('Export error:', error);
            const errorMsg = error.response?.data?.error || error.message || 'Export failed.';
            setSnackMessage(errorMsg);
            setSnackSeverity('error');
            setSnackOpen(true);
        } finally {
            if (isRoCrate) {
                setLoadingRoCrate(false);
            } else {
                setLoading(false);
            }
        }
    };

    return (
        <>
            <Button
                variant="contained"
                endIcon={<FileDownloadIcon />}
                onClick={openDialog}
                sx={{ backgroundColor: '#47854aff', '&:hover': { backgroundColor: '#4caf50' } }}
            >
                Export Selection
            </Button>

            {/* Export Dialog */}
            <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
                <DialogTitle>
                    Export Selected Data
                </DialogTitle>
                <DialogContent dividers sx={{ mt: 2 }}>
                    <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
                        Choose your export format. Most options respect your current filters. The "Full Database Dump" option exports everything regardless of filters.
                    </Typography>

                    <Box sx={{ mb: 3 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
                            Export Format
                        </Typography>
                        <RadioGroup
                            value={exportFormat}
                            onChange={(e) => setExportFormat(e.target.value)}
                        >
                            <FormControlLabel
                                value="sqlite"
                                control={<Radio />}
                                label={
                                    <Box>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                            SQLite Database
                                        </Typography>
                                        <Typography variant="caption" color="textSecondary">
                                            Single .sqlite3 file with all filtered data
                                        </Typography>
                                    </Box>
                                }
                            />
                            <FormControlLabel
                                value="zip"
                                control={<Radio />}
                                label={
                                    <Box>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                            ZIP Archive
                                        </Typography>
                                        <Typography variant="caption" color="textSecondary">
                                            Database + individual CSV files for each table
                                        </Typography>
                                    </Box>
                                }
                            />
                            <FormControlLabel
                                value="csv"
                                control={<Radio />}
                                label={
                                    <Box>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                            Single Table (CSV)
                                        </Typography>
                                        <Typography variant="caption" color="textSecondary">
                                            Export one specific table as CSV
                                        </Typography>
                                    </Box>
                                }
                            />
                            <FormControlLabel
                                value="full"
                                control={<Radio />}
                                label={
                                    <Box>
                                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                            Full Database Dump (SQLite)
                                        </Typography>
                                        <Typography variant="caption" color="textSecondary">
                                            Complete database file - fast export, ignores all filters
                                        </Typography>
                                    </Box>
                                }
                            />
                        </RadioGroup>
                    </Box>

                    {exportFormat === 'csv' && (
                        <Box sx={{ mb: 3 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
                                Select Table
                            </Typography>
                            <RadioGroup
                                value={selectedTable}
                                onChange={(e) => setSelectedTable(e.target.value)}
                            >
                                {tables.map((table) => (
                                    <FormControlLabel
                                        key={table}
                                        value={table}
                                        control={<Radio />}
                                        label={<Typography variant="body2" sx={{ textTransform: 'capitalize' }}>{table}</Typography>}
                                    />
                                ))}
                            </RadioGroup>
                        </Box>
                    )}

                    <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                        <Typography variant="caption" color="textSecondary">
                            <strong>Applied Filters:</strong>
                            <br />
                            {Object.entries(filters)
                                .filter(([, v]) => {
                                    // Exclude empty, 'all', 'All' values, and empty arrays
                                    if (!v || v === '' || v === 'all' || v === 'All') return false;
                                    if (Array.isArray(v) && v.length === 0) return false;
                                    return true;
                                })
                                .map(([k, v]) => {
                                    const displayValue = Array.isArray(v) ? v.join(', ') : String(v);
                                    return (
                                        <div key={k}>
                                            • {k}: {displayValue.substring(0, 50)}
                                        </div>
                                    );
                                })
                                .slice(0, 5) // Show first 5 filters
                            }
                            {Object.entries(filters).filter(([, v]) => {
                                if (!v || v === '' || v === 'all' || v === 'All') return false;
                                if (Array.isArray(v) && v.length === 0) return false;
                                return true;
                            }).length > 5 && (
                                <div>
                                    • ... and {Object.entries(filters).filter(([, v]) => {
                                        if (!v || v === '' || v === 'all' || v === 'All') return false;
                                        if (Array.isArray(v) && v.length === 0) return false;
                                        return true;
                                    }).length - 5} more filter(s)
                                </div>
                            )}
                        </Typography>
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeDialog} disabled={loading || loadingRoCrate}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => handleExport(false)}
                        variant="contained"
                        disabled={loading || loadingRoCrate}
                        sx={{ backgroundColor: '#388e3c' }}
                    >
                        {loading ? (
                            <Stack direction="row" alignItems="center" gap={1}>
                                <CircularProgress size={20} color="inherit" />
                                Exporting...
                            </Stack>
                        ) : (
                            'Export'
                        )}
                    </Button>
                    <Tooltip 
                        title="Packages your data with standardized research metadata including: file descriptions, table schemas (columns, keys), data counts, and applied filters. This follows the RO-Crate 1.2 specification for F.A.I.R. data."
                        arrow
                        placement="top"
                    >
                        <span>
                            <Button
                                onClick={() => handleExport(true)}
                                variant="contained"
                                disabled={loading || loadingRoCrate || exportFormat === 'full'}
                                sx={{ backgroundColor: '#1976d2' }}
                            >
                                {loadingRoCrate ? (
                                    <Stack direction="row" alignItems="center" gap={1}>
                                        <CircularProgress size={20} color="inherit" />
                                        Exporting...
                                    </Stack>
                                ) : (
                                    'Export RO-Crate'
                                )}
                            </Button>
                        </span>
                    </Tooltip>
                </DialogActions>
            </Dialog>

            {/* Snackbar */}
            <Snackbar
                open={snackOpen}
                autoHideDuration={6000}
                onClose={handleSnackClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                sx={{ mb: 6 }}
            >
                <Alert onClose={handleSnackClose} severity={snackSeverity} sx={{ width: '100%' }}>
                    {snackMessage}
                </Alert>
            </Snackbar>
        </>
    );
}
