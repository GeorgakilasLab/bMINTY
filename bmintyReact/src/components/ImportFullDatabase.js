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
    FormControlLabel
} from '@mui/material';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import axios from 'axios';
import { API_BASE } from '../config';

export default function ImportFullDatabase({ onImportSuccess, open = false, onClose }) {
    const [dialogOpen, setDialogOpen] = useState(false);
    const [createBackup, setCreateBackup] = useState(true); // backup option

    // Sync external open prop with internal state
    React.useEffect(() => {
        setDialogOpen(open);
    }, [open]);
    const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
    const [selectedFile, setSelectedFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [snackOpen, setSnackOpen] = useState(false);
    const [snackMessage, setSnackMessage] = useState('');
    const [snackSeverity, setSnackSeverity] = useState('success');

    const closeDialog = () => {
        setDialogOpen(false);
        setSelectedFile(null);
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

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            if (!file.name.toLowerCase().endsWith('.sqlite3')) {
                setSnackMessage('Please select a .sqlite3 file.');
                setSnackSeverity('error');
                setSnackOpen(true);
                event.target.value = null;
                return;
            }
            setSelectedFile(file);
        }
    };

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
                    timeout: 600000, // 10 minutes timeout
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
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeDialog} disabled={loading}>
                        Cancel
                    </Button>
                    <Button
                        onClick={openConfirmDialog}
                        variant="contained"
                        disabled={!selectedFile || loading}
                        sx={{ backgroundColor: '#ff6f00', '&:hover': { backgroundColor: '#ff8f00' } }}
                    >
                        Import
                    </Button>
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
