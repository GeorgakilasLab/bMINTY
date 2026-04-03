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
    Tooltip,
    IconButton,
    Divider
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
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
    const [checksum, setChecksum] = useState('');
    const [exportedFilename, setExportedFilename] = useState('');
    const [checksumCopied, setChecksumCopied] = useState(false);

    const tables = ['study', 'assay', 'interval', 'assembly', 'signal', 'cell', 'pipeline'];

    const openDialog = () => {
        setDialogOpen(true);
        setChecksum('');
        setExportedFilename('');
        setChecksumCopied(false);
    };

    const closeDialog = () => {
        setDialogOpen(false);
        setChecksum('');
        setExportedFilename('');
        setChecksumCopied(false);
    };

    const handleSnackClose = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackOpen(false);
    };

    const handleCopyChecksum = async () => {
        try {
            await navigator.clipboard.writeText(checksum);
            setChecksumCopied(true);
            setTimeout(() => setChecksumCopied(false), 2000);
        } catch {
            // fallback for older browsers
            const el = document.createElement('textarea');
            el.value = checksum;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            setChecksumCopied(true);
            setTimeout(() => setChecksumCopied(false), 2000);
        }
    };

    const handleDownloadChecksum = () => {
        const content = `${checksum}  ${exportedFilename}\n`;
        const blob = new Blob([content], { type: 'text/plain' });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = `${exportedFilename}.sha256`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);
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

                const sha256 = response.headers['x-sha256-checksum'] || '';
                setExportedFilename(filename);
                setChecksum(sha256);
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
                responseType: 'blob',
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

            const sha256 = response.headers['x-sha256-checksum'] || '';
            setExportedFilename(filename);
            setChecksum(sha256);
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
                    {checksum ? (
                        /* Post-export checksum view */
                        <Box>
                            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                                <CheckCircleOutlineIcon sx={{ color: '#388e3c' }} />
                                <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#388e3c' }}>
                                    Export complete
                                </Typography>
                            </Stack>
                            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                                File downloaded: <strong>{exportedFilename}</strong>
                            </Typography>

                            <Divider sx={{ mb: 2 }} />

                            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                                SHA-256 Checksum
                            </Typography>
                            <Typography variant="caption" color="textSecondary" sx={{ mb: 1, display: 'block' }}>
                                Use this checksum to verify the integrity of the downloaded file.
                            </Typography>
                            <Box sx={{
                                p: 1.5,
                                bgcolor: '#f5f5f5',
                                borderRadius: 1,
                                border: '1px solid #e0e0e0',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                mb: 2
                            }}>
                                <Typography
                                    variant="body2"
                                    sx={{
                                        fontFamily: 'monospace',
                                        fontSize: '0.75rem',
                                        wordBreak: 'break-all',
                                        flex: 1
                                    }}
                                >
                                    {checksum}
                                </Typography>
                                <Tooltip title={checksumCopied ? 'Copied!' : 'Copy to clipboard'}>
                                    <IconButton size="small" onClick={handleCopyChecksum}>
                                        <ContentCopyIcon fontSize="small" sx={{ color: checksumCopied ? '#388e3c' : 'inherit' }} />
                                    </IconButton>
                                </Tooltip>
                            </Box>
                            <Button
                                variant="outlined"
                                size="small"
                                startIcon={<FileDownloadIcon />}
                                onClick={handleDownloadChecksum}
                                sx={{ borderColor: '#388e3c', color: '#388e3c' }}
                            >
                                Download .sha256 file
                            </Button>
                        </Box>
                    ) : (
                        /* Export format selection view */
                        <>
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
                                        .slice(0, 5)
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
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    {checksum ? (
                        <Button onClick={closeDialog} variant="contained" sx={{ backgroundColor: '#388e3c' }}>
                            Done
                        </Button>
                    ) : (
                        <>
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
                        </>
                    )}
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
