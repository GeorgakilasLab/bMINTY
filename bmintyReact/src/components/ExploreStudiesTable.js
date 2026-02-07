// src/components/ExploreStudiesTable.jsx
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Paper,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TablePagination,
  IconButton,
  Typography,
  Tooltip
} from '@mui/material';
import { CiEdit } from "react-icons/ci";
import { KeyboardArrowDown, KeyboardArrowUp } from '@mui/icons-material';
import { Link } from 'react-router-dom';
import StudyFormModal from './StudyFormModal';
import AssayFormModal from './AssayFormModal';
import AssayDetailsCard from './AssayDetailsCard';
import DetailsPanel from './DetailsPanel';

import ToggleAvailabilityButton from './ToggleAvailabilityButton';
import { FaToggleOn, FaToggleOff } from 'react-icons/fa';
import { API_BASE } from '../config';


function TruncatedCell({ text, maxWidth = '100%' }) {
  return (
    <Tooltip title={text || ''} enterDelay={500}>
      <span style={{
        display: 'block',
        maxWidth,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis'
      }}>
        {text}
      </span>
    </Tooltip>
  );
}

function MultilineCell({ text, maxWidth = '100%' }) {
  return (
    <span style={{
      display: '-webkit-box',
      WebkitLineClamp: 3,
      WebkitBoxOrient: 'vertical',
      maxWidth,
      whiteSpace: 'normal',
      wordWrap: 'break-word',
      wordBreak: 'break-word',
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    }}>
      {text}
    </span>
  );
}

