import React, { useState, useEffect } from 'react';
import MultiSelectAutocomplete from './MultiSelectAutocomplete';
import axios from 'axios';
import { formatNumber } from '../utils/formatNumber';

import {
  Box,
  Typography,
  Divider,
  Button,
} from '@mui/material';
import FilterSection from './FilterSection';
import AvailabilitySelect from './AvailabilitySelect';
import { API_BASE } from '../config';

export default function FilterPanel({
  filters,
  onFiltersChange,
  orderBy, // Not used in the return block
  orderDir, // Not used in the return block
  onOrderByChange, // Not used in the return block
  onOrderDirToggle, // Not used in the return block
}) {
  const [openSections, setOpenSections] = useState({
    study: false,
    assay: false,
    interval: false,
    cell: false,
    assembly: false,
  });

  const [counts, setCounts] = useState({
    studies: 0,
    assays: 0,
    cells: 0,
    intervals: 0,
    assemblies: 0,
  });

  // API base sourced from environment via config
  
  // Fetch TOTAL counts (without filters) once on mount
  useEffect(() => {
    const fetchTotalCounts = async () => {
      try {
        // Fetch studies count
        const studiesRes = await axios.get(`${API_BASE}/studies/`, { 
          params: { page_size: 1, page: 1 } 
        });

        // Fetch assays count
        const assaysRes = await axios.get(`${API_BASE}/assays/`, { 
          params: { page_size: 1, page: 1 } 
        });

        // Fetch intervals count
        const intervalsRes = await axios.get(`${API_BASE}/intervals/`, { 
          params: { page_size: 1, page: 1 } 
        });

        // Fetch cells count
        const cellsRes = await axios.get(`${API_BASE}/cells/`, {
          params: { page_size: 1, page: 1 }
        });

        // Fetch assemblies count
        const assembliesRes = await axios.get(`${API_BASE}/assemblies/`, { 
          params: { page_size: 1, page: 1 } 
        });

        setCounts({
          studies: studiesRes.data.count || 0,
          assays: assaysRes.data.count || 0,
          cells: cellsRes.data.count || 0,
          intervals: intervalsRes.data.count || 0,
          assemblies: assembliesRes.data.count || 0,
        });
      } catch (err) {
        console.error('Error fetching total counts:', err);
      }
    };

    fetchTotalCounts();
  }, []); // Empty dependency array - fetch only once on mount
  
  
  // Helper to ensure filter values are arrays for multi-select fields
  const getFilterArray = (fieldName) => {
    const val = filters[fieldName];
    if (Array.isArray(val)) return val;
    if (val && typeof val === 'string') return val.split(',').filter(x => x);
    return [];
  };

  const toggleSection = (name) => {
    setOpenSections((prev) => {
      // If clicking the same section, toggle it off
      if (prev[name]) {
        return { ...prev, [name]: false };
      }
      // If clicking a different section, close all others and open this one
      return {
        study: false,
        assay: false,
        interval: false,
        cell: false,
        assembly: false,
        [name]: true
      };
    });
  };

  const handleSelectChange = (e) => {
    const { name, value } = e.target;
    onFiltersChange({ ...filters, [name]: value });
  };

  const handleResetFilters = () => {
    const defaultFilters = {
      study_name: [],
      study_external_id: [],
      study_repository: [],
      study_description: [],
      study_note: [],
      study_availability: 'available',
      assay_name: [],
      assay_external_id: [],
      assay_availability: 'all',
      assay_type: [],
      assay_target: [],
      assay_date: [],
      assay_kit: [],
      tissue: [],
      assay_description: [],
      assay_note: [],
      assay_cell_type: [],
      cell_type: [],
      cell_label: [],
      treatment: [],
      platform: [],
      interval_type: [],
      biotype: [],
      assembly_name: [],
      assembly_version: [],
      assembly_species: [],
      signal_assay_type: [],
    };
    onFiltersChange(defaultFilters);
  };
  
  // Helper to handle multi-select changes
  const handleMultiSelectChange = (fieldName, newValues) => {
    onFiltersChange({ ...filters, [fieldName]: newValues });
  };

  return (
    // The main container needs to support flex layout for auto margin to work
    // and defines the total height the panel takes up.
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
      <Typography 
        variant="h5"
        sx={{ mb: 1 }}
      >
        Filters
      </Typography>

      {/* ------------------------------------------------------------------ */}
      {/* SCROLLABLE FILTER SECTIONS CONTAINER                               */}
      {/* This box is where the scrolling occurs. Set a maximum height and overflow. */}
      <Box 
        sx={{ 
          overflowY: 'auto', 
          maxHeight: 'calc(100vh - 200px)', 
          pr: 1, // Add right padding to accommodate the scrollbar and prevent content overlap
          pb: 8, // Add padding at bottom to prevent content from being hidden under the button
        }}
      >
        {/* Study */}
        <FilterSection
          title={<span>Study <span style={{ fontSize: '0.75rem', color: '#999' }}>({formatNumber(counts.studies)})</span></span>}
          open={openSections.study}
          onToggle={() => toggleSection('study')}
        >
          <MultiSelectAutocomplete
            name="study_name"
            label="Study Name"
            values={getFilterArray('study_name')}
            onChange={(newVals) => handleMultiSelectChange('study_name', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="study_external_id"
            label="Study External ID"
            values={getFilterArray('study_external_id')}
            onChange={(newVals) => handleMultiSelectChange('study_external_id', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="study_repository"
            label="Repository"
            values={getFilterArray('study_repository')}
            onChange={(newVals) => handleMultiSelectChange('study_repository', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="study_description"
            label="Description"
            values={getFilterArray('study_description')}
            onChange={(newVals) => handleMultiSelectChange('study_description', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="study_note"
            label="Note"
            values={getFilterArray('study_note')}
            onChange={(newVals) => handleMultiSelectChange('study_note', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <AvailabilitySelect
            name="study_availability"
            value={filters.study_availability}
            onChange={handleSelectChange}
          />
        </FilterSection>
        <Divider sx={{ my: 2 }} />

        {/* Assay */}
        <FilterSection
          title={<span>Assay <span style={{ fontSize: '0.75rem', color: '#999' }}>({formatNumber(counts.assays)})</span></span>}
          open={openSections.assay}
          onToggle={() => toggleSection('assay')}
        >
          <MultiSelectAutocomplete
            name="assay_name"
            label="Assay Name"
            values={getFilterArray('assay_name')}
            onChange={(newVals) => handleMultiSelectChange('assay_name', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_external_id"
            label="Assay External ID"
            values={getFilterArray('assay_external_id')}
            onChange={(newVals) => handleMultiSelectChange('assay_external_id', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_type"
            label="Assay Type"
            values={getFilterArray('assay_type')}
            onChange={(newVals) => handleMultiSelectChange('assay_type', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="tissue"
            label="Tissue"
            values={getFilterArray('tissue')}
            onChange={(newVals) => handleMultiSelectChange('tissue', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_cell_type"
            label="Cell Type"
            values={getFilterArray('assay_cell_type')}
            onChange={(newVals) => handleMultiSelectChange('assay_cell_type', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="treatment"
            label="Treatment"
            values={getFilterArray('treatment')}
            onChange={(newVals) => handleMultiSelectChange('treatment', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="platform"
            label="Platform"
            values={getFilterArray('platform')}
            onChange={(newVals) => handleMultiSelectChange('platform', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_note"
            label="Note"
            values={getFilterArray('assay_note')}
            onChange={(newVals) => handleMultiSelectChange('assay_note', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_target"
            label="Target"
            values={getFilterArray('assay_target')}
            onChange={(newVals) => handleMultiSelectChange('assay_target', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_date"
            label="Date"
            values={getFilterArray('assay_date')}
            onChange={(newVals) => handleMultiSelectChange('assay_date', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_kit"
            label="Kit"
            values={getFilterArray('assay_kit')}
            onChange={(newVals) => handleMultiSelectChange('assay_kit', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assay_description"
            label="Description"
            values={getFilterArray('assay_description')}
            onChange={(newVals) => handleMultiSelectChange('assay_description', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />

          <AvailabilitySelect
            name="assay_availability"
            value={filters.assay_availability}
            onChange={handleSelectChange}
          />
        </FilterSection>
        <Divider sx={{ my: 2 }} />

        {/* Cell */}
        <FilterSection
          title={<span>Cell <span style={{ fontSize: '0.75rem', color: '#999' }}>({formatNumber(counts.cells)})</span></span>}
          open={openSections.cell}
          onToggle={() => toggleSection('cell')}
        >
          <MultiSelectAutocomplete
            name="cell_type"
            label="Type"
            values={getFilterArray('cell_type')}
            onChange={(newVals) => handleMultiSelectChange('cell_type', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />

          <MultiSelectAutocomplete
            name="cell_label"
            label="Label"
            values={getFilterArray('cell_label')}
            onChange={(newVals) => handleMultiSelectChange('cell_label', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
        </FilterSection>
        <Divider sx={{ my: 2 }} />

        {/* Interval */}
        <FilterSection
          title={<span>Interval <span style={{ fontSize: '0.75rem', color: '#999' }}>({formatNumber(counts.intervals)})</span></span>}
          open={openSections.interval}
          onToggle={() => toggleSection('interval')}
        >
          <MultiSelectAutocomplete
            name="interval_type"
            label="Interval Type"
            values={getFilterArray('interval_type')}
            onChange={(newVals) => handleMultiSelectChange('interval_type', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />

          <MultiSelectAutocomplete
            name="biotype"
            label="Biotype"
            values={getFilterArray('biotype')}
            onChange={(newVals) => handleMultiSelectChange('biotype', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
            
        </FilterSection>
        <Divider sx={{ my: 2 }} />

        {/* Assembly */}
        <FilterSection
          title={<span>Assembly <span style={{ fontSize: '0.75rem', color: '#999' }}>({formatNumber(counts.assemblies)})</span></span>}
          open={openSections.assembly}
          onToggle={() => toggleSection('assembly')}
        >
          <MultiSelectAutocomplete
            name="assembly_name"
            label="Assembly Name"
            values={getFilterArray('assembly_name')}
            onChange={(newVals) => handleMultiSelectChange('assembly_name', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
          <MultiSelectAutocomplete
            name="assembly_version"
            label="Assembly Version"
            values={getFilterArray('assembly_version')}
            onChange={(newVals) => handleMultiSelectChange('assembly_version', newVals)}
            apiBase={API_BASE}
            currentFilters={filters}
          />
        </FilterSection>
      </Box>
      
      {/* ------------------------------------------------------------------ */}
      {/* FIXED RESET FILTERS BUTTON                                         */}
      {/* This box is outside the scrollable area. mt: 'auto' pushes it to the bottom. */}
      <Box sx={{ mt: 'auto', mb: 2 }}>
        <Button 
          variant="contained" 
          color="success" 
          size="large"

          fullWidth
          onClick={handleResetFilters}
        >
          Reset Filters
        </Button>
      </Box>
    </Box>
  );
}