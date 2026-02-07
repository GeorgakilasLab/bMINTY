import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { Description as DescriptionIcon, Note as NoteIcon, Build as BuildIcon, Event as EventIcon, CenterFocusStrong as TargetIcon } from '@mui/icons-material';

/**
 * Reusable component for displaying description and note details
 * Used for both Studies and Assays
 */
export default function DetailsPanel({ 
  description, 
  note,
  kit,
  date,
  target,
  type = 'study' // 'study' or 'assay'
}) {
  const hasContent = description || note || kit || date || target;

  if (!hasContent) {
    return null;
  }

  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        backgroundColor: 'transparent',
        border: 'none',
        borderRadius: 1
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {/* For assays: Kit, Date, Target in 3-column grid */}
        {type === 'assay' && (kit || date || target) && (
          <Box sx={{ 
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 2,
            justifyContent: 'flex-start',
            alignItems: 'flex-start'
          }}>
            {[
              kit && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <BuildIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Kit:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {kit}
                    </Typography>
                  </Box>
                </Box>
              ),
              date && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <EventIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Date:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {date}
                    </Typography>
                  </Box>
                </Box>
              ),
              target && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <TargetIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Target:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {target}
                    </Typography>
                  </Box>
                </Box>
              )
            ].filter(Boolean).concat(Array(3).fill(<div key="spacer" />)).slice(0, 3)}
          </Box>
        )}

        {/* Description and Note - on same row in 3-column grid, aligned with above */}
        {(description || note) && (
          <Box sx={{ 
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 2,
            justifyContent: 'flex-start',
            alignItems: 'flex-start'
          }}>
            {[
              description && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <DescriptionIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Description:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {description}
                    </Typography>
                  </Box>
                </Box>
              ),
              note && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <NoteIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Note:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {note}
                    </Typography>
                  </Box>
                </Box>
              )
            ].filter(Boolean).concat(Array(3).fill(<div key="spacer" />)).slice(0, 3)}
          </Box>
        )}
        {/* Study type: Kit, Date, Target in 3-column grid */}
        {type === 'study' && (kit || date || target) && (
          <Box sx={{ 
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 2,
            justifyContent: 'flex-start',
            alignItems: 'flex-start'
          }}>
            {[
              kit && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <BuildIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Kit:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {kit}
                    </Typography>
                  </Box>
                </Box>
              ),
              date && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <EventIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Date:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {date}
                    </Typography>
                  </Box>
                </Box>
              ),
              target && (
                <Box sx={{ display: 'flex', gap: 0.6, alignItems: 'flex-start' }}>
                  <TargetIcon sx={{ fontSize: '1.15rem', color: '#666', marginTop: '2px', flexShrink: 0 }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: '#333',
                        display: 'inline'
                      }}
                    >
                      Target:
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontSize: '0.9rem',
                        color: '#555',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.4,
                        display: 'inline',
                        ml: 0.5
                      }}
                    >
                      {target}
                    </Typography>
                  </Box>
                </Box>
              )
            ].filter(Boolean).concat(Array(3).fill(<div key="spacer" />)).slice(0, 3)}
          </Box>
        )}

      </Box>
    </Paper>
  );
}
