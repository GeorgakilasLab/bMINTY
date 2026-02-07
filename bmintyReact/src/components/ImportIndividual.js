// src/components/ImportIndividualTable.jsx
// Note: requires react-dropzone: npm install react-dropzone
import React, { useState, useRef, useEffect } from 'react';
import EntitySelectImportDialog from './EntitySelectImportDialog';
import axios from 'axios';
import {
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Typography,
    Box,
    Stepper,
    Step,
    StepLabel,
    Table,
    TableHead,
    TableRow,
    TableCell,
    TableBody,
    TableContainer,
    Snackbar,
    Alert,
    Checkbox,
    FormControlLabel,
    CircularProgress,
    Paper,
    Chip,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Grid
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useDropzone } from 'react-dropzone';
import { API_BASE } from '../config';
// Allow very long-running uploads (e.g., multi-GB CSVs)
const AXIOS_TIMEOUT = 600000; // 10 minutes

// Define each table's description and detailed columns
const tableOptions = [
    {
        label: 'Study',
        value: 'study',
        tableDescription: 'A collection of assays with an overarching goal of exploring a biological system.',
        columns: [
            { term: 'id', description: 'Unique study id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'external_id', description: 'External id for mapping to repositories.', example: 'GSE109129', type: 'text', strictness: 'mandatory' },
            { term: 'external_repo', description: 'External repository name (e.g., GEO, TCGA).', example: 'GEO', type: 'text', strictness: 'mandatory' },
            { term: 'name', description: 'Human-friendly unique study name.', example: 'Tamoxifen effect on breast cancer', type: 'text', strictness: 'mandatory' },
            { term: 'description', description: 'Detailed purpose of the study.', example: 'Investigating genome-wide binding efficacy of GATA3.', type: 'text', strictness: 'optional' },
            { term: 'availability', description: 'Flag to show/hide study in UI.', example: '1', type: 'bool', strictness: 'optional' }
        ]
    },
    {
        label: 'Assay',
        value: 'assay',
        tableDescription: 'An experimental protocol performed on a sample that is part of a wider collection of experiments (study).',
        columns: [
            { term: 'id', description: 'Unique assay id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'external_id', description: 'External assay id for mapping to repositories.', example: 'GSM111221', type: 'text', strictness: 'mandatory' },
            { term: 'type', description: 'Type of the assay.', example: 'ChIP-Seq', type: 'text', strictness: 'mandatory' },
            { term: 'target', description: 'Target of the assay (if applicable).', example: 'GATA3', type: 'text', strictness: 'optional' },
            { term: 'name', description: 'Human-friendly unique id of the assay.', example: 'patient 1', type: 'text', strictness: 'mandatory' },
            { term: 'tissue', description: 'Tissue origin of the sample.', example: 'peripheral blood', type: 'text', strictness: 'optional' },
            { term: 'cell_type', description: 'Cell type isolated from the sample.', example: 'macrophages', type: 'text', strictness: 'optional' },
            { term: 'treatment', description: 'Treatment applied prior to assay.', example: 'treated with tamoxifen', type: 'text', strictness: 'mandatory' },
            { term: 'date', description: 'Date that the assay was performed.', example: '2024-03-17', type: 'datetime', strictness: 'optional' },
            { term: 'platform', description: 'Platform used to perform the assay.', example: 'Illumina NextSeq 2000', type: 'text', strictness: 'mandatory' },
            { term: 'kit', description: 'Library preparation kit used.', example: 'TruSeq ChIP Library Preparation Kit', type: 'text', strictness: 'optional' },
            { term: 'description', description: 'Detailed purpose of the assay.', example: 'Investigating effect of tamoxifen on GATA3 binding.', type: 'text', strictness: 'optional' },
            { term: 'availability', description: 'Flag to show/hide assay in UI.', example: '1', type: 'bool', strictness: 'optional' },
            { term: 'study_id', description: 'Foreign key to study table.', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'pipeline_id', description: 'Foreign key to pipeline table.', example: '1', type: 'int', strictness: 'mandatory' }
        ]
    },
    {
        label: 'Assembly',
        value: 'assembly',
        tableDescription: 'The genome assembly and the repository used to analyze an assay.',
        columns: [
            { term: 'id', description: 'Unique assembly id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'name', description: 'Name of the external repository hosting the assembly.', example: 'Ensembl v102', type: 'text', strictness: 'mandatory' },
            { term: 'version', description: 'Common assembly version name.', example: 'GRCh38', type: 'text', strictness: 'mandatory' },
            { term: 'species', description: '3-letter species code.', example: 'hsa', type: 'text', strictness: 'optional' }
        ]
    },
    {
        label: 'Interval',
        value: 'interval',
        tableDescription: 'A genomic interval with its associated metadata.',
        columns: [
            { term: 'id', description: 'Unique interval id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'external_id', description: 'External id to uniquely distinguish interval.', example: 'peak_x_ENST8190381290381', type: 'text', strictness: 'mandatory' },
            { term: 'parental_id', description: 'External id of parent interval.', example: 'ENSG8746234', type: 'text', strictness: 'optional' },
            { term: 'name', description: 'Name of the interval.', example: 'Foxp3.1', type: 'text', strictness: 'optional' },
            { term: 'type', description: 'Type of the interval.', example: 'transcript', type: 'text/predetermined', strictness: 'mandatory' },
            { term: 'biotype', description: 'Biotype of the interval.', example: 'protein_coding', type: 'text/predetermined', strictness: 'optional' },
            { term: 'chromosome', description: 'Chromosome location.', example: 'chr1', type: 'text', strictness: 'mandatory' },
            { term: 'start', description: 'Start coordinate.', example: '293109', type: 'int', strictness: 'mandatory' },
            { term: 'end', description: 'End coordinate.', example: '391309', type: 'int', strictness: 'mandatory' },
            { term: 'strand', description: 'DNA strand.', example: '+', type: 'text', strictness: 'mandatory' },
            { term: 'summit', description: 'Summit coordinate for peaks.', example: 'n/a', type: 'int', strictness: 'optional' },
            { term: 'assembly_id', description: 'Foreign key to assembly table.', example: '1', type: 'int', strictness: 'mandatory' }
        ]
    },
    {
        label: 'Cell',
        value: 'cell',
        tableDescription: 'A single cell with its associated metadata.',
        columns: [
            { term: 'cell_id', description: 'Unique cell id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'name', description: 'Cell identifier produced by pipelines.', example: 'CGTAGCTTCG', type: 'text', strictness: 'mandatory' },
            { term: 'type', description: 'Cell kind: cell (single cell) or spot (SRT).', example: 'cell', type: 'text/predetermined', strictness: 'mandatory' },
            { term: 'label', description: 'Experimental cell identity label (if available).', example: 'CD4+ T cell', type: 'text', strictness: 'optional' },
            { term: 'x_coordinate', description: 'X coordinate in spatial assay.', example: '100', type: 'int', strictness: 'optional' },
            { term: 'y_coordinate', description: 'Y coordinate in spatial assay.', example: '200', type: 'int', strictness: 'optional' },
            { term: 'z_coordinate', description: 'Z coordinate in spatial assay.', example: '50', type: 'int', strictness: 'optional' },
            { term: 'assay_id', description: 'Foreign key to assay table.', example: '1', type: 'int', strictness: 'mandatory' }
        ]
    },
    {
        label: 'Signal',
        value: 'signal',
        tableDescription: 'Raw signal counts and statistics for intervals from an assay.',
        columns: [
            { term: 'id', description: 'Unique signal id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'signal', description: 'Raw reads overlapping the interval.', example: '500', type: 'int', strictness: 'mandatory' },
            { term: 'p_value', description: 'P-value from peak calling.', example: 'n/a', type: 'float', strictness: 'optional' },
            { term: 'padj_value', description: 'Adjusted p-value from peak calling.', example: 'n/a', type: 'float', strictness: 'optional' },
            { term: 'assay_id', description: 'Foreign key to assay table.', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'interval_id', description: 'Foreign key to interval table.', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'cell_id', description: 'Foreign key to cell table (if applicable).', example: '1', type: 'int', strictness: 'mandatory/situational' }
        ]
    },
    {
        label: 'Pipeline',
        value: 'pipeline',
        tableDescription: 'Information about the pipeline used to analyze an assay.',
        columns: [
            { term: 'id', description: 'Unique pipeline id internally (auto-increment).', example: '1', type: 'int', strictness: 'mandatory' },
            { term: 'name', description: 'Human-friendly pipeline id.', example: 'scRNA-Seq analysis', type: 'text', strictness: 'mandatory' },
            { term: 'description', description: 'Pipeline steps and tools used.', example: 'Includes fastqc, fastp, star, htseq.', type: 'text', strictness: 'optional' },
            { term: 'external_url', description: 'URL of external pipeline repository.', example: 'https://workflowhub.eu/...', type: 'text', strictness: 'mandatory' }
        ]
    }
];

const FileDropzone = ({ onFileAccepted }) => {
    const onDrop = acceptedFiles => {
        if (acceptedFiles.length > 0) {
            onFileAccepted(acceptedFiles[0]);
        }
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        multiple: false,
        accept: { 'text/csv': ['.csv'] },
    });

    return (
        <Box
            {...getRootProps()}
            sx={{ border: '2px dashed grey', borderRadius: 4, textAlign: 'center', p: 2, mt: 2, cursor: 'pointer' }}
        >
            <input {...getInputProps()} />
            <Typography>
                {isDragActive ? 'Drop the .csv file here...' : "Drag and drop a .csv file here"}
            </Typography>
        </Box>
    );
};

export default function ImportIndividualTable({ onImportSuccess, open = false, onClose }) {
    const [selectedOption, setSelectedOption] = useState(null);
    const [dialogOpen, setDialogOpen] = useState(false);

    // Sync external open prop with internal state
    React.useEffect(() => {
        if (open) {
            openStudyDialog();
        }
    }, [open]);
    const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
    const [studyDialogOpen, setStudyDialogOpen] = useState(false);
    const [pipelineDialogOpen, setPipelineDialogOpen] = useState(false);
    const [assayDialogOpen, setAssayDialogOpen] = useState(false);
    const [assemblyDialogOpen, setAssemblyDialogOpen] = useState(false);
    const [selectedStudy, setSelectedStudy] = useState(null);
    const [selectedPipeline, setSelectedPipeline] = useState(null);
    const [selectedAssay, setSelectedAssay] = useState(null);
    const [selectedAssembly, setSelectedAssembly] = useState(null);
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [snackOpen, setSnackOpen] = useState(false);
    const [snackMessage, setSnackMessage] = useState('');
    const [snackSeverity, setSnackSeverity] = useState('success');
    
    // Grouped import state (interval → cell → signal)
    const [groupedImportStep, setGroupedImportStep] = useState(0); // 0=interval, 1=cell, 2=signal
    const [intervalFile, setIntervalFile] = useState(null);
    const [cellFile, setCellFile] = useState(null);
    const [signalFile, setSignalFile] = useState(null);
    const [omitZeroSignals, setOmitZeroSignals] = useState(false);
    const [ignoreOptionalTypeErrors, setIgnoreOptionalTypeErrors] = useState(false);
    const [ignoreRowErrors, setIgnoreRowErrors] = useState(false);
    const [deduplicateIntervals, setDeduplicateIntervals] = useState(true);
    const [jobStatus, setJobStatus] = useState(null);
    const statusPollRef = useRef(null);
    const [showSchema, setShowSchema] = useState(false);

    // Clear polling interval on unmount
    useEffect(() => {
        return () => {
            if (statusPollRef.current) {
                clearInterval(statusPollRef.current);
            }
        };
    }, []);

    const handleSnackClose = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackOpen(false);
    };

    const openStudyDialog = () => setStudyDialogOpen(true);

    // Callbacks for step guide - when user goes back
    const handleStudyChange = (study) => {
        setSelectedStudy(study);
        if (!study) {
            // Clear subsequent selections when study is cleared
            setSelectedPipeline(null);
            setSelectedAssay(null);
            // Reopen study dialog when cleared (back button was clicked)
            setStudyDialogOpen(true);
            setPipelineDialogOpen(false);
            setAssayDialogOpen(false);
        }
    };

    const handlePipelineChange = (pipeline) => {
        setSelectedPipeline(pipeline);
        if (!pipeline) {
            // Clear assay and assembly when pipeline is cleared
            setSelectedAssay(null);
            setSelectedAssembly(null);
            // Reopen pipeline dialog when cleared (back button was clicked)
            setPipelineDialogOpen(true);
            setAssayDialogOpen(false);
            setAssemblyDialogOpen(false);
        }
    };

    const handleAssayChange = (assay) => {
        setSelectedAssay(assay);
        if (!assay) {
            // Clear assembly when assay is cleared
            setSelectedAssembly(null);
            // Reopen assay dialog when cleared (back button was clicked)
            setAssayDialogOpen(true);
            setAssemblyDialogOpen(false);
        }
    };

    // Step 1: Study selection/creation
    const handleStudySelect = study => {
        setSelectedStudy(study);
        setStudyDialogOpen(false);
        setPipelineDialogOpen(true);
    };

    const handleStudyCreate = study => {
        setSelectedStudy(study);
        setStudyDialogOpen(false);
        setPipelineDialogOpen(true);
    };

    // Step 2: Pipeline selection/creation
    const handlePipelineSelect = pipeline => {
        setSelectedPipeline(pipeline);
        setPipelineDialogOpen(false);
        setAssayDialogOpen(true);
    };

    const handlePipelineCreate = pipeline => {
        setSelectedPipeline(pipeline);
        setPipelineDialogOpen(false);
        setAssayDialogOpen(true);
    };

    // Step 3: Assay selection/creation
    const handleAssaySelect = assay => {
        setSelectedAssay(assay);
        setAssayDialogOpen(false);
        setAssemblyDialogOpen(true);
    };

    const handleAssayCreate = assay => {
        setSelectedAssay(assay);
        setAssayDialogOpen(false);
        setAssemblyDialogOpen(true);
    };

    // Step 4: Assembly selection/creation
    const handleAssemblySelect = assembly => {
        setSelectedAssembly(assembly);
        setAssemblyDialogOpen(false);
        // Delay opening the main dialog to prevent flash
        setTimeout(() => {
            // Automatically select interval table (which triggers grouped import flow)
            const intervalOption = tableOptions.find(opt => opt.value === 'interval');
            setSelectedOption(intervalOption);
            setDialogOpen(true);
        }, 100);
    };

    const handleAssemblyCreate = assembly => {
        setSelectedAssembly(assembly);
        setAssemblyDialogOpen(false);
        // Delay opening the main dialog to prevent flash
        setTimeout(() => {
            // Automatically select interval table (which triggers grouped import flow)
            const intervalOption = tableOptions.find(opt => opt.value === 'interval');
            setSelectedOption(intervalOption);
            setDialogOpen(true);
        }, 100);
    };



    const closeDialog = () => {
        setDialogOpen(false);
        setSelectedOption(null);
        setFile(null);
        setJobStatus(null);
        if (statusPollRef.current) {
            clearInterval(statusPollRef.current);
            statusPollRef.current = null;
        }
    };

    const handleFinalCancelClick = () => {
        // show confirmation similar to previous screens
        setCancelConfirmOpen(true);
    };

    const handleFinalCancelConfirm = () => {
        setCancelConfirmOpen(false);
        // clear progress and close all dialogs
        setSelectedStudy(null);
        setSelectedPipeline(null);
        setSelectedAssay(null);
        setSelectedAssembly(null);
        setDialogOpen(false);
    };

    const handleFinalCancelAbort = () => {
        setCancelConfirmOpen(false);
    };

    const handleFinalBack = () => {
        // If a table is selected, go back to table selection; else go back to assembly
        if (selectedOption) {
            // If in grouped import flow, handle back within that flow
            if (['interval', 'cell', 'signal'].includes(selectedOption.value) && groupedImportStep > 0) {
                setGroupedImportStep(groupedImportStep - 1);
                return;
            }
            setSelectedOption(null);
            setGroupedImportStep(0);
            setIntervalFile(null);
            setCellFile(null);
            setSignalFile(null);
            setJobStatus(null);
            if (statusPollRef.current) {
                clearInterval(statusPollRef.current);
                statusPollRef.current = null;
            }
            return;
        }
        setDialogOpen(false);
        setAssemblyDialogOpen(true);
    };

    const handleImport = async () => {
        // Check if this is a grouped import (interval/cell/signal)
        if (selectedOption && ['interval', 'cell', 'signal'].includes(selectedOption.value)) {
            return handleGroupedImport();
        }
        
        // Standard single-table import
        if (!file || !selectedOption) return;
        setLoading(true);
        try {
            const form = new FormData();
            form.append('file', file);
            if (selectedStudy && selectedStudy.id) {
                form.append('study_id', selectedStudy.id);
            }
            if (selectedAssay && selectedAssay.id) {
                form.append('assay_id', selectedAssay.id);
            }
            const response = await axios.post(
                `${API_BASE}/import/${selectedOption.value}/`,
                form,
                { headers: { 'Content-Type': 'multipart/form-data' }, timeout: AXIOS_TIMEOUT }
            );

            setSnackMessage(response.data.message || 'Import successful!');
            setSnackSeverity('success');
            setSnackOpen(true);
            closeDialog();
            onImportSuccess?.();
        } catch (err) {
            setSnackMessage(err.response?.data?.error || 'Import failed.');
            setSnackSeverity('error');
            setSnackOpen(true);
        } finally {
            setLoading(false);
        }
    };

    const stopStatusPolling = () => {
        if (statusPollRef.current) {
            clearInterval(statusPollRef.current);
            statusPollRef.current = null;
        }
    };

    const startStatusPolling = (statusUrl) => {
        stopStatusPolling();
        statusPollRef.current = setInterval(async () => {
            try {
                const { data } = await axios.get(statusUrl, { timeout: 15000 });
                setJobStatus(data);
                if (['completed', 'failed'].includes(data.status)) {
                    stopStatusPolling();
                    setLoading(false);
                    if (data.status === 'completed' && data.result?.success) {
                        const counts = data.result.counts || {};
                        const summary = `Bulk import successful!\n• Intervals: ${counts.intervals}` +
                            (typeof counts.original_interval_count !== 'undefined' ? ` (${counts.original_interval_count} total before dedup)` : '') +
                            (typeof counts.deduplicated_intervals !== 'undefined' ? ` [${counts.deduplicated_intervals} deduplicated]` : '') +
                            `\n• Cells: ${counts.cells}\n• Signals: ${counts.signals}` +
                            (typeof counts.zero_signals !== 'undefined' ? `\n• Zero-value signals: ${counts.zero_signals}` : '') +
                            (typeof counts.non_zero_signals !== 'undefined' ? `\n• Non-zero signals: ${counts.non_zero_signals}` : '');
                        setSnackMessage(summary);
                        setSnackSeverity('success');
                        setSnackOpen(true);
                        closeDialog();
                        setGroupedImportStep(0);
                        setIntervalFile(null);
                        setCellFile(null);
                        setSignalFile(null);
                        onImportSuccess?.();
                        // Refresh the page to show updated data (delay to allow reading the message)
                        setTimeout(() => window.location.reload(), 6000);
                    } else {
                        setSnackMessage(data.error || data.result?.error || 'Bulk import failed.');
                        setSnackSeverity('error');
                        setSnackOpen(true);
                        // Refresh the page even on failure to reset state
                        setTimeout(() => window.location.reload(), 5000);
                    }
                }
            } catch (pollErr) {
                // Keep polling; transient failures are fine
            }
        }, 2000);
    };

    const handleGroupedImport = async () => {
        // Only submit when user has selected all files and is on the final step
        if (groupedImportStep < 2) {
            if (groupedImportStep === 0) {
                if (!intervalFile) {
                    setSnackMessage('Interval file is required.');
                    setSnackSeverity('error');
                    setSnackOpen(true);
                    return;
                }
                setGroupedImportStep(1);
            } else if (groupedImportStep === 1) {
                setGroupedImportStep(2);
            }
            return;
        }

        if (!intervalFile || !signalFile) {
            setSnackMessage('Interval and signal files are required.');
            setSnackSeverity('error');
            setSnackOpen(true);
            return;
        }

        setLoading(true);
        setJobStatus({ status: 'uploading', phase: 'upload', step: 1, step_name: 'Uploading Files', total_steps: 5, message: 'Uploading files...', upload_progress: 0 });
        try {
            const form = new FormData();
            form.append('interval_file', intervalFile);
            if (cellFile) {
                form.append('cell_file', cellFile);
            }
            form.append('signal_file', signalFile);
            form.append('assembly_id', selectedAssembly.id);
            form.append('assay_id', selectedAssay.id);
            if (omitZeroSignals) {
                form.append('omit_zero_signals', 'true');
            }
            if (ignoreOptionalTypeErrors) {
                form.append('ignore_optional_type_errors', 'true');
            }
            if (ignoreRowErrors) {
                form.append('ignore_row_errors', 'true');
            }
            if (deduplicateIntervals) {
                form.append('deduplicate_intervals', 'true');
            }

            const response = await axios.post(
                `${API_BASE}/database/import/bulk/`,
                form,
                { 
                    headers: { 'Content-Type': 'multipart/form-data' }, 
                    timeout: AXIOS_TIMEOUT,
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setJobStatus(prev => ({ 
                            ...prev, 
                            upload_progress: percentCompleted,
                            message: `Uploading files... ${percentCompleted}%`
                        }));
                    }
                }
            );

            if (response.status === 202 && response.data?.status_url) {
                setJobStatus({ status: 'queued', phase: 'init', message: 'Queued for processing...' });
                startStatusPolling(response.data.status_url);
            } else if (response.data?.success) {
                // Fallback in case background mode isn’t used
                const counts = response.data.counts || {};
                const summary = `Bulk import successful!\n• Intervals: ${counts.intervals}` +
                    (typeof counts.original_interval_count !== 'undefined' ? ` (${counts.original_interval_count} total before dedup)` : '') +
                    (typeof counts.deduplicated_intervals !== 'undefined' ? ` [${counts.deduplicated_intervals} deduplicated]` : '') +
                    `\n• Cells: ${counts.cells}\n• Signals: ${counts.signals}` +
                    (typeof counts.zero_signals !== 'undefined' ? `\n• Zero-value signals: ${counts.zero_signals}` : '') +
                    (typeof counts.non_zero_signals !== 'undefined' ? `\n• Non-zero signals: ${counts.non_zero_signals}` : '');
                setSnackMessage(summary);
                setSnackSeverity('success');
                setSnackOpen(true);
                closeDialog();
                setGroupedImportStep(0);
                setIntervalFile(null);
                setCellFile(null);
                setSignalFile(null);
                onImportSuccess?.();
                setLoading(false);
            } else {
                throw new Error(response.data?.error || 'Bulk import failed.');
            }
        } catch (err) {
            stopStatusPolling();
            setLoading(false);
            setSnackMessage(err.response?.data?.error || err.message || 'Bulk import failed. Transaction rolled back.');
            setSnackSeverity('error');
            setSnackOpen(true);
        }
    };


    return (
        <>
            {/* Step 1: Study selection/import */}
            <EntitySelectImportDialog
                open={studyDialogOpen}
                onClose={() => {
                    setStudyDialogOpen(false);
                    onClose?.();
                }}
                entityType="study"
                apiBase={API_BASE}
                columns={tableOptions[0].columns}
                onSelect={handleStudySelect}
                onCreate={handleStudyCreate}
                allowNotes={true}
                showStepGuide={true}
            />

            {/* Step 2: Pipeline selection/import */}
            <EntitySelectImportDialog
                open={pipelineDialogOpen}
                onClose={() => setPipelineDialogOpen(false)}
                entityType="pipeline"
                apiBase={API_BASE}
                columns={tableOptions[6].columns}
                onSelect={handlePipelineSelect}
                onCreate={handlePipelineCreate}
                allowNotes={false}
                selectedStudy={selectedStudy}
                onStudyChange={handleStudyChange}
                showStepGuide={true}
            />

            {/* Step 3: Assay selection/import */}
            <EntitySelectImportDialog
                open={assayDialogOpen}
                onClose={() => setAssayDialogOpen(false)}
                entityType="assay"
                apiBase={API_BASE}
                columns={tableOptions[1].columns}
                onSelect={handleAssaySelect}
                onCreate={handleAssayCreate}
                allowNotes={true}
                parentId={selectedStudy?.id}
                pipelineId={selectedPipeline?.id}
                selectedStudy={selectedStudy}
                selectedPipeline={selectedPipeline}
                selectedAssay={selectedAssay}
                onStudyChange={handleStudyChange}
                onPipelineChange={handlePipelineChange}
                onAssayChange={handleAssayChange}
                showStepGuide={true}
            />

            {/* Step 4: Assembly selection/import */}
            <EntitySelectImportDialog
                open={assemblyDialogOpen}
                onClose={() => setAssemblyDialogOpen(false)}
                entityType="assembly"
                apiBase={API_BASE}
                columns={tableOptions[2].columns}
                onSelect={handleAssemblySelect}
                onCreate={handleAssemblyCreate}
                allowNotes={false}
                selectedStudy={selectedStudy}
                selectedPipeline={selectedPipeline}
                selectedAssay={selectedAssay}
                onStudyChange={handleStudyChange}
                onPipelineChange={handlePipelineChange}
                onAssayChange={handleAssayChange}
                showStepGuide={true}
            />

            {/* Step 5: Table import */}
            {dialogOpen && (
                <Dialog open={dialogOpen} onClose={handleFinalCancelClick} maxWidth="md" fullWidth>
                    <DialogTitle>
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#388e3c' }}>
                                Data Import Wizard
                            </Typography>
                            <Button
                                variant="outlined"
                                color="error"
                                onClick={handleFinalCancelClick}
                                sx={{ textTransform: 'none' }}
                                disabled={loading}
                            >
                                Cancel
                            </Button>
                        </Box>
                    </DialogTitle>
                    <DialogContent dividers>
                        {/* Loading overlay with progress */}
                        {loading && (
                            <Box
                                sx={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    zIndex: 9999,
                                    borderRadius: 1,
                                    px: 3
                                }}
                            >
                                {/* Green circular progress spinner */}
                                <Box sx={{ position: 'relative', width: 100, height: 100, mb: 3 }}>
                                    <CircularProgress
                                        variant="determinate"
                                        value={(() => {
                                            if (jobStatus?.phase === 'upload' && jobStatus?.upload_progress !== undefined) {
                                                return jobStatus.upload_progress;
                                            } else if (['intervals', 'cells', 'signals'].includes(jobStatus?.phase)) {
                                                if (jobStatus.phase === 'intervals' && jobStatus.total_intervals) {
                                                    return Math.min(100, (jobStatus.processed / jobStatus.total_intervals) * 100);
                                                } else if (jobStatus.phase === 'cells' && jobStatus.total_cells) {
                                                    return Math.min(100, (jobStatus.processed / jobStatus.total_cells) * 100);
                                                } else if (jobStatus.phase === 'signals' && jobStatus.total_signals) {
                                                    return Math.min(100, (jobStatus.processed / jobStatus.total_signals) * 100);
                                                }
                                            }
                                            return 0;
                                        })()}
                                        size={100}
                                        thickness={4}
                                        sx={{ color: '#4caf50' }}
                                    />
                                    <Box
                                        sx={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                            right: 0,
                                            bottom: 0,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center'
                                        }}
                                    >
                                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#4caf50' }}>
                                            {(() => {
                                                if (jobStatus?.phase === 'upload' && jobStatus?.upload_progress !== undefined) {
                                                    return `${jobStatus.upload_progress}%`;
                                                } else if (['intervals', 'cells', 'signals'].includes(jobStatus?.phase)) {
                                                    if (jobStatus.phase === 'intervals' && jobStatus.total_intervals) {
                                                        return Math.min(100, Math.round((jobStatus.processed / jobStatus.total_intervals) * 100)) + '%';
                                                    } else if (jobStatus.phase === 'cells' && jobStatus.total_cells) {
                                                        return Math.min(100, Math.round((jobStatus.processed / jobStatus.total_cells) * 100)) + '%';
                                                    } else if (jobStatus.phase === 'signals' && jobStatus.total_signals) {
                                                        return Math.min(100, Math.round((jobStatus.processed / jobStatus.total_signals) * 100)) + '%';
                                                    }
                                                }
                                                return '0%';
                                            })()}
                                        </Typography>
                                    </Box>
                                </Box>

                                <Typography variant="h6" sx={{ color: '#388e3c', fontWeight: 'bold', mb: 2, textAlign: 'center' }}>
                                    Step {jobStatus?.step ?? 0}/{jobStatus?.total_steps ?? 5} {jobStatus?.step_name || ''}
                                </Typography>

                                <Box sx={{ width: '100%', maxWidth: '450px' }}>
                                    {jobStatus && (
                                        <Box sx={{ width: '100%' }}>
                                            {/* Row count during processing */}
                                            {['intervals', 'cells', 'signals'].includes(jobStatus.phase) && (
                                                <Typography variant="body2" sx={{ textAlign: 'center', color: '#555', mb: 1 }}>
                                                    {jobStatus.phase === 'intervals' && `Intervals: ${jobStatus.processed || 0} / ${typeof jobStatus.total_intervals !== 'undefined' ? jobStatus.total_intervals : '?'}`}
                                                    {jobStatus.phase === 'cells' && `Cells: ${jobStatus.processed || 0} / ${typeof jobStatus.total_cells !== 'undefined' ? jobStatus.total_cells : '?'}`}
                                                    {jobStatus.phase === 'signals' && `Signals: ${jobStatus.processed || 0} / ${typeof jobStatus.total_signals !== 'undefined' ? jobStatus.total_signals : '?'}`}
                                                </Typography>
                                            )}

                                            {/* Zero signals skip counter */}
                                            {jobStatus.zeros !== undefined && jobStatus.phase === 'signals' && (
                                                <Typography variant="caption" sx={{ color: '#888', textAlign: 'center', display: 'block', mb: 1 }}>
                                                    Zero-value signals skipped: {jobStatus.zeros}
                                                </Typography>
                                            )}
                                        </Box>
                                    )}
                                </Box>
                            </Box>
                        )}
                        {/* Stepper milestones and selected cards (green) */}
                        <Box sx={{ mb: 3 }}>
                            <Stepper activeStep={3} sx={{ mb: 2 }}>
                                <Step completed={!!selectedStudy}>
                                    <StepLabel>Study</StepLabel>
                                </Step>
                                <Step completed={!!selectedPipeline}>
                                    <StepLabel>Pipeline</StepLabel>
                                </Step>
                                <Step completed={!!selectedAssay}>
                                    <StepLabel>Assay</StepLabel>
                                </Step>
                                <Step completed={!!selectedAssembly}>
                                    <StepLabel>Assembly</StepLabel>
                                </Step>
                            </Stepper>
                            {selectedStudy && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Study:</strong> {selectedStudy.name || selectedStudy.external_id || selectedStudy.id}
                                    </Typography>
                                </Paper>
                            )}
                            {selectedPipeline && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Pipeline:</strong> {selectedPipeline.name || selectedPipeline.external_id || selectedPipeline.id}
                                    </Typography>
                                </Paper>
                            )}
                            {selectedAssay && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Assay:</strong> {selectedAssay.name || selectedAssay.external_id || selectedAssay.id}
                                    </Typography>
                                </Paper>
                            )}
                            {selectedAssembly && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Assembly:</strong> {selectedAssembly.name || selectedAssembly.external_id || selectedAssembly.id}
                                    </Typography>
                                </Paper>
                            )}
                        </Box>

                        {/* Table selection or table details */}
                        <Typography variant="h6" sx={{ mb: 1 }}>
                            {selectedOption ? `Import ${selectedOption.label} Table` : 'Import Table'}
                        </Typography>
                        
                        {/* Grouped import stepper for interval/cell/signal */}
                        {selectedOption && ['interval', 'cell', 'signal'].includes(selectedOption.value) && (
                            <Box sx={{ mb: 3 }}>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                    Import interval, cell, and signal data in a coordinated transaction. If any step fails, all changes are rolled back.
                                </Typography>
                                <Stepper activeStep={groupedImportStep} sx={{ mb: 2 }}>
                                    <Step completed={groupedImportStep > 0}>
                                        <StepLabel>Intervals</StepLabel>
                                    </Step>
                                    <Step completed={groupedImportStep > 1}>
                                        <StepLabel>Cells (Optional)</StepLabel>
                                    </Step>
                                    <Step completed={groupedImportStep > 2}>
                                        <StepLabel>Signals</StepLabel>
                                    </Step>
                                </Stepper>
                            </Box>
                        )}
                        
                        {selectedOption ? (
                            <>
                                <Typography gutterBottom>
                                    {(() => {
                                        const isGrouped = selectedOption && ['interval','cell','signal'].includes(selectedOption.value);
                                        let optionForText = selectedOption;
                                        if (isGrouped) {
                                            const stepToValue = ['interval','cell','signal'][groupedImportStep] || 'interval';
                                            optionForText = tableOptions.find(opt => opt.value === stepToValue) || selectedOption;
                                        }
                                        return optionForText.tableDescription;
                                    })()}
                                </Typography>

                                <Accordion expanded={showSchema} onChange={() => setShowSchema(!showSchema)} sx={{ mb: 2 }}>
                                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                            Expected columns (click to {showSchema ? 'collapse' : 'expand'})
                                        </Typography>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <TableContainer component={Paper} variant="outlined">
                                            <Table size="small" stickyHeader>
                                                <TableHead>
                                                    <TableRow>
                                                        <TableCell>Column</TableCell>
                                                        <TableCell>Description</TableCell>
                                                        <TableCell>Example</TableCell>
                                                        <TableCell>Type</TableCell>
                                                        <TableCell>Strictness</TableCell>
                                                    </TableRow>
                                                </TableHead>
                                                <TableBody>
                                                    {(() => {
                                                        const isGrouped = selectedOption && ['interval','cell','signal'].includes(selectedOption.value);
                                                        let optionForColumns = selectedOption;
                                                        if (isGrouped) {
                                                            const stepToValue = ['interval','cell','signal'][groupedImportStep] || 'interval';
                                                            optionForColumns = tableOptions.find(opt => opt.value === stepToValue) || selectedOption;
                                                        }
                                                        return optionForColumns.columns.map(col => (
                                                        <TableRow key={col.term} hover>
                                                            <TableCell><strong>{col.term}</strong></TableCell>
                                                            <TableCell>{col.description || '-'}</TableCell>
                                                            <TableCell>{col.example || '-'}</TableCell>
                                                            <TableCell>{col.type || '-'}</TableCell>
                                                            <TableCell>{col.strictness || '-'}</TableCell>
                                                        </TableRow>
                                                        ));
                                                    })()}
                                                </TableBody>
                                            </Table>
                                        </TableContainer>
                                    </AccordionDetails>
                                </Accordion>
                                
                                {/* File upload based on grouped import step */}
                                {['interval', 'cell', 'signal'].includes(selectedOption.value) ? (
                                    <>
                                        {groupedImportStep === 0 && (
                                            <>
                                                <Typography variant="body2" sx={{ mb: 2, fontWeight: 'bold', color: '#388e3c' }}>
                                                    Step 1: Upload Interval CSV <Chip label="Required" size="small" color="error" variant="outlined" />
                                                </Typography>
                                                <FileDropzone onFileAccepted={setIntervalFile} />
                                                {intervalFile && <Typography variant="body2" mt={2}>Selected file: <strong>{intervalFile.name}</strong></Typography>}
                                            </>
                                        )}
                                        {groupedImportStep === 1 && (
                                            <>
                                                <Typography variant="body2" sx={{ mb: 2, fontWeight: 'bold', color: '#388e3c' }}>
                                                    Step 2: Upload Cell CSV <Chip label="Optional" size="small" color="warning" variant="outlined" />
                                                </Typography>
                                                <FileDropzone onFileAccepted={setCellFile} />
                                                {cellFile && <Typography variant="body2" mt={2}>Selected file: <strong>{cellFile.name}</strong></Typography>}
                                                {!cellFile && <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic', color: '#999' }}>No cell file selected - proceeding without cells.</Typography>}
                                            </>
                                        )}
                                        {groupedImportStep === 2 && (
                                            <>
                                                <Typography variant="body2" sx={{ mb: 2, fontWeight: 'bold', color: '#388e3c' }}>
                                                    Step 3: Upload Signal CSV <Chip label="Required" size="small" color="error" variant="outlined" />
                                                </Typography>
                                                <FileDropzone onFileAccepted={setSignalFile} />
                                                {signalFile && <Typography variant="body2" mt={2}>Selected file: <strong>{signalFile.name}</strong></Typography>}
                                                <Box sx={{ mt: 3, mb: 2 }}>
                                                    <Grid container spacing={1.5}>
                                                        <Grid item xs={12} sm={6} md={3}>
                                                            <FormControlLabel
                                                                control={<Checkbox checked={deduplicateIntervals} onChange={(e) => setDeduplicateIntervals(e.target.checked)} size="medium" />}
                                                                label={<Typography variant="body2"><strong>Deduplicate Intervals</strong><br/><Typography variant="caption" sx={{ color: '#666' }}>Reuse existing intervals by external_id</Typography></Typography>}
                                                                sx={{ width: '100%', alignItems: 'flex-start' }}
                                                            />
                                                        </Grid>
                                                        <Grid item xs={12} sm={6} md={3}>
                                                            <FormControlLabel
                                                                control={<Checkbox checked={omitZeroSignals} onChange={(e) => setOmitZeroSignals(e.target.checked)} size="medium" />}
                                                                label={<Typography variant="body2"><strong>Omit Zero Signals</strong><br/><Typography variant="caption" sx={{ color: '#666' }}>Skip storing signal==0</Typography></Typography>}
                                                                sx={{ width: '100%', alignItems: 'flex-start' }}
                                                            />
                                                        </Grid>
                                                        <Grid item xs={12} sm={6} md={3}>
                                                            <FormControlLabel
                                                                control={<Checkbox checked={ignoreOptionalTypeErrors} onChange={(e) => setIgnoreOptionalTypeErrors(e.target.checked)} size="medium" />}
                                                                label={<Typography variant="body2"><strong>Ignore Type Errors</strong><br/><Typography variant="caption" sx={{ color: '#666' }}>Set optional fields to NULL</Typography></Typography>}
                                                                sx={{ width: '100%', alignItems: 'flex-start' }}
                                                            />
                                                        </Grid>
                                                        <Grid item xs={12} sm={6} md={3}>
                                                            <FormControlLabel
                                                                control={<Checkbox checked={ignoreRowErrors} onChange={(e) => setIgnoreRowErrors(e.target.checked)} size="medium" />}
                                                                label={<Typography variant="body2"><strong>Ignore Row Errors</strong><br/><Typography variant="caption" sx={{ color: '#666' }}>Skip invalid values</Typography></Typography>}
                                                                sx={{ width: '100%', alignItems: 'flex-start' }}
                                                            />
                                                        </Grid>
                                                    </Grid>
                                                </Box>
                                            </>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        <FileDropzone onFileAccepted={setFile} />
                                        {file && <Typography variant="body2" mt={2}>Selected file: <strong>{file.name}</strong></Typography>}
                                    </>
                                )}
                            </>
                        ) : (
                            <>
                                <Typography gutterBottom>Select which table to import into:</Typography>
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                                    {tableOptions
                                        // exclude entities already selected in wizard steps
                                        .filter(opt => !['study','assay','assembly','pipeline'].includes(opt.value))
                                        .map(opt => (
                                            <Button key={opt.value} variant="outlined" onClick={() => setSelectedOption(opt)}>
                                                {opt.label}
                                            </Button>
                                        ))}
                                </Box>
                            </>
                        )}
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={handleFinalBack} disabled={loading}>Back</Button>
                        {selectedOption && ['interval', 'cell', 'signal'].includes(selectedOption.value) && (
                            <>
                                {groupedImportStep === 0 && (
                                    <Button 
                                        onClick={handleImport} 
                                        variant="contained" 
                                        disabled={loading || !intervalFile}
                                    >
                                        Next
                                    </Button>
                                )}
                                {groupedImportStep === 1 && (
                                    <Button 
                                        onClick={handleImport} 
                                        variant="contained"
                                        disabled={loading}
                                    >
                                        Next
                                    </Button>
                                )}
                                {groupedImportStep === 2 && (
                                    <Button 
                                        onClick={handleImport} 
                                        variant="contained" 
                                        disabled={loading || !signalFile}
                                    >
                                        Import
                                    </Button>
                                )}
                            </>
                        )}
                        {selectedOption && !['interval', 'cell', 'signal'].includes(selectedOption.value) && (
                            <Button 
                                onClick={handleImport} 
                                variant="contained" 
                                disabled={loading || !file}
                            >
                                Import
                            </Button>
                        )}
                    </DialogActions>
                </Dialog>
            )}

            {/* Cancel confirmation dialog for final screen */}
            <Dialog open={cancelConfirmOpen} onClose={handleFinalCancelAbort}>
                <DialogTitle>Cancel Selection?</DialogTitle>
                <DialogContent>
                    <Typography>
                        You have selected Study, Pipeline, Assay and Assembly. Are you sure you want to cancel and lose all progress?
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleFinalCancelAbort} variant="contained">Keep Importing</Button>
                    <Button onClick={handleFinalCancelConfirm} variant="outlined" color="error">Cancel & Clear All</Button>
                </DialogActions>
            </Dialog>

            <Snackbar
                open={snackOpen}
                autoHideDuration={6000}
                onClose={handleSnackClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                sx={{ mb: 6 }} // push it up slightly so it sits just above the import button
            >
                <Alert onClose={handleSnackClose} severity={snackSeverity} sx={{ width: '100%' }}>
                    {snackMessage}
                </Alert>
            </Snackbar>
        </>
    );
}
