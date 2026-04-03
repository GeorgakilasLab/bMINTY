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
    CircularProgress,
    Stack,
    Checkbox,
    FormControlLabel,
    TextField,
    InputAdornment,
    Tooltip
} from '@mui/material';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import axios from 'axios';
import { API_BASE } from '../config';

async function computeSha256(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export default function ImportFullDatabase({ onImportSuccess, open = false, onClose }) {
    const [dialogOpen, setDialogOpen] = useState(false);
    const [createBackup, setCreateBackup] = useState(true);

    React.useEffect(() => {
        setDialogOpen(open);
    }, [open]);

    const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [computingChecksum, setComputingChecksum] = useState(false);
    const [computedChecksum, setComputedChecksum] = useState('');
    const [expectedChecksum, setExpectedChecksum] = useState('');
    const [snackOpen, setSnackOpen] = useState(false);
    const [snackMessage, setSnackMessage] = useState('');
    const [snackSeverity, setSnackSeverity] = useState('success');

    const closeDialog = () => {
        setDialogOpen(false);
        setSelectedFile(null);
        setComputedChecksum('');
        setExpectedChecksum('');
        onClose?.();
    };

    const openConfirmDialog = () => {
        if (!selectedFile) {
            setSnackMessage('Please select a SQLite file first.');
            setSnackSeverity('warning');
            setSnackOpen(true);
            return;
        }
        setConfirmDialogOpen(true);
    };

    const closeConfirmDialog = () => {
        setConfirmDialogOpen(false);
    };

    const handleSnackClose = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackOpen(false);
    };

    const handleFileChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.sqlite3')) {
            setSnackMessage('Please select a .sqlite3 file.');
            setSnackSeverity('error');
            setSnackOpen(true);
            event.target.value = null;
            return;
        }

        setSelectedFile(file);
        setComputedChecksum('');
        setComputingChecksum(true);
        try {
            const hash = await computeSha256(file);
            setComputedChecksum(hash);
        } catch {
            setComputedChecksum('');
        } finally {
            setComputingChecksum(false);
        }
    };

    const checksumMatch =
        expectedChecksum.trim() !== '' &&
        computedChecksum !== '' &&
        expectedChecksum.trim().toLowerCase() === computedChecksum.toLowerCase();

    const checksumMismatch =
        expectedChecksum.trim() !== '' &&
        computedChecksum !== '' &&
        expectedChecksum.trim().toLowerCase() !== computedChecksum.toLowerCase();

    const handleImport = async () => {
        if (!selectedFile) {
            setSnackMessage('No file selected.');
            setSnackSeverity('error');
            setSnackOpen(true);
            return;
        }

        setLoading(true);
        closeConfirmDialog();

        try {
            const formData = new FormData();
            formData.append('sqlite_file', selectedFile);
            formData.append('create_backup', createBackup);

            const response = await axios.post(
                `${API_BASE}/database/import/sqlite/`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    timeout: 600000,
                }
            );

            setSnackMessage(response.data.message || 'Database imported successfully!');
            setSnackSeverity('success');
            setSnackOpen(true);
            closeDialog();
            onImportSuccess?.();
        } catch (error) {
            console.error('Import error:', error);
            const errorMsg = error.response?.data?.error || error.message || 'Import failed.';
            setSnackMessage(errorMsg);
            setSnackSeverity('error');
            setSnackOpen(true);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* File Selection Dialog */}
            <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
                <DialogTitle>
                    Import Full Database
                </DialogTitle>
                <DialogContent dividers sx={{ mt: 2, position: 'relative' }}>
                    {/* Loading Overlay */}
                    {loading && (
                        <Box sx={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            bgcolor: 'rgba(255, 255, 255, 0.9)',
                            zIndex: 9999,
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 2
                        }}>
                            <CircularProgress size={60} sx={{ color: '#4caf50' }} />
                            <Typography variant="h6" sx={{ color: '#2e7d32' }}>
                                Importing Database...
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                                This may take several minutes. Please do not close this window.
                            </Typography>
                        </Box>
                    )}

                    <Box sx={{
                        p: 2,
                        bgcolor: '#fff3e0',
                        borderRadius: 1,
                        border: '2px solid #ff6f00',
                        mb: 3
                    }}>
                        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                            <WarningAmberIcon color="warning" />
                            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#e65100' }}>
                                Warning
                            </Typography>
                        </Stack>
                        <Typography variant="body2" color="textSecondary">
                            <strong>All existing data will be deleted and replaced</strong> with the imported database.
                            {createBackup
                                ? ' The current database will be backed up automatically.'
                                : ' No backup will be created.'}
                        </Typography>
                        <Typography variant="body2" color="textSecondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                            Note: Import may take several minutes depending on database size.
                        </Typography>
                    </Box>

                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={createBackup}
                                onChange={(e) => setCreateBackup(e.target.checked)}
                                sx={{ color: '#4caf50', '&.Mui-checked': { color: '#4caf50' } }}
                            />
                        }
                        label={
                            <Box>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                    Create backup before importing (recommended)
                                </Typography>
                                <Typography variant="caption" color="textSecondary">
                                    Backup allows recovery if import fails or data needs to be restored.
                                </Typography>
                            </Box>
                        }
                        sx={{ mb: 3, alignItems: 'flex-start' }}
                    />

                    <Typography variant="body2" sx={{ mb: 2 }}>
                        Select a SQLite database file (.sqlite3) to import:
                    </Typography>

                    <Box sx={{
                        p: 3,
                        border: '2px dashed #bdbdbd',
                        borderRadius: 2,
                        textAlign: 'center',
                        bgcolor: '#fafafa',
                        cursor: 'pointer',
                        '&:hover': {
                            bgcolor: '#f5f5f5',
                            borderColor: '#9e9e9e'
                        }
                    }}>
                        <input
                            type="file"
                            accept=".sqlite3"
                            onChange={handleFileChange}
                            style={{ display: 'none' }}
                            id="database-file-input"
                        />
                        <label htmlFor="database-file-input" style={{ cursor: 'pointer' }}>
                            <FileUploadIcon sx={{ fontSize: 48, color: '#9e9e9e', mb: 1 }} />
                            <Typography variant="body1" sx={{ mb: 1 }}>
                                Click to select a database file
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                                Only .sqlite3 files are accepted
                            </Typography>
                        </label>
                    </Box>

                    {selectedFile && (
                        <Box sx={{ mt: 2, p: 2, bgcolor: '#e8f5e9', borderRadius: 1 }}>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                Selected file:
                            </Typography>
                            <Typography variant="body2" color="textSecondary">
                                {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
                            </Typography>
                            {computingChecksum && (
                                <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 1 }}>
                                    <CircularProgress size={14} />
                                    <Typography variant="caption" color="textSecondary">
                                        Computing checksum…
                                    </Typography>
                                </Stack>
                            )}
                            {computedChecksum && (
                                <Box sx={{ mt: 1 }}>
                                    <Typography variant="caption" color="textSecondary">
                                        SHA-256:
                                    </Typography>
                                    <Typography
                                        variant="caption"
                                        sx={{
                                            display: 'block',
                                            fontFamily: 'monospace',
                                            fontSize: '0.7rem',
                                            wordBreak: 'break-all',
                                            color: '#555'
                                        }}
                                    >
                                        {computedChecksum}
                                    </Typography>
                                </Box>
                            )}
                        </Box>
                    )}

                    {/* Checksum verification */}
                    <Box sx={{ mt: 3 }}>
                        <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 1 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                Verify Checksum (optional)
                            </Typography>
                            <Tooltip
                                title="Paste the expected SHA-256 checksum here to verify the file hasn't been corrupted or tampered with. You can obtain the checksum from the Export dialog."
                                arrow
                            >
                                <HelpOutlineIcon sx={{ fontSize: 16, color: 'text.secondary', cursor: 'help' }} />
                            </Tooltip>
                        </Stack>
                        <TextField
                            fullWidth
                            size="small"
                            placeholder="Paste expected SHA-256 checksum here…"
                            value={expectedChecksum}
                            onChange={(e) => setExpectedChecksum(e.target.value)}
                            inputProps={{ style: { fontFamily: 'monospace', fontSize: '0.78rem' } }}
                            InputProps={{
                                endAdornment: computedChecksum && expectedChecksum.trim() ? (
                                    <InputAdornment position="end">
                                        {checksumMatch ? (
                                            <Tooltip title="Checksums match — file is intact">
                                                <CheckCircleIcon sx={{ color: '#388e3c' }} />
                                            </Tooltip>
                                        ) : (
                                            <Tooltip title="Checksum mismatch — file may be corrupted or incorrect">
                                                <CancelIcon sx={{ color: '#d32f2f' }} />
                                            </Tooltip>
                                        )}
                                    </InputAdornment>
                                ) : null
                            }}
                        />
                        {checksumMatch && (
                            <Typography variant="caption" sx={{ color: '#388e3c', mt: 0.5, display: 'block' }}>
                                Checksums match — file integrity verified.
                            </Typography>
                        )}
                        {checksumMismatch && (
                            <Typography variant="caption" sx={{ color: '#d32f2f', mt: 0.5, display: 'block' }}>
                                Checksum mismatch! The file may be corrupted or not the expected database.
                            </Typography>
                        )}
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeDialog} disabled={loading}>
                        Cancel
                    </Button>
                    <Tooltip
                        title={checksumMismatch ? 'Checksum mismatch — verify you have the correct file before importing' : ''}
                        arrow
                    >
                        <span>
                            <Button
                                onClick={openConfirmDialog}
                                variant="contained"
                                disabled={!selectedFile || loading || computingChecksum}
                                sx={{
                                    backgroundColor: checksumMismatch ? '#d32f2f' : '#ff6f00',
                                    '&:hover': { backgroundColor: checksumMismatch ? '#b71c1c' : '#ff8f00' }
                                }}
                            >
                                {checksumMismatch ? 'Import Anyway' : 'Import'}
                            </Button>
                        </span>
                    </Tooltip>
                </DialogActions>
            </Dialog>

            {/* Confirmation Dialog */}
            <Dialog open={confirmDialogOpen} onClose={closeConfirmDialog} maxWidth="xs" fullWidth>
                <DialogTitle sx={{ color: '#d32f2f' }}>
                    Confirm Database Replacement
                </DialogTitle>
                <DialogContent>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                        Are you sure you want to replace the current database?
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                        This action will:
                    </Typography>
                    <Box component="ul" sx={{ mt: 1, pl: 2 }}>
                        {createBackup ? (
                            <Typography component="li" variant="body2" color="textSecondary">
                                Backup the current database to .backup file
                            </Typography>
                        ) : (
                            <Typography component="li" variant="body2" color="textSecondary" sx={{ fontWeight: 600, color: '#d32f2f' }}>
                                Delete current database with NO backup
                            </Typography>
                        )}
                        <Typography component="li" variant="body2" color="textSecondary" sx={{ fontWeight: 600 }}>
                            Delete ALL existing data
                        </Typography>
                        <Typography component="li" variant="body2" color="textSecondary">
                            Replace with imported database
                        </Typography>
                        {!createBackup && (
                            <Typography component="li" variant="body2" color="textSecondary" sx={{ fontWeight: 600, color: '#d32f2f' }}>
                                Cannot be undone!
                            </Typography>
                        )}
                    </Box>
                    {checksumMismatch && (
                        <Box sx={{ mt: 2, p: 1.5, bgcolor: '#ffebee', borderRadius: 1, border: '1px solid #ef9a9a' }}>
                            <Typography variant="body2" sx={{ color: '#d32f2f', fontWeight: 600 }}>
                                Warning: Checksum mismatch detected!
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                                The file's checksum does not match the expected value. Proceeding may import an incorrect or corrupted database.
                            </Typography>
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeConfirmDialog}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleImport}
                        variant="contained"
                        color="error"
                        disabled={loading}
                    >
                        {loading ? (
                            <Stack direction="row" alignItems="center" gap={1}>
                                <CircularProgress size={20} color="inherit" />
                                Importing...
                            </Stack>
                        ) : (
                            'Confirm Import'
                        )}
                    </Button>
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
