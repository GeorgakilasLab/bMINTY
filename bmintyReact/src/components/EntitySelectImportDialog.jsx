// Reusable dialog for selecting/importing an entity (study/assay)
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    Button, Typography, Stack, TextField, CircularProgress,
    Box, Chip, Paper, Snackbar, Alert, InputAdornment, Stepper, Step, StepLabel
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

export default function EntitySelectImportDialog({
    open,
    onClose,
    entityType, // 'study', 'assay', 'pipeline', or 'assembly'
    apiBase,
    columns, // columns for table description
    onSelect,
    onCreate,
    allowNotes = false,
    parentId = null, // for assay, pass study id
    pipelineId = null, // for assay, pass pipeline id
    selectedStudy = null, // current study selection for context
    selectedPipeline = null, // current pipeline selection for context
    selectedAssay = null, // current assay selection for context
    onStudyChange = null, // callback when study is changed/cleared
    onPipelineChange = null, // callback when pipeline is changed/cleared
    onAssayChange = null, // callback when assay is changed/cleared
    showStepGuide = false // whether to show the multi-step guide
}) {
    const [entities, setEntities] = useState([]);
    const [allEntities, setAllEntities] = useState([]);
    const [search, setSearch] = useState('');
    const [page, setPage] = useState(1);
    const [pageSize] = useState(10);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [addDialogOpen, setAddDialogOpen] = useState(false);
    const [newEntity, setNewEntity] = useState({
        name: '',
        ...(entityType === 'assembly' 
            ? { version: '', species: '' }
            : entityType === 'pipeline'
            ? { external_url: '', description: '', note: '' }
            : { external_id: '', description: '', note: '' }
        ),
        ...(entityType === 'assay' ? { 
            type: '', 
            target: '',
            tissue: '',
            cell_type: '',
            treatment: '', 
            date: '',
            platform: '',
            kit: '',
            availability: true,
            study_id: parentId,
            pipeline: pipelineId || 1 // use selected pipeline or default to 1
        } : {}),
        ...(entityType === 'pipeline' ? {
            // pipeline fields initialized empty
        } : {})
    });
    const [snackOpen, setSnackOpen] = useState(false);
    const [snackMessage, setSnackMessage] = useState('');
    const [snackSeverity, setSnackSeverity] = useState('success');
    const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
    const [isClosing, setIsClosing] = useState(false);
    const [justOpened, setJustOpened] = useState(false);
    
    // Step guide state - initialize step based on entityType
    const getInitialStep = useCallback(() => {
        if (entityType === 'study') return 0;
        if (entityType === 'pipeline') return 1;
        if (entityType === 'assay') return 2;
        if (entityType === 'assembly') return 3;
        return 0;
    }, [entityType]);
    
    const [currentStep, setCurrentStep] = useState(getInitialStep());
    const [stepProgress, setStepProgress] = useState({
        study: selectedStudy,
        pipeline: selectedPipeline,
        assay: selectedAssay,
        assembly: null
    });

    // Define filterAndPaginate first (doesn't depend on other functions)
    const filterAndPaginate = useCallback((pg, term, source = allEntities) => {
        const searchLower = (term || '').toLowerCase();
        const filtered = !searchLower
            ? source
            : source.filter(e => (
                (e.name && e.name.toLowerCase().includes(searchLower)) ||
                (e.external_id && e.external_id.toLowerCase().includes(searchLower)) ||
                (e.description && e.description.toLowerCase().includes(searchLower)) ||
                (e.id && e.id.toString().includes(searchLower))
            ));
        const totalCount = filtered.length;
        const start = (pg - 1) * pageSize;
        const end = start + pageSize;
        setEntities(filtered.slice(start, end));
        setTotal(totalCount);
        setPage(pg);
    }, [allEntities, pageSize]);

    // Define fetchAllEntities second (depends on filterAndPaginate)
    const fetchAllEntities = useCallback(async () => {
        setLoading(true);
        try {
            let collected = [];
            let pageNum = 1;
            let totalCount = null;
            while (true) {
                const params = { page: pageNum, page_size: 100 };
                if (entityType === 'assay' && parentId) {
                    params.study_id = parentId;
                }
                if (entityType === 'assay' && pipelineId) {
                    params.pipeline = pipelineId;
                }
                let endpoint = `${apiBase}/studies/`;
                if (entityType === 'assay') endpoint = `${apiBase}/assays/`;
                if (entityType === 'pipeline') endpoint = `${apiBase}/pipelines/`;
                if (entityType === 'assembly') endpoint = `${apiBase}/assemblies/`;
                
                console.log(`Fetching ${entityType}s with params:`, params);
                const resp = await axios.get(endpoint, { params });
                const data = resp.data || {};
                let batch = Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : [];
                totalCount = typeof data.count === 'number' ? data.count : null;
                console.log(`Received ${batch.length} ${entityType}s`);
                if (batch.length === 0) break;
                collected = collected.concat(batch);
                if (totalCount !== null && collected.length >= totalCount) break;
                pageNum += 1;
            }
            setAllEntities(collected);
            setLoading(false);
            filterAndPaginate(1, '', collected);
        } catch (err) {
            console.error(`Failed to fetch ${entityType}s`, err);
            setAllEntities([]);
            setEntities([]);
            setTotal(0);
            setLoading(false);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [entityType, parentId, pipelineId, apiBase]);

    // Now the useEffect hooks can safely use these functions
    useEffect(() => {
        if (open) {
            console.log(`Opening ${entityType} dialog`);
            setIsClosing(false);
            setJustOpened(true);
            setCurrentStep(getInitialStep());
            fetchAllEntities();
            // Prevent immediate close from backdrop click after opening
            const timer = setTimeout(() => {
                console.log(`${entityType} dialog protection window ended`);
                setJustOpened(false);
            }, 500); // Increased from 300ms to 500ms
            return () => clearTimeout(timer);
        } else {
            // Reset state when dialog closes
            setJustOpened(false);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, parentId, entityType]);

    useEffect(() => {
        if (entityType === 'assay' && (parentId || pipelineId)) {
            setNewEntity(prev => ({ 
                ...prev, 
                study_id: parentId,
                pipeline: pipelineId || prev.pipeline
            }));
        }
    }, [parentId, pipelineId, entityType]);

    // Refetch entities when step changes in step guide mode
    useEffect(() => {
        if (open && showStepGuide) {
            setSearch('');
            setPage(1);
            fetchAllEntities();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentStep, showStepGuide, open]);

    // Update step progress when selections change
    useEffect(() => {
        if (showStepGuide) {
            setStepProgress(prev => ({
                ...prev,
                study: selectedStudy,
                pipeline: selectedPipeline,
                assay: selectedAssay
            }));
        }
    }, [selectedStudy, selectedPipeline, selectedAssay, showStepGuide]);

    useEffect(() => {
        if (!open) return;
        filterAndPaginate(1, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [search, open, allEntities]);

    const handlePage = (newPage) => {
        if (newPage < 1) return;
        const maxPage = Math.max(1, Math.ceil(total / pageSize));
        if (newPage > maxPage) return;
        filterAndPaginate(newPage, search);
    };

    const handleAdd = () => setAddDialogOpen(true);
    const closeAddDialog = () => {
        setAddDialogOpen(false);
        // Reset form
        setNewEntity({
            name: '',
            ...(entityType === 'assembly' 
                ? { version: '', species: '' }
                : { external_id: '', external_repo: '', description: '', note: '' }
            ),
            ...(entityType === 'assay' ? { 
                type: '', 
                target: '',
                tissue: '',
                cell_type: '',
                treatment: '', 
                date: '',
                platform: '',
                kit: '',
                availability: true,
                study_id: parentId,
                pipeline: pipelineId || 1
            } : {}),
            ...(entityType === 'pipeline' ? {} : {})
        });
    };

    const handleAddSubmit = async () => {
        if (entityType === 'assembly') {
            if (!newEntity.name) {
                setSnackMessage('Please provide a name for the assembly.');
                setSnackSeverity('error');
                setSnackOpen(true);
                return;
            }
        } else if (entityType === 'assay') {
            if (!newEntity.name && !newEntity.external_id) {
                setSnackMessage('Please provide at least a name or external ID.');
                setSnackSeverity('error');
                setSnackOpen(true);
                return;
            }
            if (!newEntity.external_id) {
                setSnackMessage('External ID is required for assays.');
                setSnackSeverity('error');
                setSnackOpen(true);
                return;
            }
        } else {
            if (!newEntity.name && !newEntity.external_id) {
                setSnackMessage('Please provide at least a name or external ID.');
                setSnackSeverity('error');
                setSnackOpen(true);
                return;
            }
        }
        if (entityType === 'pipeline' && !newEntity.external_url) {
            setSnackMessage('External URL is required for pipelines.');
            setSnackSeverity('error');
            setSnackOpen(true);
            return;
        }
        if (entityType === 'assay') {
            if (!newEntity.type || !newEntity.treatment || !newEntity.platform || !newEntity.kit) {
                setSnackMessage('Please provide type, treatment, platform, and kit for the assay.');
                setSnackSeverity('error');
                setSnackOpen(true);
                return;
            }
        }
        if (entityType === 'assembly') {
            if (!newEntity.version) {
                setSnackMessage('Please provide a version for the assembly.');
                setSnackSeverity('error');
                setSnackOpen(true);
                return;
            }
        }
        try {
            setLoading(true);
            let payload;
            if (entityType === 'assembly') {
                payload = { name: newEntity.name, version: newEntity.version, species: newEntity.species };
            } else {
                payload = { ...newEntity };
            }
            if (entityType === 'assay' && parentId) {
                payload.study_id = parentId;
            }
            // Use the correct endpoint based on entity type
            let endpoint;
            if (entityType === 'study') {
                endpoint = `${apiBase}/studies/`;
            } else if (entityType === 'pipeline') {
                endpoint = `${apiBase}/pipelines/`;
            } else if (entityType === 'assay') {
                endpoint = `${apiBase}/studies/${parentId}/assays/`;
            } else if (entityType === 'assembly') {
                endpoint = `${apiBase}/assemblies/`;
            }
            const resp = await axios.post(endpoint, payload);
            const created = resp.data;
            setSnackMessage(`${entityType.charAt(0).toUpperCase() + entityType.slice(1)} created successfully.`);
            setSnackSeverity('success');
            setSnackOpen(true);
            setAddDialogOpen(false);
            onCreate?.(created);
            fetchAllEntities();
        } catch (err) {
            console.error(`Failed to create ${entityType}`, err);
            setSnackMessage(err.response?.data?.error || `Failed to create ${entityType}`);
            setSnackSeverity('error');
            setSnackOpen(true);
        } finally {
            setLoading(false);
        }
    };

    const handleSnackClose = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackOpen(false);
    };

    const handleCancelClick = (event, reason) => {
        // Prevent closing immediately after opening (debounce against accidental backdrop clicks)
        if (justOpened) {
            console.log('Dialog just opened, ignoring close request. Reason:', reason);
            // Prevent the event from bubbling
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return;
        }
        
        // If confirmation dialog is already open, don't process
        if (cancelConfirmOpen) return;
        
        // Prevent double-triggering during close
        if (isClosing) {
            onClose();
            return;
        }
        
        // Show confirmation dialog if any selections have been made
        if (showStepGuide && (stepProgress.study || stepProgress.pipeline)) {
            setCancelConfirmOpen(true);
        } else {
            // No selections, close immediately
            console.log('Closing dialog');
            onClose();
        }
    };

    const handleConfirmCancel = () => {
        // Clear all selections WITHOUT notifying parent (don't call onStudyChange/onPipelineChange)
        // because parent will reopen dialogs thinking we're doing a "back" action
        setIsClosing(true);
        setCancelConfirmOpen(false);
        setStepProgress({ study: null, pipeline: null, assay: null });
        setCurrentStep(getInitialStep());
        // Just close without calling the change callbacks
        onClose();
    };

    const handleCancelAbort = () => {
        // User changed their mind, keep dialog open
        setCancelConfirmOpen(false);
    };

    const handleStepBack = (stepNum) => {
        // Going back in the flow means closing this dialog and reopening the previous one
        // The parent component (ImportIndividual) manages which dialog is open
        
        if (stepNum === 0) {
            // Going back to study - clear pipeline, assay, and assembly selections
            onStudyChange?.(null);
            onPipelineChange?.(null);
            onAssayChange?.(null);
            // Note: Parent should reopen study dialog
        } else if (stepNum === 1) {
            // Going back to pipeline - keep study but clear pipeline, assay, and assembly
            onPipelineChange?.(null);
            onAssayChange?.(null);
            // Note: Parent should reopen pipeline dialog
        } else if (stepNum === 2) {
            // Going back to assay - keep study and pipeline but clear assay and assembly
            onAssayChange?.(null);
            // Note: Parent should reopen assay dialog
        }
        
        // Close the current dialog
        onClose();
    };

    const handleStepSelect = (entity, stepNum) => {
        // Update progress for current step
        if (stepNum === 0) {
            setStepProgress(prev => ({ ...prev, study: entity, pipeline: null, assay: null, assembly: null }));
            onStudyChange?.(entity);
            onPipelineChange?.(null);
            onAssayChange?.(null);
        } else if (stepNum === 1) {
            setStepProgress(prev => ({ ...prev, pipeline: entity, assay: null, assembly: null }));
            onPipelineChange?.(entity);
            onAssayChange?.(null);
        } else if (stepNum === 2) {
            setStepProgress(prev => ({ ...prev, assay: entity, assembly: null }));
            onAssayChange?.(entity);
        } else if (stepNum === 3) {
            setStepProgress(prev => ({ ...prev, assembly: entity }));
        }
        
        // For step guide mode: always call onSelect and close to move to next dialog
        if (showStepGuide) {
            onSelect(entity);
            onClose();
        } else if (stepNum < 3) {
            // Non-step-guide mode: if not the last step, just update progress
            setCurrentStep(stepNum + 1);
        } else {
            // Last step - call onSelect and close
            onSelect(entity);
            onClose();
        }
    };

    return (
        <>
            <Dialog 
                open={open} 
                onClose={handleCancelClick} 
                maxWidth="md" 
                fullWidth
                disableEscapeKeyDown={justOpened}
            >
                <DialogTitle>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#388e3c' }}>
                            {showStepGuide ? 'Data Import Wizard' : `Select or Add ${entityType.charAt(0).toUpperCase() + entityType.slice(1)}`}
                        </Typography>
                        <Button
                            variant="outlined"
                            color="error"
                            onClick={handleCancelClick}
                            sx={{ textTransform: 'none' }}
                        >
                            Cancel
                        </Button>
                    </Box>
                </DialogTitle>
                <DialogContent dividers>
                    {/* Step Guide */}
                    {showStepGuide && (
                        <Box sx={{ mb: 3 }}>
                            <Stepper activeStep={currentStep} sx={{ mb: 2 }}>
                                <Step completed={stepProgress.study !== null}>
                                    <StepLabel>Study</StepLabel>
                                </Step>
                                <Step completed={stepProgress.pipeline !== null}>
                                    <StepLabel>Pipeline</StepLabel>
                                </Step>
                                <Step completed={stepProgress.assay !== null}>
                                    <StepLabel>Assay</StepLabel>
                                </Step>
                                <Step completed={stepProgress.assembly !== null}>
                                    <StepLabel>Assembly</StepLabel>
                                </Step>
                            </Stepper>
                            {stepProgress.study && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Study:</strong> {stepProgress.study.name}
                                    </Typography>
                                </Paper>
                            )}
                            {stepProgress.pipeline && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Pipeline:</strong> {stepProgress.pipeline.name}
                                    </Typography>
                                </Paper>
                            )}
                            {stepProgress.assay && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Assay:</strong> {stepProgress.assay.name}
                                    </Typography>
                                </Paper>
                            )}
                            {stepProgress.assembly && (
                                <Paper sx={{ p: 2, mb: 2, backgroundColor: '#f0f8f5', borderLeft: '4px solid #388e3c' }}>
                                    <Typography variant="body2" sx={{ color: '#666' }}>
                                        <strong>Selected Assembly:</strong> {stepProgress.assembly.name}
                                    </Typography>
                                </Paper>
                            )}
                        </Box>
                    )}

                    {loading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                            <CircularProgress size={60} />
                        </Box>
                    ) : (
                        <>
                            <Typography variant="body1" sx={{ mb: 3, color: '#666' }}>
                                {showStepGuide 
                                    ? (currentStep === 0 ? 'Select a study' : currentStep === 1 ? 'Select a pipeline' : currentStep === 2 ? 'Select an assay' : 'Select an assembly')
                                    : `Select an existing ${entityType} or add a new one.`
                                }
                            </Typography>
                            <TextField
                                fullWidth
                                variant="outlined"
                                placeholder={`Search for a ${entityType} by its name, ID, external ID, or description...`}
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                sx={{ mb: 3 }}
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <SearchIcon />
                                        </InputAdornment>
                                    ),
                                }}
                            />
                            <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
                                {entities.length === 0 ? (
                                    <Typography sx={{ textAlign: 'center', color: '#999', p: 2 }}>
                                        Could not retrieve any {entityType}
                                    </Typography>
                                ) : (
                                    entities.map(entity => (
                                        <Paper
                                            key={entity.id}
                                            elevation={1}
                                            sx={{
                                                p: 2,
                                                mb: 2,
                                                cursor: 'pointer',
                                                transition: 'all 0.2s',
                                                '&:hover': {
                                                    elevation: 4,
                                                    transform: 'translateY(-2px)',
                                                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                                                }
                                            }}
                                            onClick={() => { 
                                                if (showStepGuide) {
                                                    handleStepSelect(entity, currentStep);
                                                } else {
                                                    onSelect(entity); 
                                                    onClose(); 
                                                }
                                            }}
                                        >
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                                <Box sx={{ flexGrow: 1 }}>
                                                    <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#2e7031' }}>
                                                        {entity.name || entity.external_id}
                                                    </Typography>
                                                    {entity.description && (
                                                        <Typography variant="body2" sx={{ color: '#666', mt: 0.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                                            {entity.description}
                                                        </Typography>
                                                    )}
                                                    <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                                                        <Chip label={`ID: ${entity.id}`} size="small" />
                                                        {entity.external_id && (
                                                            <Chip label={`External: ${entity.external_id}`} size="small" />
                                                        )}
                                                        {entityType === 'assay' && entity.type && (
                                                            <Chip label={entity.type} size="small" color="primary" />
                                                        )}
                                                        {entityType === 'assembly' && entity.version && (
                                                            <Chip label={`Version: ${entity.version}`} size="small" color="primary" />
                                                        )}
                                                        {entityType === 'assembly' && entity.species && (
                                                            <Chip label={`Species: ${entity.species}`} size="small" />
                                                        )}
                                                    </Box>
                                                </Box>
                                                <Button 
                                                    variant="contained" 
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        if (showStepGuide) {
                                                            handleStepSelect(entity, currentStep);
                                                        } else {
                                                            onSelect(entity);
                                                            onClose();
                                                        }
                                                    }}
                                                    sx={{ textTransform: 'none', backgroundColor: '#2e7031', '&:hover': { backgroundColor: '#276027' } }}
                                                >
                                                    Select
                                                </Button>
                                            </Box>
                                        </Paper>
                                    ))
                                )}
                            </Box>
                            {search && (
                                <Typography variant="caption" sx={{ display: 'block', mt: 2, textAlign: 'center', color: '#666' }}>
                                    Showing {entities.length} of {total} {entityType}s
                                </Typography>
                            )}
                            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 3, gap: 2 }}>
                                <Button variant="outlined" disabled={page <= 1} onClick={() => handlePage(page - 1)}>
                                    Previous
                                </Button>
                                <Typography variant="body2" sx={{ color: '#666' }}>
                                    Page {page} of {Math.max(1, Math.ceil(total / pageSize))}
                                </Typography>
                                <Button variant="outlined" disabled={(page * pageSize) >= total} onClick={() => handlePage(page + 1)}>
                                    Next
                                </Button>
                            </Box>
                            {/* Back button for step guide */}
                            {showStepGuide && currentStep > 0 && (
                                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-start' }}>
                                    <Button 
                                        variant="outlined"
                                        startIcon={<ArrowBackIcon />}
                                        onClick={() => handleStepBack(currentStep - 1)}
                                        sx={{ textTransform: 'none' }}
                                    >
                                        Back to {currentStep === 1 ? 'Study' : currentStep === 2 ? 'Pipeline' : 'Assay'}
                                    </Button>
                                </Box>
                            )}
                            <Box sx={{ mt: 3, textAlign: 'center' }}>
                                <Button 
                                    variant="contained" 
                                    onClick={handleAdd} 
                                    sx={{ 
                                        borderRadius: 3, 
                                        py: 1.5, 
                                        px: 4,
                                        textTransform: 'none', 
                                        fontSize: '1rem', 
                                        fontWeight: 400, 
                                        backgroundColor: '#66bb6a', 
                                        '&:hover': { backgroundColor: '#4caf50' } 
                                    }}
                                >
                                    Add New {entityType.charAt(0).toUpperCase() + entityType.slice(1)}
                                </Button>
                            </Box>
                        </>
                    )}
                </DialogContent>
            </Dialog>
            
            {/* Add new entity dialog */}
            <Dialog open={addDialogOpen} onClose={closeAddDialog} maxWidth="sm" fullWidth>
                <DialogTitle>Add New {entityType.charAt(0).toUpperCase() + entityType.slice(1)}</DialogTitle>
                <DialogContent dividers>
                    <Stack spacing={2} sx={{ py: 1 }}>
                        <TextField 
                            label="Name *" 
                            value={newEntity.name} 
                            onChange={e => setNewEntity({ ...newEntity, name: e.target.value })} 
                            fullWidth 
                        />
                        {entityType === 'pipeline' ? (
                            <TextField 
                                label="External URL *"
                                value={newEntity.external_url} 
                                onChange={e => setNewEntity({ ...newEntity, external_url: e.target.value })} 
                                fullWidth 
                                placeholder='https://workflowhub.eu/...'
                                helperText='URL of external pipeline repository (required)'
                            />
                        ) : entityType !== 'assembly' && (
                            <TextField 
                                label={entityType === 'assay' ? "External ID" : "External ID"}
                                value={newEntity.external_id} 
                                onChange={e => setNewEntity({ ...newEntity, external_id: e.target.value })} 
                                fullWidth 
                                required={entityType === 'assay'}
                            />
                        )}
                        {entityType === 'study' && (
                            <TextField 
                                label="External Repository"
                                value={newEntity.external_repo} 
                                onChange={e => setNewEntity({ ...newEntity, external_repo: e.target.value })} 
                                fullWidth 
                                placeholder="e.g. GEO"
                            />
                        )}
                        {entityType !== 'assembly' && (
                            <TextField 
                                label="Description" 
                                value={newEntity.description} 
                                onChange={e => setNewEntity({ ...newEntity, description: e.target.value })} 
                                multiline 
                                rows={3} 
                                fullWidth 
                            />
                        )}
                        {allowNotes && (
                            <TextField 
                                label="Note" 
                                value={newEntity.note} 
                                onChange={e => setNewEntity({ ...newEntity, note: e.target.value })} 
                                multiline 
                                rows={2} 
                                fullWidth 
                                placeholder={`Add any additional notes about this ${entityType}...`} 
                            />
                        )}
                        {entityType === 'assay' && (
                            <>
                                <TextField 
                                    label="Type *" 
                                    value={newEntity.type} 
                                    onChange={e => setNewEntity({ ...newEntity, type: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., ChIP-Seq, RNA-Seq, ATAC-Seq"
                                />
                                <TextField 
                                    label="Treatment *" 
                                    value={newEntity.treatment} 
                                    onChange={e => setNewEntity({ ...newEntity, treatment: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., untreated, drug X"
                                />
                                <TextField 
                                    label="Platform *" 
                                    value={newEntity.platform} 
                                    onChange={e => setNewEntity({ ...newEntity, platform: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., Illumina NextSeq 2000"
                                />
                                <TextField 
                                    label="Kit *" 
                                    value={newEntity.kit || ''} 
                                    onChange={e => setNewEntity({ ...newEntity, kit: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., TruSeq ChIP Library Preparation Kit"
                                />
                                <TextField 
                                    label="Target" 
                                    value={newEntity.target || ''} 
                                    onChange={e => setNewEntity({ ...newEntity, target: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., GATA3 (for ChIP-Seq)"
                                />
                                <TextField 
                                    label="Tissue" 
                                    value={newEntity.tissue || ''} 
                                    onChange={e => setNewEntity({ ...newEntity, tissue: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., peripheral blood"
                                />
                                <TextField 
                                    label="Cell Type" 
                                    value={newEntity.cell_type || ''} 
                                    onChange={e => setNewEntity({ ...newEntity, cell_type: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., macrophages"
                                />
                                <TextField 
                                    label="Date" 
                                    type="date"
                                    value={newEntity.date || ''} 
                                    onChange={e => setNewEntity({ ...newEntity, date: e.target.value })} 
                                    fullWidth 
                                    InputLabelProps={{ shrink: true }}
                                    placeholder="2024-03-17"
                                />
                            </>
                        )}
                        {entityType === 'assembly' && (
                            <>
                                <TextField 
                                    label="Version *" 
                                    value={newEntity.version} 
                                    onChange={e => setNewEntity({ ...newEntity, version: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., GRCh38, GRCm39"
                                />
                                <TextField 
                                    label="Species" 
                                    value={newEntity.species || ''} 
                                    onChange={e => setNewEntity({ ...newEntity, species: e.target.value })} 
                                    fullWidth 
                                    placeholder="e.g., hsa, mmu"
                                />
                            </>
                        )}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeAddDialog} disabled={loading}>Cancel</Button>
                    <Button onClick={handleAddSubmit} variant="contained" disabled={loading}>
                        {loading ? 'Creating...' : 'Create'}
                    </Button>
                </DialogActions>
            </Dialog>
            
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

            {/* Cancel confirmation dialog */}
            <Dialog open={cancelConfirmOpen} onClose={handleCancelAbort} disableEscapeKeyDown>
                <DialogTitle>Cancel Selection?</DialogTitle>
                <DialogContent>
                    <Typography>
                        You have made selections for {stepProgress.study ? 'Study' : ''}{stepProgress.study && stepProgress.pipeline ? ', Pipeline' : stepProgress.pipeline ? 'Pipeline' : ''}.
                        {(stepProgress.study || stepProgress.pipeline) && ' '}
                        Are you sure you want to cancel and lose all progress?
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCancelAbort} variant="contained">
                        Keep Selecting
                    </Button>
                    <Button onClick={handleConfirmCancel} variant="outlined" color="error">
                        Cancel & Clear All
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
}
