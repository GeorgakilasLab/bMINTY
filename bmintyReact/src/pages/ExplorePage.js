import React, { useState } from 'react';
import { Box, Paper, IconButton, Tooltip, Typography, Button, Link, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import { ChevronLeft as ChevronLeftIcon, ChevronRight as ChevronRightIcon, GitHub as GitHubIcon, Api as ApiIcon, FileUpload as FileUploadIcon, TableChart as TableChartIcon, Storage as StorageIcon } from '@mui/icons-material';
import { Routes, Route } from 'react-router-dom';
import { useStudies } from '../hooks/useStudies';
import FilterPanel from '../components/FilterPanel';
import AppliedFilters from '../components/AppliedFilters';
import ExploreStudiesTable from '../components/ExploreStudiesTable';
import ImportIndividualTable from '../components/ImportIndividual';
import ImportFullDatabase from '../components/ImportFullDatabase';
import ExportSelectionButton from '../components/ExportSelectionButton';
import { clearAsyncAutocompleteCache } from '../components/AsyncAutocomplete';
import { API_PROTOCOL, API_HOST, API_PORT } from '../config';

export default function ExplorePage() {
  const [showFilters, setShowFilters] = useState(true);
  const [filterWidth, setFilterWidth] = useState(350);
  const [isResizing, setIsResizing] = useState(false);
  const [importMenuAnchor, setImportMenuAnchor] = useState(null);
  const [showIndividualImport, setShowIndividualImport] = useState(false);
  const [showFullDatabaseImport, setShowFullDatabaseImport] = useState(false);

  // Load filters from localStorage if available
  const getInitialFilters = () => {
    try {
      const saved = localStorage.getItem('exploreFilters');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return {
      study_name: [],
      study_external_id: [],
      study_repository: [],
      study_description: [],
      study_note: [],
      study_availability: 'available',
      assay_name: [],
      assay_external_id: [],
      assay_availability: 'available',
      assay_type: [],
      assay_target: [],
      assay_date: [],
      assay_kit: [],
      tissue: [],
      assay_description: [],
      assay_note: [],
      cell_type: [],
      treatment: [],
      platform: [],
      interval_type: [],
      biotype: [],
      assembly_name: [],
      assembly_species: [],
      signal_assay_type: [],
    };
  };

  const {
    studies,
    setStudies,
    totalCount,
    page,
    rowsPerPage,
    filters,
    setFilters,
    orderBy,
    orderDir,
    loading,
    setPage,
    setRowsPerPage,
    setOrderBy,
    setOrderDir,
    fetchStudies,
    cancelRequest,
    onToggleStudyAvailability,
    onAddStudy,
  } = useStudies(getInitialFilters());

  // Persist filters to localStorage on change
  React.useEffect(() => {
    localStorage.setItem('exploreFilters', JSON.stringify(filters));
  }, [filters]);

  // Handle mouse resizing
  const handleMouseDown = (e) => {
    setIsResizing(true);
    e.preventDefault();
  };

  React.useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      
      const newWidth = e.clientX;
      const minWidth = window.innerWidth < 768 ? 250 : 300;
      const maxWidth = Math.min(600, window.innerWidth * 0.5);
      
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        setFilterWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  return (
    <Box display="flex" height="100vh" position="relative">
      {/* Animated collapsible filter drawer */}
      <Box sx={{ height:'100%', position:'relative', display:'flex' }}>
        <Paper
          elevation={3}
          sx={{
            width: showFilters ? filterWidth : 0,
            minWidth: showFilters ? { xs: 250, md: 300 } : 0,
            maxWidth: showFilters ? { xs: '80vw', sm: '50vw', md: 600 } : 0,
            transition: isResizing ? 'none' : 'width 300ms ease',
            height: '100vh',
            p: 0,
            boxSizing: 'border-box',
            display: 'flex',
            flexDirection: 'column',
            bgcolor: showFilters ? '#d2fae0' : 'transparent',
            borderTopRightRadius: 12,
            borderBottomRightRadius: 12,
            position: 'relative',
          }}
        >
          {showFilters && (
            <>
              <Box sx={{ height: '100%', overflowY: 'auto', p: { xs: 2, md: 3 }, pr: { xs: 1.5, md: 2 }, backgroundColor: '#c8e6c9' }}>
                <FilterPanel
                  filters={filters}
                  onFiltersChange={setFilters}
                  orderBy={orderBy}
                  orderDir={orderDir}
                  onOrderByChange={(v) => { setOrderBy(v); setPage(0); }}
                  onOrderDirToggle={() => setOrderDir((d) => (d === 'asc' ? 'desc' : 'asc'))}
                />
              </Box>
              {/* Resize handle */}
              <Box
                onMouseDown={handleMouseDown}
                sx={{
                  position: 'absolute',
                  right: 0,
                  top: 0,
                  bottom: 0,
                  width: 8,
                  cursor: 'ew-resize',
                  backgroundColor: isResizing ? 'rgba(56, 142, 60, 0.3)' : 'transparent',
                  transition: 'background-color 0.2s',
                  '&:hover': {
                    backgroundColor: 'rgba(56, 142, 60, 0.2)',
                  },
                  zIndex: 11,
                }}
              />
            </>
          )}
        </Paper>
        {/* Toggle handle */}
        <Box
          sx={{
            position:'absolute',
            top: 40,
            right: -18,
            zIndex: 10
          }}
        >
          <Tooltip title={showFilters ? 'Hide filters' : 'Show filters'} placement="right">
            <IconButton
              size="large"
              onClick={() => setShowFilters(s => !s)}
              sx={{
                backgroundColor:'background.paper',
                border:'3px solid #388e3c',
                color: '#388e3c',
                boxShadow:2,
                width: 40,
                height: 40,
                borderRadius: '50%',
                '&:hover':{ backgroundColor:'rgba(46, 112, 49, 0.06)' }
              }}
            >
              {showFilters ? <ChevronLeftIcon fontSize="medium" /> : <ChevronRightIcon fontSize="medium" />}
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Main content */}
      <Box flexGrow={1} p={2} overflow="auto" sx={{ display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* Loading overlay */}
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              backdropFilter: 'blur(2px)',
            }}
          >
            <Box sx={{ textAlign: 'center' }}>
              <Box
                sx={{
                  width: 60,
                  height: 60,
                  border: '4px solid #e0e0e0',
                  borderTop: '4px solid #388e3c',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto 16px',
                  '@keyframes spin': {
                    '0%': { transform: 'rotate(0deg)' },
                    '100%': { transform: 'rotate(360deg)' },
                  },
                }}
              />
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Applying filters...
              </Typography>
              <Button
                variant="outlined"
                color="error"
                onClick={cancelRequest}
                size="small"
              >
                Cancel
              </Button>
            </Box>
          </Box>
        )}
        <Routes>
          <Route
            path="/"
            element={
              <>
                <ExploreStudiesTable
                  studies={studies}
                  setStudies={setStudies}
                  totalCount={totalCount}
                  page={page}
                  rowsPerPage={rowsPerPage}
                  onPageChange={(p, size) => { setPage(p); setRowsPerPage(size); }}
                  filters={filters}
                  setFilters={setFilters}
                  onToggleStudyAvailability={onToggleStudyAvailability}
                  onAddStudy={onAddStudy}
                  fetchStudies={fetchStudies}
                />
                <AppliedFilters 
                  filters={filters}
                  onFiltersChange={setFilters}
                />
                {/* Fixed footer bar at the bottom */}
                <Box
                  sx={{
                    backgroundColor: '#ffffff',
                    paddingTop: 2,
                    paddingBottom: 2,
                    paddingLeft: 3,
                    paddingRight: 3,
                    borderTop: '1px solid #e0e0e0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 2,
                    flexWrap: 'wrap',
                    boxShadow: '0 -2px 8px rgba(0, 0, 0, 0.1)',
                    position: 'fixed',
                    bottom: 16,
                    left: showFilters ? filterWidth + 24 : 24,
                    right: 24,
                    zIndex: 100,
                    transition: isResizing ? 'none' : 'left 300ms ease'
                  }}
                >
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <Button
                      variant="contained"
                      startIcon={<FileUploadIcon />}
                      onClick={(e) => setImportMenuAnchor(e.currentTarget)}
                      sx={{
                        backgroundColor: '#388e3c',
                        '&:hover': { backgroundColor: '#2e7031' }
                      }}
                    >
                      Import Data
                    </Button>
                    <Menu
                      anchorEl={importMenuAnchor}
                      open={Boolean(importMenuAnchor)}
                      onClose={() => setImportMenuAnchor(null)}
                      anchorOrigin={{
                        vertical: 'top',
                        horizontal: 'left',
                      }}
                      transformOrigin={{
                        vertical: 'bottom',
                        horizontal: 'left',
                      }}
                    >
                      <MenuItem 
                        onClick={() => {
                          setImportMenuAnchor(null);
                          setShowIndividualImport(true);
                        }}
                      >
                        <ListItemIcon>
                          <TableChartIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Import Individual Data" 
                          secondary="Upload CSV files to specific tables"
                        />
                      </MenuItem>
                      <MenuItem 
                        onClick={() => {
                          setImportMenuAnchor(null);
                          setShowFullDatabaseImport(true);
                        }}
                      >
                        <ListItemIcon>
                          <StorageIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText 
                          primary="Import Database" 
                          secondary="Replace entire database with SQLite file"
                        />
                      </MenuItem>
                    </Menu>
                    <ImportIndividualTable
                      open={showIndividualImport}
                      onImportSuccess={() => { 
                        clearAsyncAutocompleteCache(); 
                        fetchStudies(); 
                        setShowIndividualImport(false);
                      }}
                      onClose={() => setShowIndividualImport(false)}
                    />
                    <ImportFullDatabase
                      open={showFullDatabaseImport}
                      onImportSuccess={() => { 
                        clearAsyncAutocompleteCache(); 
                        fetchStudies(); 
                        setShowFullDatabaseImport(false);
                      }}
                      onClose={() => setShowFullDatabaseImport(false)}
                    />
                    <ExportSelectionButton
                      filters={filters}
                      onExportSuccess={() => { clearAsyncAutocompleteCache(); }}
                    />
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Link 
                        href={`${API_PROTOCOL}://${API_HOST}:${API_PORT}/swagger/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ 
                          fontSize: '0.875rem', 
                          textDecoration: 'none',
                          fontWeight: 'bold',
                          color: '#000000',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                          '&:hover': {
                            color: '#388e3c'
                          }
                        }}
                      >
                        <ApiIcon sx={{ fontSize: '1.1rem' }} />
                        API Documentation
                      </Link>
                      <Link 
                        href="https://github.com/GeorgakilasLab/bMINTY"
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ 
                          fontSize: '0.875rem', 
                          textDecoration: 'none',
                          fontWeight: 'bold',
                          color: '#000000',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                          '&:hover': {
                            color: '#388e3c'
                          }
                        }}
                      >
                        <GitHubIcon sx={{ fontSize: '1.1rem' }} />
                        GitHub Repository
                      </Link>
                    </Box>
                    <img 
                      src="/static/bmintyShort.png" 
                      alt="bMinty" 
                      style={{
                        height: "55px",
                        width: "auto"
                      }}
                    />
                  </Box>
                </Box>
              </>
            }
          />
        </Routes>
      </Box>
    </Box>
  );
}