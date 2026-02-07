import React from 'react';
import { Box, Chip, Typography } from '@mui/material';
import ClearIcon from '@mui/icons-material/Clear';

export default function AppliedFilters({ filters, onFiltersChange }) {
  // Collect all applied filters into a flat list
  const appliedFilters = [];

  // Map of filter keys to display names
  const filterLabels = {
    study_name: 'Study Name',
    study_external_id: 'Study External ID',
    study_repository: 'Repository',
    study_description: 'Study Description',
    study_note: 'Study Note',
    study_availability: 'Study Availability',
    assay_name: 'Assay Name',
    assay_external_id: 'Assay External ID',
    assay_availability: 'Assay Availability',
    assay_type: 'Assay Type',
    assay_target: 'Target',
    assay_date: 'Date',
    assay_kit: 'Kit',
    tissue: 'Tissue',
    assay_description: 'Assay Description',
    assay_note: 'Assay Note',
    assay_cell_type: 'Assay Cell Type',
    cell_type: 'Cell Type',
    cell_label: 'Cell Label',
    treatment: 'Treatment',
    platform: 'Platform',
    interval_type: 'Interval Type',
    biotype: 'Biotype',
    assembly_name: 'Assembly Name',
    assembly_version: 'Assembly Version',
    assembly_species: 'Assembly Species',
    signal_assay_type: 'Signal Assay Type',
  };

  // Helper to format availability filter values
  const formatValue = (key, value) => {
    if (key === 'study_availability' || key === 'assay_availability') {
      return value === 'available' ? 'Available' : value === 'unavailable' ? 'Unavailable' : 'All';
    }
    return value;
  };

  // Collect non-default filters
  Object.keys(filters).forEach((key) => {
    const value = filters[key];
    const label = filterLabels[key];

    // Skip if not in label map or is default/empty
    if (!label) return;

    // Handle array values (multi-select)
    if (Array.isArray(value) && value.length > 0) {
      value.forEach((v) => {
        appliedFilters.push({
          key: `${key}-${v}`,
          label: `${label}: ${v}`,
          filterKey: key,
          filterValue: v,
        });
      });
    }
    // Handle non-default single values
    else if (!Array.isArray(value) && value && value !== 'all') {
      appliedFilters.push({
        key: `${key}-${value}`,
        label: `${label}: ${formatValue(key, value)}`,
        filterKey: key,
        filterValue: value,
      });
    }
  });

  // If no filters applied, show a message
  if (appliedFilters.length === 0) {
    return (
      <Box sx={{ mb: 2 }}>
        {/* <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Applied Filters:
        </Typography> */}
        <Box
          sx={{
            p: 1.5,
            backgroundColor: '#f5f5f5',
            borderRadius: 1,
            border: '1px solid #e0e0e0',
          }}
        >
          <Typography variant="body2" sx={{ color: '#999' }}>
            No filters applied
          </Typography>
        </Box>
      </Box>
    );
  }

  const handleRemoveFilter = (filterKey, filterValue) => {
    const updatedFilters = { ...filters };

    if (Array.isArray(updatedFilters[filterKey])) {
      updatedFilters[filterKey] = updatedFilters[filterKey].filter(
        (v) => v !== filterValue
      );
    } else {
      // Reset to default for non-array values
      if (filterKey === 'study_availability' || filterKey === 'assay_availability') {
        updatedFilters[filterKey] = 'all';
      } else {
        updatedFilters[filterKey] = '';
      }
    }

    onFiltersChange(updatedFilters);
  };

  return (
    <Box sx={{ mb: 2 }}>
      {/* <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
        Applied Filters:
      </Typography> */}
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 1,
          p: 1.5,
          backgroundColor: '#f5f5f5',
          borderRadius: 1,
          border: '1px solid #e0e0e0',
        }}
      >
        {appliedFilters.map((filter) => (
          <Chip
            key={filter.key}
            label={filter.label}
            onDelete={() => handleRemoveFilter(filter.filterKey, filter.filterValue)}
            deleteIcon={<ClearIcon />}
            size="small"
            variant="outlined"
            sx={{
              backgroundColor: '#fff',
              '&:hover': {
                backgroundColor: '#f0f0f0',
              },
            }}
          />
        ))}
      </Box>
    </Box>
  );
}
