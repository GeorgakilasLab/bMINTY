// src/components/StudyFormModal.jsx
import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Tooltip
} from '@mui/material';

/**
 * Reusable modal for creating or editing a study.
 *
 * Props:
 * - open: boolean
 * - study: object|null  (if null, we're adding; otherwise editing)
 * - onSave: fn(formData)
 * - onCancel: fn()
 */
export default function StudyFormModal({ open, study, onSave, onCancel }) {
  const isEdit = Boolean(study);
  const [formState, setFormState] = useState({
    external_id: '',
    external_repo: '',
    name: '',
    description: '',
    note: ''
  });

  // Initialize or reset form when modal opens or study changes
  useEffect(() => {
    if (open) {
      if (isEdit) {
        setFormState({
          external_id: study.external_id || '',
          external_repo: study.external_repo || '',
          name: study.name || '',
          description: study.description || '',
          note: study.note || ''
        });
      } else {
        setFormState({ external_id: '', external_repo: '', name: '', description: '', note: '' });
      }
    }
  }, [open, isEdit, study]);

  const handleChange = e => {
    const { name, value } = e.target;
    setFormState(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = () => {
    onSave(formState); // includes note
  };

  const isDisabled = !formState.external_id || !formState.name || !formState.description;

  return (
    <Dialog open={open} onClose={onCancel} fullWidth maxWidth="md">
      <DialogTitle>{isEdit ? 'Modify Study' : 'Add New Study'}</DialogTitle>
      <DialogContent>
        <TextField
          label="External ID"
          name="external_id"
          fullWidth
          margin="normal"
          value={formState.external_id}
          onChange={handleChange}
          required
          InputProps={{ readOnly: isEdit }}
        />
        {isEdit && (
          <Tooltip title="External ID cannot be modified" arrow>
            <span style={{ display: 'block', color: 'gray', fontSize: '12px' }}>
              External ID is read-only
            </span>
          </Tooltip>
        )}
        <TextField
          label="External Repository"
          name="external_repo"
          fullWidth
          margin="normal"
          value={formState.external_repo}
          onChange={handleChange}
          placeholder="e.g. GEO"
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
          label="Description"
          name="description"
          fullWidth
          margin="normal"
          value={formState.description}
          onChange={handleChange}
          required
          multiline
          minRows={2}
        />
        {/* NEW: Note (editable here instead of in table) */}
        <TextField
          label="Note"
          name="note"
          fullWidth
          margin="normal"
          value={formState.note}
          onChange={handleChange}
          multiline
          minRows={3}
          placeholder="Add any notes about this study…"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSubmit} disabled={isDisabled} variant="contained">
          {isEdit ? 'Modify' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