export default function ExploreStudiesTable({
  studies,
  setStudies,
  totalCount,
  page,
  rowsPerPage,
  onPageChange,
  filters,
  setFilters,
  onToggleStudyAvailability, // unused external prop
  onAddStudy,
  fetchStudies
}) {
  const [expandedStudy, setExpandedStudy] = useState(null);
  const [assaysByStudy, setAssaysByStudy] = useState({});
  const [assaysPage, setAssaysPage] = useState(0);
  const [assaysRows, setAssaysRows] = useState(5);
  const [expandedAssay, setExpandedAssay] = useState(null);
  const [assayDetails, setAssayDetails] = useState({});
  const [draggedAssay, setDraggedAssay] = useState(null);
  const [dragOverStudyId, setDragOverStudyId] = useState(null);
  
  // Ref for tracking mouse down time to enable drag only after >1s hold
  const mouseDownTimeRef = useRef(null);
  const dragEnabledRef = useRef(false);
  const dragTimerRef = useRef(null);
  const [heldAssayId, setHeldAssayId] = useState(null); // Track which assay is being held

  const [openForm, setOpenForm] = useState(false);
  const [currentStudy, setCurrentStudy] = useState(null);
  const [openAssayForm, setOpenAssayForm] = useState(false);
  const [currentAssay, setCurrentAssay] = useState(null);
  const [currentAssayStudyId, setCurrentAssayStudyId] = useState(null);

  // Column width state for resizable columns
  const [studyColumnWidths, setStudyColumnWidths] = useState({
    expand: 40,
    externalId: 100,
    repository: 90,
    name: 120,
    description: 140,
    note: 100,
    assays: 70,
    available: 70,
    modify: 50
  });

  const [assayColumnWidths, setAssayColumnWidths] = useState({
    expand: 40,
    name: 80,
    externalId: 70,
    type: 65,
    tissue: 70,
    cellType: 75,
    treatment: 75,
    platform: 75,
    note: 80,
    available: 55,
    modify: 50
  });

  const [resizingColumn, setResizingColumn] = useState(null);
  const [resizeStart, setResizeStart] = useState(0);

  // Mouse down handler for column resizing
  const handleResizeStart = (e, column, isAssay = false) => {
    setResizingColumn({ column, isAssay });
    setResizeStart(e.clientX);
    e.preventDefault();
  };

  // Mouse move and mouse up handlers for column resizing
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!resizingColumn) return;
      
      const diff = e.clientX - resizeStart;
      const { column, isAssay } = resizingColumn;
      const setter = isAssay ? setAssayColumnWidths : setStudyColumnWidths;
      
      setter(prev => ({
        ...prev,
        [column]: Math.max(40, prev[column] + diff)
      }));
      setResizeStart(e.clientX);
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
    };

    if (resizingColumn) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizingColumn, resizeStart, assayColumnWidths, studyColumnWidths]);


  // called by modal “Save”
  const handleSave = async formData => {
    if (currentStudy) {
      await axios.put(`${API_BASE}/studies/${currentStudy.id}/`, formData);
    } else {
      await axios.post(`${API_BASE}/studies/`, formData);
    }
    setOpenForm(false);
    setCurrentStudy(null);
    fetchStudies(page, rowsPerPage);
  };

  const handleCancel = () => {
    setOpenForm(false);
    setCurrentStudy(null);
  };

  const handleAssaySave = async (formData) => {
    if (currentAssay && currentAssayStudyId) {
      try {
        const newStudyId = formData.study;
        const hasStudyChanged = newStudyId && newStudyId !== currentAssayStudyId;

        // PATCH to the nested endpoint with the updated study_id
        await axios.patch(
          `${API_BASE}/studies/${currentAssayStudyId}/assays/${currentAssay.id}/`,
          formData
        );
        
        if (hasStudyChanged) {
          // If study changed, remove assay from old study and reload both studies
          setAssaysByStudy(prev => {
            const oldPack = prev[currentAssayStudyId] || { assays: [], totalCount: 0 };
            const updatedAssays = (oldPack.assays || []).filter(a => a.id !== currentAssay.id);
            return { 
              ...prev, 
              [currentAssayStudyId]: { ...oldPack, assays: updatedAssays, totalCount: Math.max(0, oldPack.totalCount - 1) }
            };
          });
          // Refresh the new study's assays if it's expanded to show the moved assay
          if (expandedStudy === newStudyId) {
            await loadAssays(newStudyId, assaysPage, assaysRows);
          }
          // Refresh studies to update assay counts
          fetchStudies(page, rowsPerPage);
        } else {
          // Update local state if assay stayed in same study
          setAssaysByStudy(prev => {
            const pack = prev[currentAssayStudyId] || { assays: [], totalCount: 0 };
            const updatedAssays = (pack.assays || []).map(a => 
              a.id === currentAssay.id ? { ...a, ...formData } : a
            );
            return { ...prev, [currentAssayStudyId]: { ...pack, assays: updatedAssays } };
          });
        }
        
        setOpenAssayForm(false);
        setCurrentAssay(null);
        setCurrentAssayStudyId(null);
      } catch (err) {
        console.error('Failed to save assay:', err);
      }
    }
  };

  const handleAssayFormCancel = () => {
    setOpenAssayForm(false);
    setCurrentAssay(null);
    setCurrentAssayStudyId(null);
  };

  // Toggle availability (local handler)
  async function onToggleStudyAvailabilityLocal(studyId, newAvailability) {
    try {
      await axios.patch(
        `${API_BASE}/studies/${studyId}/status/`,
        { study_availability: newAvailability }
      );
      setStudies(studies =>
        studies.map(s =>
          s.id === studyId ? { ...s, availability: newAvailability } : s
        )
      );
      fetchStudies(page, rowsPerPage);
    } catch (err) {
      console.error('Failed to toggle availability:', err);
    }
  }

  // Toggle availability for an assay within a study (nested endpoint)
  async function onToggleAssayAvailabilityLocal(studyId, assayId, currentAvailability) {
    try {
      await axios.patch(
        `${API_BASE}/studies/${studyId}/assays/${assayId}/status/`,
        { assay_availability: !currentAvailability }
      );
      // Update local state without full refetch
      setAssaysByStudy(prev => {
        const pack = prev[studyId] || { assays: [], totalCount: 0 };
        const updated = (pack.assays || []).map(a =>
          a.id === assayId ? { ...a, availability: !currentAvailability } : a
        );
        return { ...prev, [studyId]: { ...pack, assays: updated } };
      });
      // Trigger fresh query for studies
      fetchStudies(page, rowsPerPage);
    } catch (err) {
      console.error('Failed to toggle assay availability:', err);
    }
  }

  // Remove the useEffect that reloads assays on filter change
  // The nested assay list should show all assays for the expanded study
  // regardless of global filters
  
  // load assays for a study
  const loadAssays = async (studyId, pg, pgSize) => {
    try {
      const { data } = await axios.get(
        `${API_BASE}/studies/${studyId}/assays/`,
        { params: { page: pg + 1, page_size: pgSize } }
      );
      // Debug: log first item to inspect availability field
      if (data?.results?.length) {
        console.log('[ExploreStudiesTable] First assay payload:', data.results[0]);
      } else {
        console.log('[ExploreStudiesTable] No assays returned for study', studyId);
      }
      setAssaysByStudy(m => ({
        ...m,
        [studyId]: { assays: data.results, totalCount: data.count }
      }));
    } catch (err) {
      console.error(err);
    }
  };

  // toggle expand on a study
  const toggleStudy = studyId => {
    const next = expandedStudy === studyId ? null : studyId;
    setExpandedStudy(next);
    setExpandedAssay(null);
    setAssaysPage(0);
    setAssaysRows(5);
    if (next) loadAssays(next, assaysPage, assaysRows);
  };

  // toggle expand on an assay, fetching details once
  const toggleAssay = async (studyId, assayId) => {
    if (expandedAssay === assayId) {
      setExpandedAssay(null);
      return;
    }
    if (!assayDetails[assayId]) {
      try {
        const resp = await axios.get(
          `${API_BASE}/studies/${studyId}/assays/${assayId}/details/`
        );
        setAssayDetails(m => ({ ...m, [assayId]: resp.data }));
      } catch (err) {
        console.error(err);
      }
    }
    setExpandedAssay(assayId);
  };

  // Drag and drop handlers
  const handleAssayDragStart = (e, assay, studyId) => {
    // Only allow drag if held for >1s
    if (!dragEnabledRef.current) {
      e.preventDefault();
      return;
    }
    
    setDraggedAssay({ assay, studyId });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', `assay-${assay.id}-${studyId}`);
  };

  const handleStudyDragOver = (e, studyId) => {
    if (draggedAssay && draggedAssay.studyId !== studyId) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      setDragOverStudyId(studyId);
      // Auto-expand the study being dragged over
      setExpandedStudy(studyId);
    }
  };

  const handleStudyDragLeave = () => {
    setDragOverStudyId(null);
  };

  const handleStudyDrop = async (e, targetStudyId) => {
    e.preventDefault();
    setDragOverStudyId(null);

    if (!draggedAssay || draggedAssay.studyId === targetStudyId) {
      setDraggedAssay(null);
      return;
    }

    // Move the assay to the target study
    const { assay, studyId: sourceStudyId } = draggedAssay;
    const formData = {
      name: assay.name,
      type: assay.type,
      tissue: assay.tissue,
      cell_type: assay.cell_type,
      treatment: assay.treatment,
      platform: assay.platform,
      kit: assay.kit,
      target: assay.target,
      date: assay.date,
      description: assay.description,
      note: assay.note,
      study: targetStudyId
    };

    try {
      await axios.patch(
        `${API_BASE}/studies/${sourceStudyId}/assays/${assay.id}/`,
        formData
      );

      // Remove assay from old study
      setAssaysByStudy(prev => {
        const oldPack = prev[sourceStudyId] || { assays: [], totalCount: 0 };
        const updatedAssays = (oldPack.assays || []).filter(a => a.id !== assay.id);
        return {
          ...prev,
          [sourceStudyId]: { ...oldPack, assays: updatedAssays, totalCount: Math.max(0, oldPack.totalCount - 1) }
        };
      });

      // Refresh new study's assays if expanded
      if (expandedStudy === targetStudyId) {
        await loadAssays(targetStudyId, assaysPage, assaysRows);
      }

      // Refresh studies to update assay counts
      fetchStudies(page, rowsPerPage);
    } catch (err) {
      console.error('Failed to move assay:', err);
    }

    setDraggedAssay(null);
  };

  return (
    <div>
      <StudyFormModal
        open={openForm}
        study={currentStudy}
        onSave={handleSave}
        onCancel={handleCancel}
      />

      <AssayFormModal
        open={openAssayForm}
        assay={currentAssay}
        studies={studies}
        currentStudyId={currentAssayStudyId}
        onSave={handleAssaySave}
        onCancel={handleAssayFormCancel}
      />

      <TableContainer component={Paper} sx={{ mt: 2, overflowX: 'auto', overflowY: 'auto' }}>
        <Table sx={{ tableLayout: 'fixed', minWidth: '100%' }}>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#c8e6c9', fontSize: '1rem' }}>
              <TableCell sx={{ width: studyColumnWidths.expand, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }} />
              <TableCell sx={{ width: studyColumnWidths.name, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                Name
                <div onMouseDown={(e) => handleResizeStart(e, 'name')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.externalId, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                External ID
                <div onMouseDown={(e) => handleResizeStart(e, 'externalId')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)', '&:hover': { backgroundColor: 'rgba(0,0,0,0.3)' } }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.repository, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                Repository
                <div onMouseDown={(e) => handleResizeStart(e, 'repository')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.description, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                Description
                <div onMouseDown={(e) => handleResizeStart(e, 'description')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.note, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                Note
                <div onMouseDown={(e) => handleResizeStart(e, 'note')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.assays, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                Assays
                <div onMouseDown={(e) => handleResizeStart(e, 'assays')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.available, fontSize: '0.95rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                Available
                <div onMouseDown={(e) => handleResizeStart(e, 'available')} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
              </TableCell>
              <TableCell sx={{ width: studyColumnWidths.modify, fontSize: '0.95rem', fontWeight: 'bold' }}>Modify</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {studies.map(s => (
              <React.Fragment key={s.id}>
                <TableRow 
                  hover 
                  onDragOver={(e) => handleStudyDragOver(e, s.id)}
                  onDragLeave={handleStudyDragLeave}
                  onDrop={(e) => handleStudyDrop(e, s.id)}
                  sx={{
                    backgroundColor: dragOverStudyId === s.id ? '#fff3e0' : (expandedStudy === s.id ? '#d4edd6' : 'inherit'),
                    fontWeight: 'bold',
                    border: dragOverStudyId === s.id ? '2px dashed #ff9800' : 'none',
                    borderLeft: expandedStudy === s.id ? '6px solid #388e3c' : 'none',
                    transition: 'background-color 0.2s'
                  }}>
                  <TableCell sx={{ width: studyColumnWidths.expand, overflow: 'hidden' }}>
                    <IconButton size="small" onClick={() => toggleStudy(s.id)}>
                      {expandedStudy === s.id
                        ? <KeyboardArrowUp />
                        : <KeyboardArrowDown />}
                    </IconButton>
                  </TableCell>
                  {/* <TableCell>{s.id}</TableCell> */}
                  <TableCell sx={{ width: studyColumnWidths.name, overflow: 'hidden', fontWeight: 'bold', whiteSpace: 'normal' }}><MultilineCell text={s.name} maxWidth="100%" /></TableCell>
                  <TableCell sx={{ width: studyColumnWidths.externalId, overflow: 'hidden', fontWeight: 'bold' }}>{s.external_id}</TableCell>
                  <TableCell sx={{ width: studyColumnWidths.repository, overflow: 'hidden', fontWeight: 'bold' }}>{s.external_repo ? <TruncatedCell text={s.external_repo} maxWidth="100%" /> : <span style={{ opacity: 0.6 }}>-</span>}</TableCell>
                  <TableCell sx={{ width: studyColumnWidths.description, overflow: 'hidden', fontWeight: 'bold', whiteSpace: 'normal' }}><MultilineCell text={s.description} maxWidth="100%" /></TableCell>
                  {/* READ-ONLY study note; edit via Modify pencil (modal) */}
                  <TableCell sx={{ width: studyColumnWidths.note, overflow: 'hidden', fontWeight: 'bold' }}>
                    <Typography sx={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem', fontWeight: 'bold' }}>
                      {s.note || <span style={{ opacity: 0.6 }}>No note</span>}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ width: studyColumnWidths.assays, overflow: 'hidden', textAlign: 'right', fontWeight: 'bold' }}>{s.assay_count}</TableCell>
                  <TableCell sx={{ width: studyColumnWidths.available, overflow: 'hidden' }}>
                    <ToggleAvailabilityButton
                      studyId={s.id}
                      study_availability={s.availability}
                      onToggle={onToggleStudyAvailabilityLocal}
                    />
                  </TableCell>
                  <TableCell sx={{ width: studyColumnWidths.modify, overflow: 'hidden' }}>
                    <IconButton
                      size="small"
                      onClick={() => {
                        setCurrentStudy(s);
                        setOpenForm(true); // edit note inside modal
                      }}
                      sx={{
                        color: !s.availability ? '#9e9e9e' : '#388e3c',
                        '&:hover': { backgroundColor: 'rgba(56, 142, 60, 0.1)' }
                      }}
                    >
                       <CiEdit size={24} />
                    </IconButton>
                  </TableCell>
                </TableRow>

                {expandedStudy === s.id && (
                  <TableRow sx={{
                    backgroundColor: '#f1f8f5',
                    borderLeft: '6px solid #388e3c',
                    borderBottom: 'none',
                    '& > *': { borderBottom: 'none' }
                  }}>
                    <TableCell colSpan={9} sx={{ p: 2, pb: 0 }}>
                      <DetailsPanel 
                        type="study"
                      />
                    </TableCell>
                  </TableRow>
                )}

                {expandedStudy === s.id && (
                  <TableRow sx={{
                    backgroundColor: '#f1f8f5',
                    borderLeft: '6px solid #388e3c',
                    borderTop: 'none',
                    '& > *': { borderBottom: 'none', borderTop: 'none' }
                  }}>
                    {/* columns for assay table */}
                    <TableCell colSpan={9} sx={{ p: 2, pt: 0 }}>
                      <Table size="small">
                        <TableHead>
                          <TableRow sx={{ backgroundColor: '#e8f5e9' }}>
                            <TableCell sx={{ width: assayColumnWidths.expand, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }} />
                            <TableCell sx={{ width: assayColumnWidths.name, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Name
                              <div onMouseDown={(e) => handleResizeStart(e, 'name', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.externalId, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Ext. ID
                              <div onMouseDown={(e) => handleResizeStart(e, 'externalId', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.type, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Type
                              <div onMouseDown={(e) => handleResizeStart(e, 'type', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.tissue, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Tissue
                              <div onMouseDown={(e) => handleResizeStart(e, 'tissue', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.cellType, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Cell Type
                              <div onMouseDown={(e) => handleResizeStart(e, 'cellType', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.treatment, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Treatment
                              <div onMouseDown={(e) => handleResizeStart(e, 'treatment', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.platform, fontSize: '0.9rem', fontWeight: 'bold', position: 'relative', userSelect: 'none' }}>
                              Platform
                              <div onMouseDown={(e) => handleResizeStart(e, 'platform', true)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '4px', cursor: 'col-resize', backgroundColor: 'rgba(0,0,0,0.1)' }} />
                            </TableCell>
                            <TableCell sx={{ width: assayColumnWidths.available, fontSize: '0.9rem', fontWeight: 'bold' }}>Available</TableCell>
                            <TableCell sx={{ width: assayColumnWidths.modify, fontSize: '0.9rem', fontWeight: 'bold' }}>Modify</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {(assaysByStudy[s.id]?.assays || []).map(a => {
                            const assemblyList = (() => {
                              const detailAssemblies = assayDetails[a.id]?.assemblies;
                              if (Array.isArray(detailAssemblies) && detailAssemblies.length) {
                                return detailAssemblies;
                              }
                              if (a.assemblies) {
                                return a.assemblies
                                  .split(',')
                                  .map(name => name.trim())
                                  .filter(Boolean)
                                  .map((name, idx) => ({ id: `fallback-${a.id}-${idx}`, name, version: null, species: null }));
                              }
                              return [];
                            })();

                            return (
                              <React.Fragment key={a.id}>
                                <TableRow 
                                  hover 
                                  draggable="true"
                                  onMouseDown={() => {
                                    mouseDownTimeRef.current = Date.now();
                                    dragEnabledRef.current = false;
                                    setHeldAssayId(a.id);
                                    // Enable drag after 200ms
                                    dragTimerRef.current = setTimeout(() => {
                                      dragEnabledRef.current = true;
                                    }, 200);
                                  }}
                                  onMouseUp={() => {
                                    const holdTime = Date.now() - (mouseDownTimeRef.current || 0);
                                    
                                    if (dragTimerRef.current) {
                                      clearTimeout(dragTimerRef.current);
                                      dragTimerRef.current = null;
                                    }
                                    
                                    // Short click (< 200ms) = expand/collapse
                                    if (holdTime < 200 && !dragEnabledRef.current) {
                                      toggleAssay(s.id, a.id);
                                    }
                                    
                                    mouseDownTimeRef.current = null;
                                    dragEnabledRef.current = false;
                                    setHeldAssayId(null);
                                  }}
                                  onMouseLeave={() => {
                                    if (dragTimerRef.current) {
                                      clearTimeout(dragTimerRef.current);
                                      dragTimerRef.current = null;
                                    }
                                    mouseDownTimeRef.current = null;
                                    dragEnabledRef.current = false;
                                    setHeldAssayId(null);
                                  }}
                                  onDragStart={(e) => handleAssayDragStart(e, a, s.id)}
                                  sx={{
                                    backgroundColor: heldAssayId === a.id && dragEnabledRef.current ? 'rgba(56, 142, 60, 0.1)' : (expandedAssay === a.id ? '#c5e1a5' : 'inherit'),
                                    borderLeft: expandedAssay === a.id ? '6px solid #689f38' : 'none',
                                    cursor: 'grab',
                                    opacity: draggedAssay?.assay.id === a.id ? 0.6 : 1,
                                    transition: 'opacity 0.2s'
                                  }}>
                                <TableCell sx={{ width: assayColumnWidths.expand, overflow: 'hidden' }}>
                                  <IconButton size="small"
                                    onClick={() => toggleAssay(s.id, a.id)}>
                                    {expandedAssay === a.id
                                      ? <KeyboardArrowUp />
                                      : <KeyboardArrowDown />} 
                                  </IconButton>
                                </TableCell>
                                <TableCell sx={{ width: assayColumnWidths.name, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.name} maxWidth="100%" /></TableCell>
                                <TableCell sx={{ width: assayColumnWidths.externalId, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.external_id} maxWidth="100%" /></TableCell>
                                <TableCell sx={{ width: assayColumnWidths.type, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.type} maxWidth="100%" /></TableCell>
                                <TableCell sx={{ width: assayColumnWidths.tissue, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.tissue} maxWidth="100%" /></TableCell>
                                <TableCell sx={{ width: assayColumnWidths.cellType, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.cell_type} maxWidth="100%" /></TableCell>
                                <TableCell sx={{ width: assayColumnWidths.treatment, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.treatment} maxWidth="100%" /></TableCell> 
                                <TableCell sx={{ width: assayColumnWidths.platform, overflow: 'hidden', fontWeight: 'bold' }}><TruncatedCell text={a.platform} maxWidth="100%" /></TableCell>
                                <TableCell>
                                  <IconButton
                                    size="small"
                                    onClick={() => onToggleAssayAvailabilityLocal(s.id, a.id, a.availability)}
                                    aria-label={a.availability ? 'Deactivate assay' : 'Activate assay'}
                                  >
                                    {a.availability ? (
                                      <FaToggleOn size={20} className="text-green-500" />
                                    ) : (
                                      <FaToggleOff size={20} className="text-gray-500" />
                                    )}
                                  </IconButton>
                                </TableCell>
                                <TableCell sx={{ width: assayColumnWidths.modify, overflow: 'hidden' }}>
                                  <IconButton
                                    size="small"
                                    onClick={() => {
                                      setCurrentAssay(a);
                                      setCurrentAssayStudyId(s.id);
                                      setOpenAssayForm(true);
                                    }}
                                    sx={{
                                      color: !a.availability ? '#9e9e9e' : '#388e3c',
                                      '&:hover': { backgroundColor: 'rgba(56, 142, 60, 0.1)' }
                                    }}
                                  >
                                    <CiEdit size={24} />
                                  </IconButton>
                                </TableCell>

                              </TableRow>
                              {expandedAssay === a.id && (
                                <TableRow sx={{
                                  backgroundColor: '#a5d6a7',
                                  borderLeft: '6px solid #388e3c',
                                  '& > *': { borderBottom: 'none' }
                                }}>
                                  <TableCell colSpan={11} sx={{ p: 3, pr: 4, width: '100%' }}>
                                    {assayDetails[a.id] ? (
                                      <AssayDetailsCard 
                                        assayDetails={assayDetails[a.id]} 
                                        assemblyList={assemblyList}
                                        kit={a.kit}
                                        date={a.date}
                                        description={a.description}
                                        target={a.target}
                                        note={a.note}
                                      />
                                    ) : (
                                      <Typography>Loading assay details…</Typography>
                                    )}
                                  </TableCell>
                                </TableRow>
                              )}
                            </React.Fragment>
                          );
                          })}
                        </TableBody>
                      </Table>

                      <TablePagination
                        component="div"
                        count={assaysByStudy[s.id]?.totalCount || 0}
                        page={assaysPage}
                        rowsPerPage={assaysRows}
                        rowsPerPageOptions={[5, 10, 20]}
                        onPageChange={(_, newPage) => {
                          setAssaysPage(newPage);
                          loadAssays(expandedStudy, newPage, assaysRows);
                        }}
                        onRowsPerPageChange={e => {
                          const newSize = +e.target.value;
                          setAssaysRows(newSize);
                          setAssaysPage(0);
                          loadAssays(expandedStudy, 0, newSize);
                        }}
                      />
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}

            {/* bottom row */}
            {/* <AddStudyRow onAdd={() => setOpenForm(true)} /> */}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={totalCount}
          page={page}
          rowsPerPage={rowsPerPage}
          rowsPerPageOptions={[5, 10, 20]}
          onPageChange={(e, newPage) => onPageChange(newPage)}
          onRowsPerPageChange={e => onPageChange(0)}
        />
      </TableContainer>
    </div>
  );
}
