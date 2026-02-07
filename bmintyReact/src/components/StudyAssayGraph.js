import React, { useEffect, useState, useCallback } from 'react';
import { 
  CircularProgress, 
  Paper, 
  Box, 
  Typography, 
  Chip,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  InputAdornment
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SearchIcon from '@mui/icons-material/Search';
import HomeIcon from '@mui/icons-material/Home';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

/*
  StudyAssayGraph - Enhanced version with ReactFlow
  - Fetches all studies and lets user pick one
  - Displays a central study node with edges to assay nodes
  - ReactFlow provides zoom, pan, and better UX
  - Each node shows key info; click to open detail page
*/

import { API_BASE } from '../config';

// Custom node colors based on availability
const getNodeColor = (available) => {
  if (available === true) return '#4caf50'; // green
  if (available === false) return '#f44336'; // red
  return '#9e9e9e'; // gray for unknown
};

export default function StudyAssayGraph() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [studies, setStudies] = useState([]);
  const [selectedStudyId, setSelectedStudyId] = useState(null);
  const [assays, setAssays] = useState([]);
  const [selectedAssayIds, setSelectedAssayIds] = useState(new Set());
  const [error, setError] = useState(null);
  const [studySearchTerm, setStudySearchTerm] = useState('');
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Fetch all studies on mount
  useEffect(() => {
    const fetchStudies = async () => {
      try {
        const resp = await fetch(`${API_BASE}/studies/`);
        const json = await resp.json();
        const list = Array.isArray(json.results) ? json.results : (Array.isArray(json) ? json : []);
        setStudies(list);
        // Don't auto-select first study - let user choose
      } catch (e) {
        console.error(e);
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchStudies();
  }, []);

  // Fetch assays when study changes
  useEffect(() => {
    if (!selectedStudyId) return;
    const fetchAssays = async () => {
      setLoading(true);
      try {
        const resp = await fetch(`${API_BASE}/studies/${selectedStudyId}/assays-full/`);
        const json = await resp.json();
        const list = Array.isArray(json.results) ? json.results : (Array.isArray(json) ? json : []);
        setAssays(list);
        // Select all assays by default
        setSelectedAssayIds(new Set(list.map(a => a.id)));
      } catch (e) {
        console.error(e);
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchAssays();
  }, [selectedStudyId]);

  // Fetch assay details for each assay
  const fetchAssayDetails = useCallback(async (studyId, assayId) => {
    try {
      const resp = await fetch(`${API_BASE}/studies/${studyId}/assays/${assayId}/details/`);
      const json = await resp.json();
      return json;
    } catch (e) {
      console.error('Error fetching assay details:', e);
      return null;
    }
  }, []);

  // Toggle individual assay selection
  const handleToggleAssay = (assayId) => {
    setSelectedAssayIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(assayId)) {
        newSet.delete(assayId);
      } else {
        newSet.add(assayId);
      }
      return newSet;
    });
  };

  // Select all assays
  const handleSelectAll = () => {
    setSelectedAssayIds(new Set(assays.map(a => a.id)));
  };

  // Unselect all assays
  const handleUnselectAll = () => {
    setSelectedAssayIds(new Set());
  };

  // Filter studies based on search term
  const filteredStudies = studies.filter(study => {
    const searchLower = studySearchTerm.toLowerCase();
    return (
      (study.name && study.name.toLowerCase().includes(searchLower)) ||
      (study.external_id && study.external_id.toLowerCase().includes(searchLower)) ||
      (study.description && study.description.toLowerCase().includes(searchLower)) ||
      study.id.toString().includes(searchLower)
    );
  });

  // Handle study selection
  const handleSelectStudy = (studyId) => {
    setSelectedStudyId(studyId);
    setStudySearchTerm(''); // Clear search after selection
  };

  // Build nodes and edges whenever assays change
  useEffect(() => {
    if (!selectedStudyId || assays.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const study = studies.find(s => s.id === selectedStudyId);
    if (!study) return;

    const buildGraph = async () => {
      // Filter only selected assays
      const visibleAssays = assays.filter(a => selectedAssayIds.has(a.id));

      // Center study node
      const studyNode = {
        id: 'study-' + study.id,
        type: 'default',
        position: { x: 400, y: 300 },
        data: { 
          label: (
            <div style={{textAlign:'center', padding:'8px'}}>
              <strong style={{fontSize:'1.1rem'}}>{study.name || study.external_id}</strong>
              <div style={{fontSize:'0.8rem', marginTop:4}}>Study ID: {study.id}</div>
              <Chip label={`${visibleAssays.length} / ${assays.length} assays`} size="small" style={{marginTop:4}} />
            </div>
          )
        },
        style: {
          background: '#3f51b5',
          color: '#fff',
          border: '2px solid #303f9f',
          borderRadius: '12px',
          width: 200,
          fontSize: '0.9rem',
          boxShadow: '0 4px 12px rgba(0,0,0,0.25)'
        }
      };

      // Fetch details for visible assays only
      const assaysWithDetails = await Promise.all(
        visibleAssays.map(async (assay) => {
          const details = await fetchAssayDetails(selectedStudyId, assay.id);
          return { ...assay, details };
        })
      );

      // Assay nodes in a circular layout
      const assayNodes = assaysWithDetails.map((assay, idx) => {
        const angle = (2 * Math.PI * idx) / Math.max(visibleAssays.length, 1);
        const radius = 350;
        const x = 400 + radius * Math.cos(angle);
        const y = 300 + radius * Math.sin(angle);
        
        return {
          id: 'assay-' + assay.id,
          type: 'default',
          position: { x, y },
          data: {
            label: (
              <div style={{textAlign:'left', padding:'10px', fontSize:'0.8rem', lineHeight:'1.4'}}>
                <strong style={{fontSize:'0.95rem', display:'block', marginBottom:'6px'}}>{assay.name}</strong>
                {assay.details ? (
                  <>
                    <div><strong>Assembly:</strong> {assay.details.assembly_name || 'N/A'}</div>
                    <div><strong>Pipeline:</strong> {assay.details.pipeline || 'N/A'}</div>
                    <div><strong>Total Intervals:</strong> {assay.details.total_intervals || 0}</div>
                    <div><strong>Zero-signal:</strong> {assay.details.interval_zero_count || 0}</div>
                    <div><strong>Non-zero:</strong> {assay.details.interval_nonzero_count || 0}</div>
                  </>
                ) : (
                  <>
                    <div><strong>Platform:</strong> {assay.platform}</div>
                    <div><strong>Peaks:</strong> {assay.peak_count || 0}</div>
                    <div><strong>Non-zero:</strong> {assay.interval_nonzero_count || 0}</div>
                    <div><strong>Zero:</strong> {assay.interval_zero_count || 0}</div>
                  </>
                )}
              </div>
            )
          },
          style: {
            background: getNodeColor(assay.availability),
            color: '#fff',
            border: '2px solid rgba(255,255,255,0.5)',
            borderRadius: '8px',
            width: 220,
            fontSize: '0.8rem',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
          }
        };
      });

      // Edges from study to each assay (no animation)
      const assayEdges = visibleAssays.map(assay => ({
        id: `e-study-${study.id}-assay-${assay.id}`,
        source: 'study-' + study.id,
        target: 'assay-' + assay.id,
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#1976d2', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#1976d2'
        }
      }));

      setNodes([studyNode, ...assayNodes]);
      setEdges(assayEdges);
    };

    buildGraph();
  }, [selectedStudyId, assays, studies, selectedAssayIds, setNodes, setEdges, fetchAssayDetails]);

  const onNodeClick = useCallback((event, node) => {
    if (node.id.startsWith('assay-')) {
      const assayId = node.id.replace('assay-', '');
      window.open(`/studies/${selectedStudyId}/assays-full/${assayId}`, '_blank');
    }
  }, [selectedStudyId]);

  if (error) {
    return <div style={{color:'red', textAlign:'center', marginTop:'2rem'}}>{error}</div>;
  }

  // Study selection screen (before graph)
  if (!selectedStudyId) {
    return (
      <Box sx={{ width: '100%', minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f7fa', p: 3 }}>
        <Paper elevation={3} sx={{ maxWidth: 800, mx: 'auto', p: 4, mt: 4 }}>
          {/* Header with Home button */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#3f51b5', flexGrow: 1, textAlign: 'center' }}>
              bMinty Graph Visualization
            </Typography>
            <Button
              variant="outlined"
              startIcon={<HomeIcon />}
              onClick={() => navigate('/')}
              sx={{ 
                textTransform: 'none',
                position: 'absolute',
                top: 32,
                right: 32
              }}
            >
              Home
            </Button>
          </Box>
          
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress size={60} />
            </Box>
          ) : (
            <>
              <Typography variant="body1" sx={{ mb: 3, color: '#666', textAlign: 'center' }}>
                Select a study to visualize its assays in an interactive graph
              </Typography>

              {/* Search box */}
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Search studies by name, ID, or description..."
                value={studySearchTerm}
                onChange={(e) => setStudySearchTerm(e.target.value)}
                sx={{ mb: 3 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />

              {/* Study list */}
              <Box sx={{ maxHeight: 500, overflowY: 'auto' }}>
                {filteredStudies.length === 0 ? (
                  <Typography sx={{ textAlign: 'center', color: '#999', p: 2 }}>
                    No studies found
                  </Typography>
                ) : (
                  filteredStudies.map(study => (
                    <Paper
                      key={study.id}
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
                      onClick={() => handleSelectStudy(study.id)}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#3f51b5' }}>
                            {study.name || study.external_id}
                          </Typography>
                          {study.description && (
                            <Typography variant="body2" sx={{ color: '#666', mt: 0.5 }}>
                              {study.description}
                            </Typography>
                          )}
                          <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                            <Chip label={`ID: ${study.id}`} size="small" />
                            <Chip label={`External: ${study.external_id}`} size="small" />
                            {study.availability !== undefined && (
                              <Chip 
                                label={study.availability ? 'Available' : 'Unavailable'} 
                                size="small" 
                                color={study.availability ? 'success' : 'error'}
                              />
                            )}
                          </Box>
                        </Box>
                        <Button variant="contained" sx={{ textTransform: 'none' }}>
                          View Graph
                        </Button>
                      </Box>
                    </Paper>
                  ))
                )}
              </Box>

              {studySearchTerm && (
                <Typography variant="caption" sx={{ display: 'block', mt: 2, textAlign: 'center', color: '#666' }}>
                  Showing {filteredStudies.length} of {studies.length} studies
                </Typography>
              )}
            </>
          )}
        </Paper>
      </Box>
    );
  }

  // Graph view (after study selection)
  const selectedStudy = studies.find(s => s.id === selectedStudyId);

  return (
    <Box sx={{ width: '100%', height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f7fa' }}>
      {/* Header with navigation and study info */}
      <Paper elevation={2} sx={{ p: 2, mb: 1, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            variant="outlined" 
            startIcon={<HomeIcon />}
            onClick={() => navigate('/')}
            sx={{ textTransform: 'none' }}
          >
            Home
          </Button>
          <Button 
            variant="outlined" 
            onClick={() => setSelectedStudyId(null)}
            sx={{ textTransform: 'none' }}
          >
            ← Back to Studies
          </Button>
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#3f51b5' }}>
            {selectedStudy?.name || selectedStudy?.external_id}
          </Typography>
          <Typography variant="caption" sx={{ color: '#666' }}>
            Study ID: {selectedStudyId}
          </Typography>
        </Box>
        {loading && <CircularProgress size={24} />}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip label="Available" size="small" style={{background:'#4caf50', color:'#fff'}} />
          <Chip label="Unavailable" size="small" style={{background:'#f44336', color:'#fff'}} />
          <Chip label="Unknown" size="small" style={{background:'#9e9e9e', color:'#fff'}} />
        </Box>
      </Paper>

      {/* Assay selection panel */}
      {!loading && assays.length > 0 && (
        <Paper elevation={2} sx={{ mx: 2, mb: 1 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 'bold' }}>
                Select Assays ({selectedAssayIds.size} of {assays.length} selected)
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Button 
                  variant="outlined" 
                  size="small" 
                  onClick={handleSelectAll}
                  sx={{ textTransform: 'none' }}
                >
                  Select All
                </Button>
                <Button 
                  variant="outlined" 
                  size="small" 
                  onClick={handleUnselectAll}
                  sx={{ textTransform: 'none' }}
                >
                  Unselect All
                </Button>
              </Box>
              <FormGroup sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 1 }}>
                {assays.map(assay => (
                  <FormControlLabel
                    key={assay.id}
                    control={
                      <Checkbox
                        checked={selectedAssayIds.has(assay.id)}
                        onChange={() => handleToggleAssay(assay.id)}
                        size="small"
                      />
                    }
                    label={
                      <span style={{fontSize:'0.9rem'}}>
                        {assay.name} <em style={{color:'#666'}}>({assay.platform})</em>
                      </span>
                    }
                  />
                ))}
              </FormGroup>
            </AccordionDetails>
          </Accordion>
        </Paper>
      )}

      {/* ReactFlow canvas */}
      <Box sx={{ flexGrow: 1, position: 'relative' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress size={60} />
          </Box>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="#aaa" gap={16} />
            <Controls />
            <MiniMap 
              nodeColor={(node) => node.style?.background || '#ccc'}
              maskColor="rgba(0, 0, 0, 0.1)"
            />
          </ReactFlow>
        )}
      </Box>
    </Box>
  );
}
