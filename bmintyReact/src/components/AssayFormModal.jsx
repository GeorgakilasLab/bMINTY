// src/components/AssayFormModal.jsx
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Tooltip,
  Autocomplete
} from '@mui/material';

/**
 * Reusable modal for editing an assay.
 *
 * Props:
 * - open: boolean
 * - assay: object|null  (required - only used for editing)
 * - studies: array (list of available studies for reassignment)
 * - currentStudyId: number (the study the assay currently belongs to)
 * - onSave: fn(formData)
 * - onCancel: fn()
 */
export default function AssayFormModal({ open, assay, studies = [], currentStudyId, onSave, onCancel }) {
  const [formState, setFormState] = useState({
    external_id: '',
    name: '',
    type: '',
    tissue: '',
    cell_type: '',
    treatment: '',
    platform: '',
    kit: '',
    target: '',
    date: '',
    description: '',
    note: '',
    study: null
  });

  const [searchText, setSearchText] = useState('');
  const [selectedStudy, setSelectedStudy] = useState(null);

  const filterOptions = (options, { inputValue }) => {
    const query = (inputValue || '').toLowerCase();
    const filtered = options
      .filter(study =>
        study.external_id?.toLowerCase().includes(query) ||
        study.name?.toLowerCase().includes(query)
      )
      .slice(0, 5);

    if (selectedStudy && !filtered.some(study => study.id === selectedStudy.id)) {
      return [selectedStudy, ...filtered];
    }

    return filtered;
  };

  // Initialize form when modal opens or assay changes
  useEffect(() => {
    if (open && assay) {
      setFormState({
        external_id: assay.external_id || '',
        name: assay.name || '',
        type: assay.type || '',
        tissue: assay.tissue || '',
        cell_type: assay.cell_type || '',
        treatment: assay.treatment || '',
        platform: assay.platform || '',
        kit: assay.kit || '',
        target: assay.target || '',
        date: assay.date || '',
        description: assay.description || '',
        note: assay.note || '',
        study: currentStudyId || null
      });
      // Set the selected study based on currentStudyId
      const currentStudy = studies.find(s => s.id === currentStudyId);
      setSelectedStudy(currentStudy || null);
      setSearchText('');
    }
  }, [open, assay, currentStudyId, studies]);

  const handleChange = e => {
    const { name, value } = e.target;
    setFormState(prev => ({ ...prev, [name]: value }));
  };

  const handleStudyChange = (event, value) => {
    setSelectedStudy(value);
    setFormState(prev => ({ ...prev, study: value?.id || null }));
  };

  const handleSubmit = () => {
    // Don't include external_id or internal id in the submission
    const { external_id, ...editableFields } = formState;
    onSave(editableFields);
  };

  // Require at least name, type, and platform
  const isDisabled = !formState.name || !formState.type || !formState.platform;

  return (
    <Dialog open={open} onClose={onCancel} fullWidth maxWidth="md">
      <DialogTitle>Modify Assay</DialogTitle>
      <DialogContent>
        <TextField
          label="External ID"
          name="external_id"
          fullWidth
          margin="normal"
          value={formState.external_id}
          disabled
          InputProps={{ readOnly: true }}
        />
        <Tooltip title="External ID cannot be modified" arrow>
          <span style={{ display: 'block', color: 'gray', fontSize: '12px', marginBottom: '12px' }}>
            External ID is read-only
          </span>
        </Tooltip>

        <Autocomplete
          options={studies}
          filterOptions={filterOptions}
          getOptionLabel={(option) => `${option.name}`}
          value={selectedStudy}
          onChange={handleStudyChange}
          inputValue={searchText}
          onInputChange={(event, newInputValue) => setSearchText(newInputValue)}
          isOptionEqualToValue={(option, value) => option?.id === value?.id}
          openOnFocus
          fullWidth
          margin="normal"
          renderInput={(params) => (
            <TextField
              {...params}
              label="Study"
              placeholder="Search by ID or name..."
              required
              margin="normal"
            />
          )}
          noOptionsText="No studies found"
          ListboxProps={{
            style: { maxHeight: '200px' }
          }}
        />

        <TextField
          label="Name"
          name="name"
          fullWidth
          margin="normal"
          value={formState.name}
          onChange={handleChange}
          required
        />

        <TextField
          label="Type"
          name="type"
          fullWidth
          margin="normal"
          value={formState.type}
          onChange={handleChange}
          required
        />

        <TextField
          label="Tissue"
          name="tissue"
          fullWidth
          margin="normal"
          value={formState.tissue}
          onChange={handleChange}
          placeholder="e.g. Lung"
        />

        <TextField
          label="Cell Type"
          name="cell_type"
          fullWidth
          margin="normal"
          value={formState.cell_type}
          onChange={handleChange}
          placeholder="e.g. T cell"
        />

        <TextField
          label="Treatment"
          name="treatment"
          fullWidth
          margin="normal"
          value={formState.treatment}
          onChange={handleChange}
          multiline
          minRows={2}
          placeholder="e.g. untreated, vehicle control"
        />

        <TextField
          label="Platform"
          name="platform"
          fullWidth
          margin="normal"
          value={formState.platform}
          onChange={handleChange}
          required
          placeholder="e.g. Illumina NovaSeq, 10x Genomics"
        />

        <TextField
          label="Kit"
          name="kit"
          fullWidth
          margin="normal"
          value={formState.kit}
          onChange={handleChange}
          placeholder="e.g. NextSeq 500/550"
        />

        <TextField
          label="Target"
          name="target"
          fullWidth
          margin="normal"
          value={formState.target}
          onChange={handleChange}
          placeholder="e.g. Open chromatin"
        />

        <TextField
          label="Date"
          name="date"
          type="date"
          fullWidth
          margin="normal"
          value={formState.date}
          onChange={handleChange}
          InputLabelProps={{ shrink: true }}
        />

        <TextField
          label="Description"
          name="description"
          fullWidth
          margin="normal"
          value={formState.description}
          onChange={handleChange}
          multiline
          minRows={2}
          placeholder="Add a description of this assay…"
        />

        <TextField
          label="Note"
          name="note"
          fullWidth
          margin="normal"
          value={formState.note}
          onChange={handleChange}
          multiline
          minRows={3}
          placeholder="Add any notes about this assay…"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSubmit} disabled={isDisabled} variant="contained">
          Modify
        </Button>
      </DialogActions>
    </Dialog>
  );
}
