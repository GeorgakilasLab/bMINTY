// src/components/AssayDetailsCard.jsx
import React from 'react';
import {
  Card,
  CardContent,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Stack,
  Box
} from '@mui/material';
import { formatNumber } from '../utils/formatNumber';
import DetailsPanel from './DetailsPanel';

export default function AssayDetailsCard({ assayDetails, assemblyList, kit, date, description, target, note }) {
  if (!assayDetails) {
    return null;
  }

  return (
    <Card 
      sx={{ 
        width: '100%', 
        boxSizing: 'border-box',
        backgroundColor: 'transparent',
        border: 'none',
        boxShadow: 'none'
      }}
    >
      <CardContent sx={{ 
        width: '100%', 
        padding: '0',
        boxSizing: 'border-box',
        '&:last-child': { paddingBottom: 0 }
      }}>
        <Box sx={{
          backgroundColor: '#f5f5f5',
          padding: '16px 24px',
          borderRadius: '8px'
        }}>
          {/* Details Panel above metrics */}
          <Box sx={{ mb: 2 }}>
            <DetailsPanel 
              kit={kit}
              date={date}
              target={target}
              description={description}
              note={note}
              type="assay"
            />
          </Box>

          <Stack 
            direction="row" 
            spacing={1} 
            sx={{ 
              width: '100%', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start', 
              flexWrap: 'nowrap',
              gap: 1
            }}
          >
            {/* Metrics Section */}
            <MetricsTable assayDetails={assayDetails} />

            {/* Pipeline Section */}
            {assayDetails.pipeline_name && (
              <PipelineTable assayDetails={assayDetails} />
            )}

            {/* Assemblies Section */}
            {assemblyList && assemblyList.length > 0 && (
              <AssembliesSection assemblyList={assemblyList} />
            )}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}

function MetricsTable({ assayDetails }) {
  return (
    <Table 
      size="small" 
      sx={{
        backgroundColor: '#f1f8f5',
        borderRadius: 1,
        '& td': { 
          border: '1px solid #c8e6c9', 
          padding: '6px 8px', 
          fontSize: '0.85rem' 
        },
        flex: '1 1 0',
        alignSelf: 'flex-start'
      }}
    >
      <TableHead>
        <TableRow sx={{ borderBottom: '3px solid #388e3c' }}>
          <TableCell 
            colSpan={2} 
            sx={{ 
              fontWeight: 700, 
              backgroundColor: '#e8f5e9', 
              fontSize: '1.1rem', 
              textAlign: 'center' 
            }}
          >
            Metrics
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        <TableRow>
          <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9', width: '150px' }}>
            Total Intervals
          </TableCell>
          <TableCell>{formatNumber(assayDetails.total_intervals)}</TableCell>
        </TableRow>
        <TableRow>
          <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
            Non-zero Signals
          </TableCell>
          <TableCell>{formatNumber(assayDetails.signal_nonzero)}</TableCell>
        </TableRow>
        <TableRow>
          <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
            Zero Signals
          </TableCell>
          <TableCell>{formatNumber(assayDetails.signal_zero)}</TableCell>
        </TableRow>
        <TableRow>
          <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
            Cells
          </TableCell>
          <TableCell>{formatNumber(assayDetails.cell_total)}</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}

function PipelineTable({ assayDetails }) {
  return (
    <Table 
      size="small" 
      sx={{
        backgroundColor: '#f1f8f5',
        borderRadius: 1,
        '& td': { 
          border: '1px solid #c8e6c9', 
          padding: '6px 8px', 
          fontSize: '0.85rem' 
        },
        flex: '1 1 0',
        alignSelf: 'flex-start'
      }}
    >
      <TableHead>
        <TableRow sx={{ borderBottom: '3px solid #388e3c' }}>
          <TableCell 
            colSpan={2} 
            sx={{ 
              fontWeight: 700, 
              backgroundColor: '#e8f5e9', 
              fontSize: '1.1rem', 
              textAlign: 'center' 
            }}
          >
            Pipeline
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        <TableRow>
          <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9', width: '120px' }}>
            Name
          </TableCell>
          <TableCell>{assayDetails.pipeline_name}</TableCell>
        </TableRow>
        {assayDetails.pipeline_description && (
          <TableRow>
            <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
              Description
            </TableCell>
            <TableCell>{assayDetails.pipeline_description}</TableCell>
          </TableRow>
        )}
        {assayDetails.pipeline_external_url && (
          <TableRow>
            <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
              External URL
            </TableCell>
            <TableCell>
              <a
                href={assayDetails.pipeline_external_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ 
                  color: '#388e3c', 
                  textDecoration: 'none', 
                  wordBreak: 'break-word' 
                }}
              >
                {assayDetails.pipeline_external_url.length > 50
                  ? assayDetails.pipeline_external_url.substring(0, 50) + '…'
                  : assayDetails.pipeline_external_url}
              </a>
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function AssembliesSection({ assemblyList }) {
  return (
    <Stack 
      sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 2, 
        flex: '1 1 0',
        alignSelf: 'flex-start'
      }}
    >
      {assemblyList.map((asm, idx) => (
        <Table 
          key={`asm-${asm.id || idx}`} 
          size="small" 
          sx={{
            backgroundColor: '#f1f8f5',
            borderRadius: 1,
            '& td': { 
              border: '1px solid #c8e6c9', 
              padding: '6px 8px', 
              fontSize: '0.85rem' 
            },
            width: '100%'
          }}
        >
          <TableHead>
            <TableRow sx={{ borderBottom: '3px solid #388e3c' }}>
              <TableCell 
                colSpan={2} 
                sx={{ 
                  fontWeight: 700, 
                  backgroundColor: '#e8f5e9', 
                  fontSize: '1.1rem', 
                  textAlign: 'center' 
                }}
              >
                Assembly {assemblyList.length > 1 ? `${idx + 1}` : ''}
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            <TableRow>
              <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9', width: '120px' }}>
                Name
              </TableCell>
              <TableCell>{asm.name}</TableCell>
            </TableRow>
            {asm.version && (
              <TableRow>
                <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
                  Version
                </TableCell>
                <TableCell>{asm.version}</TableCell>
              </TableRow>
            )}
            {asm.species && (
              <TableRow>
                <TableCell sx={{ fontWeight: 600, backgroundColor: '#e8f5e9' }}>
                  Species
                </TableCell>
                <TableCell>{asm.species}</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      ))}
    </Stack>
  );
}
